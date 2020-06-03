#!/usr/bin/env python3
# flake8: noqa
"""
This program will convert source tables with data into partitioned tables,
copying the data from source to the new partitioned table. All required
table partitions to hold the data will also be created as well as a default
partition.
"""
# Config:
# {
#     partition_targets: {
#         <schema>: [
#             {
#                 <table_name>: {
#                     target_schema: <schema_name>, # Optional. If not found, then target_schema = processing schema
#                     partition_key: <column_name>,
#                     partition_type: <partition-type>, # should be "list" or "range"
#                     <partition-type>: {
#                         values: [[<values here>], ...], # List of lists Required for list partition type
#                         interval_type: <val>     # If date, timestamp type, choose "month" or "year"
#                                                  # If numeric type, choose the appropriate DB data type (int, numeric(10,2), etc)
#                                                  # Required for range partition type
#                         interval: <val>          # The interval itself: 1, 5, 10, etc
#                                                  # Required for range partition type
#                     }
#                     drop_table: boolean          # Drop the source table after data migration. False by default
#                 }
#             },
#             ...
#         ],
#         # A "*" will match any schema not explicitly listed to process or exclude
#         "*":      [
#             {
#                 <table_name>: {
#                     target_schema: <schema_name>, # Optional. If not found, then target_schema = processing schema
#                     partition_key: <column_name>,
#                     partition_type: <partition-type>, # should be "list" or "range"
#                     <partition-type>: {
#                         values: [[<values here>], ...], # List of lists Required for list partition type
#                         interval_type: <val>     # If date, timestamp type, choose "month" or "year"
#                                                  # If numeric type, choose the appropriate DB data type (int, numeric(10,2), etc)
#                                                  # Required for range partition type
#                         interval: <val>          # The interval itself: 1, 5, 10, etc
#                                                  # Required for range partition type
#                     }
#                     drop_table: boolean          # Drop the source table after data migration. False by default
#                 }
#             },
#             ...
#         ]
#     }
#     excluded_shemata: []    # put any user schemata to exclude here
# }
#
# The "*" schema matches any schema not explicitly listed
import argparse
import datetime
import decimal
import json
import logging
import os
import sys
from collections import defaultdict
from collections import namedtuple
from math import ceil

import psycopg2
import sqlparse
import yaml
from dateutil import relativedelta
from psycopg2.extras import Json
from psycopg2.extras import NamedTupleCursor
from pytz import UTC


logging.basicConfig(level=logging.INFO, style="{", format="{filename}:{asctime}:{levelname}:{message}")
LOG = logging.getLogger(os.path.basename(sys.argv[0]))
LINFO = LOG.info
LERROR = LOG.error
LWARN = LOG.warning
LDEBUG = LOG.debug


SQL_SCRIPT_FILE = None
TABLE_CACHE = {}


def db_json_dumps(d):
    """
    Dump json data using str as the default transform
    Args:
        d (dict) : data
    Returns:
        str : json-formatted string form of d
    """
    return json.dumps(d, default=str)


def json_adapter(d):
    """
    Set the psycopg2 Json class for dict data using db_json_dumps as the dump function
    Args:
        d (dict) : data
    Returns:
        Json : data (d) in a Json instance so that the psycopg2 driver can process it
    """
    return Json(d, dumps=db_json_dumps)


def generate_sample_config():
    cfg = {
        "partition_targets": {
            "<schema>": [
                {
                    "<table_name>": {
                        "target_schema": "<schema_name>, # Optional. If not found, then target_schema = processing schema",
                        "partition_key": "<column_name>",
                        "partition_type": '<partition-type>, # should be "list" or "range"',
                        "<partition-type>": {
                            "values": "[[<values here>], ...], # List of lists. Required for list partition type",
                            "interval_type": '<val>     # If date, timestamp type, choose "month" or "year". If numeric type, choose the appropriate DB data type (int, numeric(10,2), etc). Required for range partition type',
                            "interval": "<val>          # The interval itself: 1, 5, 10, etc. Required for range partition type",
                        },
                        "drop_table": "boolean          # Drop the source table after data migration. False by default",
                    }
                }
            ],
            "*": [
                {
                    "<table_name>": {
                        "target_schema": "<schema_name>, # Optional. If not found, then target_schema = processing schema",
                        "partition_key": "<column_name>",
                        "partition_type": '<partition-type>, # should be "list" or "range"',
                        "<partition-type>": {
                            "values": "[[<values here>], ...], # List of lists. Required for list partition type",
                            "interval_type": '<val>     # If date, timestamp type, choose "month" or "year". If numeric type, choose the appropriate DB data type (int, numeric(10,2), etc). Required for range partition type',
                            "interval": "<val>          # The interval itself: 1, 5, 10, etc. Required for range partition type",
                        },
                        "drop_table": "boolean          # Drop the source table after data migration. False by default",
                    }
                }
            ],
        },
        "excluded_shemata": "[]    # put any user schemata to exclude here",
    }
    comment_buff = """
#
# The "*" schema matches any schema not explicitly listed as a partition target or exclusion
#
# The "<partiiton-type>" value **must** match the value from the "partition_type" key
"""
    yaml.safe_dump(cfg, sys.stdout, sort_keys=True, width=255)
    print(comment_buff, flush=True)


def load_config(config_file_name):
    """
    Load the config file. This is a YAML file.
    Args:
        config_file_name (str) : path to the config file
    Returns:
        dict : The config as read from the YAML
    """
    return yaml.safe_load(open(config_file_name, "rt"))


def connect(db_url):
    """
    Connect to the database
    Args:
        db_url (str) : DB connect string as a URL
    Returns:
        datbase connection class instance
    """
    conn = psycopg2.connect(db_url, cursor_factory=NamedTupleCursor, application_name=os.path.basename(sys.argv[0]))
    LINFO("Connected to {dbname} on {host} at port {port} as user {user}".format(**conn.get_dsn_parameters()))

    return conn


def mogrify_sql(cur, sql, values=None):
    """
    Returns a formatted SQL string from the SQL and arguments
    Args:
        cur (Cursor) : cursor to process the SQL
        sql (str) : The SQL string
        values (list, dict, None) : The values (if any) for the SQL statements. Default = None
    Returns:
        str : The formatted SQL with parameters
    """
    try:
        mog_sql = sqlparse.format(
            cur.mogrify(sql, values), encoding="utf-8", reindent_aligned=True, keyword_case="upper"
        )
    except psycopg2.ProgrammingError:
        mog_sql = f"""{sqlparse.format(sql, encoding='utf-8', reindent_aligned=True, keyword_case='upper')}
VALUES: {str(values)}"""

    return mog_sql


def execute(conn, sql, values=None, override=False):
    """
    Executes the given SQL against the given database connections
    Args:
        conn (Connection) : Database connection
        sql (str) : SQL string
        values (list, dict, None) : Parameters (if any) for the SQL. Default = None
    Returns:
        Cursor : The cursor instance after statement execution
    """
    cur = conn.cursor()
    sqlbuff = mogrify_sql(cur, sql, values)
    LDEBUG(f"Executiong SQL: {os.linesep}{sqlbuff}")

    sqlexec = override or (not SQL_SCRIPT_FILE)
    if sqlexec:
        cur.execute(sql, values)
    else:
        print(sqlbuff, file=SQL_SCRIPT_FILE, end=os.linesep * 2)

    return cur


def get_table_info(conn, schema_name, table_names):
    """
    Get schema name, table name, column name, column data type, column default value
    for a given list of tables. Columns will be in defined column order.
    Args:
        conn (Connection) : Database connection
        schema_name (str) : Name of schema in which table(s) should reside
        table_names (str, list) : comma-separated string of table names or a list of table names
    Returns:
        dict : Returned table info indexed by table_name
    """
    if not (bool(schema_name) or bool(table_names)):
        return {}

    sql = """
select n.nspname as "schema_name",
       c.relname as "table_name",
       a.attname as "column_name",
       format_type(a.atttypid, a.atttypmod) as "data_type",
       a.attnotnull as "not_null",
       (SELECT substring(pg_catalog.pg_get_expr(d.adbin, d.adrelid) for 128)
          FROM pg_catalog.pg_attrdef d
         WHERE d.adrelid = a.attrelid
           AND d.adnum = a.attnum
           AND a.atthasdef) as "default"
  from pg_class c
  join pg_namespace n
    on n.oid = c.relnamespace
  join pg_attribute a
    on a.attrelid = c.oid
   and a.attnum > 0
   and not a.attisdropped
 where n.nspname = %(schema)s
   and c.relkind = 'r'
   and c.relname = any( %(tables)s )
 order by n.nspname,
          c.relname,
          a.attnum;
"""
    if isinstance(table_names, str):
        v_table_names = [t.strip() for t in table_names.split(",")]
    else:
        v_table_names = list(table_names)

    LINFO(f"Getting info for table(s): {', '.join(v_table_names)}")
    values = {"schema": schema_name, "tables": v_table_names}
    res = defaultdict(list)
    for rec in execute(conn, sql, values, override=True):
        res[rec.table_name].append(rec)

    return res


def db_schemas(conn, config):
    """
    Generator that returns all schemata not excluded in the config
    Args:
        conn (Connection) : Database connection
        config (dict) : program config settings
    Returns:
        (generator returning str) : schema name
    """
    excluded_schemata = config.get("excluded_schemata", [])
    if excluded_schemata:
        where = """ where schemaname != any(%s)"""
        values = (excluded_schemata,)
    else:
        where = ""
        values = None

    sql = f"""
select distinct
       schemaname
  from pg_stat_user_tables
{where}
 order
    by schemaname;
    """
    for rec in execute(conn, sql, values, override=True).fetchall():
        LINFO(f"Processing schema {rec.schemaname}")
        yield rec.schemaname


def partition_table_targets(conn, schema, conf):
    """
    Return table info for partition targets from config file
    Args:
        conn (Connection) : Database connection
        schema (str) : Schema name
        conf (dict) : Program config settings
    Returns:
        generator returning dict : {'structure': [<table_info_column_rec>],
                                    'partition_info': config partition settings for table}
    """
    all_targets = conf["partition_targets"]
    schema_targets = all_targets.get(schema, all_targets.get("*", {}))
    fetch_targets = set(schema_targets) - set(TABLE_CACHE)
    if fetch_targets:
        LINFO(f"Caching table info for {','.join(fetch_targets)}")
        TABLE_CACHE.update(
            {
                k: {"structure": v, "partition_info": schema_targets[k]}
                for k, v in get_table_info(conn, schema, fetch_targets).items()
            }
        )
    else:
        LINFO("All table targets cached")

    for table_name in schema_targets:
        LINFO(f"Processing table {table_name}")
        yield TABLE_CACHE[table_name]


def get_partition_key_bounds(conn, schema_name, table_info):
    """
    Using partition information, get the lower and upper bounds of the
    partiton key value for the table partition definition
    Args:
        conn (Connection) : Database connection
        schema_name (str) : Schema name
        table_info (dict) : Table definition and Partition definition
    Returns:
        tuple : (lower_key_value, upper_key_value)
    """
    partition_key = table_info["partition_info"]["partition_key"]
    partition_key_type = get_partition_key_data_type(table_info)
    table_name = table_info["structure"][0].table_name
    sql = f"""
select min({partition_key}) as min_partition_value,
       max({partition_key}) as max_partition_value
  from {schema_name}.{table_name};
"""
    ResultRow = namedtuple("ResultRow", ["min_partition_value", "max_partition_value"])
    LINFO(f"Getting min and max values for {schema_name}.{table_name}.{partition_key}")
    res = execute(conn, sql, override=True).fetchone()

    if res.min_partition_value is None and partition_key_type in (
        "date",
        "timestamp with time zone",
        "timestamp without time zone",
        "timestamp",
        "timestamptz",
    ):
        val = (datetime.date.today() - relativedelta.relativedelta(months=6)).replace(day=1)
        if partition_key_type.startswith("time"):
            val = datetime.datetime(*val.timetuple()[:3]).replace(tzinfo=UTC)
        res = ResultRow(min_partition_value=val, max_partition_value=res.max_partition_value)

    if res.max_partition_value is None and partition_key_type in (
        "date",
        "timestamp with time zone",
        "timestamp without time zone",
        "timestamp",
        "timestamptz",
    ):
        val = (datetime.date.today() + relativedelta.relativedelta(months=6)).replace(day=1)
        if partition_key_type.startswith("time"):
            val = datetime.datetime(*val.timetuple()[:3]).replace(tzinfo=UTC)
        res = ResultRow(min_partition_value=res.min_partition_value, max_partition_value=val)

    return (res.min_partition_value, res.max_partition_value)


def get_partition_key_data_type(table_info):
    """
    Get the DB data type of the partition key
    Args:
        table_info (dict) : Table definition and Partition definition
    Returns:
        str : data type spec
    """
    partition_key = table_info["partition_info"]["partition_key"]
    for col_info in table_info["structure"]:
        if col_info.column_name == partition_key:
            return col_info.data_type


def get_primary_key(table_info):
    """
    Find the primary key column definition in the table structure
    Args:
        table_info (dict) : Table definition and Partition definition
    Returns:
        dict : Column definition
    """
    for rec in table_info["structure"]:
        if rec.is_primary_key:
            return rec


def floor_date(date_val, scale):
    """
    Returns the appropriate day 1 value for a month scale or year scale
    Args:
        date_val (datetime, date) : Date value
        scale (str) : Should be "month" or "year"
    Returns:
        date : the day 1 date value
        None : error
    """
    if isinstance(date_val, datetime.datetime):
        date_val = datetime.date()

    if scale == "month":
        return date_val.replace(day=1)
    elif scale == "year":
        return date_val.replace(month=1, day=1)


def ceil_date(date_val, scale):
    """
    Find the max exclusive date value for the scale of month or year.
    Args:
        date_val (datetime, date) : Date value
        scale (str) : Should be "month" or "year"
    Returns:
        date : the day 1 date value of the next scale period
        None : error
    """
    if isinstance(date_val, datetime.datetime):
        date_val = datetime.date()

    if scale == "month":
        return (date_val + relativedelta.relativedelta(months=1)).replace(day=1)
    elif scale == "year":
        return datetime.date(date_val.year + 1, 1, 1)


def resolve_partition_key_minimum(table_info, min_val):
    """
    Resolve the minimum value for the parititon type and values
    Args:
        table_info (dict) : structure definition and partition definition
        min_val (datetime, date, int, str) : min_val used in the resolution
    Returns:
        Resolve value of the same min_val type
    """
    partition_type = table_info["partition_info"]["partition_type"]
    partition_type_info = table_info["partition_info"][partition_type]
    if partition_type == "range":
        if isinstance(min_val, (datetime.datetime, datetime.date)):
            return floor_date(min_val, partition_type_info["interval_type"])
        else:
            return min_val
    else:
        raise ValueError(
            f"Invalid partition type '{partition_type}'. Partition type should be either 'list' or 'range'"
        )


def resolve_partition_key_maximum(table_info, max_val):
    """
    Resolve the maximum value for the parititon type and values
    Args:
        table_info (dict) : structure definition and partition definition
        max_val (datetime, date, int, str) : max_val used in the resolution
    Returns:
        Resolve value of the same max_val type
    """
    partition_type = table_info["partition_info"]["partition_type"]
    partition_type_info = table_info["partition_info"][partition_type]
    if partition_type == "range":
        if isinstance(max_val, (datetime.datetime, datetime.date)):
            return ceil_date(max_val, partition_type_info["interval_type"])
        elif isinstance(max_val, decimal.Decimal):
            return max_val + decimal.Decimal("1")
        else:
            return max_val + 1
    else:
        raise ValueError(
            f"Invalid partition type '{partition_type}'. Partition type should be either 'list' or 'range'"
        )


def create_partition_table_tracker(conn, schema_name):
    """
    Create a table that will hold the partitions created by
    this program and the definitions of those partitions
    Args:
        conn (Connection) : Database connection
        schema_name (str) : Schema into which this table will be created
    Returns:
        None
    """
    execute(conn, f"drop table if exists {schema_name}.partitioned_tables;")
    sql = f"""
create table if not exists {schema_name}.partitioned_tables
(
    schema_name text not null default '{schema_name}',
    table_name text not null,
    partition_of_table_name text not null,
    partition_type text not null,
    partition_col text not null,
    partition_parameters jsonb not null,
    constraint table_partition_pkey primary key (schema_name, table_name)
);
"""
    execute(conn, sql)


def add_partition_track_record(conn, partition_table_record):
    """
    Add a record to the partition tracking table
    Args:
        conn (Connection) : Database connection
        partition_table_record (dict) : Record data
    """
    sql = f"""
insert into {partition_table_record['schema_name']}.partitioned_tables
(
    schema_name,
    table_name,
    partition_of_table_name,
    partition_type,
    partition_col,
    partition_parameters
)
values
(
    %(schema_name)s,
    %(table_name)s,
    %(partition_of_table_name)s,
    %(partition_type)s,
    %(partition_col)s,
    %(partition_parameters)s
);
"""
    LINFO(
        f"Creating partiton tracking record for {partition_table_record['schema_name']}.{partition_table_record['table_name']}"
    )
    execute(conn, sql, partition_table_record)


def partition_table(conn, schema_name, table_info):
    """
    Create a new partitioned table from the original table definition.
    This will create a new structure that will consist of the partitioned table
    as well as the required number of table partitions that will hold the
    original table's data.
    Args:
        conn (Connection) : Database connection
        schema_name (str) : schema in which the source table resides
        table_info (dict) : Table structure and partition settings
    Returns:
        None
    """
    partition_type = table_info["partition_info"]["partition_type"]
    if partition_type == "range":
        min_val, max_val = get_partition_key_bounds(conn, schema_name, table_info)
        partition_min = resolve_partition_key_minimum(table_info, min_val)
        partition_max = resolve_partition_key_maximum(table_info, max_val)
        partition_values = [partition_min, partition_max]
    else:
        partition_values = table_info["partition_info"][partition_type]["values"]

    create_partitioned_table(conn, schema_name, table_info, partition_values)


def build_partitioned_table_sql(schema_name, table_info):
    """
    Generate the CREATE TABLE statement for the partitioned table
    Args:
        schema_name (str) : Schema name into which this table should be created
        table_info (dict) : Table structure and partition information
    Returns:
        str : CREATE TABLE statement
    """
    table_name = table_info["structure"][0].table_name
    sql = f"""
create table if not exists {schema_name}.p_{table_name}
(
    {f',{os.linesep}    '.join(f'{i.column_name} {i.data_type} {"not null" if i.not_null else ""} {f"default {i.default}" if i.default else ""}' for i in table_info['structure'])}
)
"""
    return sql


def range_interval_gen(interval_type, interval, partition_values):
    """
    Generator that yields a tuple of the min and max values
    for a date range table partition.
    Args:
        interval_type (str) : Interval type for the partition. Should be "month" or "year"
        interval (int) : Interval
        partition_values (list) : (start_val, end_val)
    Returns:
        tuple : A start, end pair within the partition values bounds by the interval type and interval
    """
    interval = int(interval)
    if interval_type == "month":
        reldel_params = {"months": interval}
    elif interval_type == "year":
        reldel_params = {"years": interval}
    else:
        raise ValueError(f"Invalid value {interval_type} for interval_type")

    reldel = relativedelta.relativedelta(**reldel_params)
    start = end = partition_values[0]
    # This should generate one extra range, which will probably be a good thing in this case.
    while start < partition_values[1]:
        start = end
        end = (start + reldel).replace(day=1)
        if isinstance(start, datetime.datetime):
            start = datetime.datetime(*start.timetuple()[:3]).replace(tzinfo=UTC)
            end = datetime.datetime(*end.timetuple()[:3]).replace(tzinfo=UTC)

        yield (start, end)


def create_partitioned_table(conn, schema_name, table_info, partition_values):
    """
    Create the partitioned table from the source table definition. Also create the
    default partition plus any partitions needed based on the data in the table as well
    as the partition settings from the config.
    Note, there will be several commits during this function execution
    Args:
        conn (Connection) : Database connection
        schema_name (str) : Schema of source table
        table_info (dict) : Structure and partition settings of the table to be partitioned
        parttiion_values (list, tuple) : For list partition type, this should be a list of lists of discrete values
                                         For range partition type, this should be a tuple of the lower and upper bounds
    Returns:
        None
    """
    table_name = table_info["structure"][0].table_name
    target_schema = table_info["partition_info"].get("target_schema", schema_name)
    partition_key = table_info["partition_info"]["partition_key"]
    partition_type = table_info["partition_info"]["partition_type"]
    partition_interval_type = table_info["partition_info"][partition_type]["interval_type"]
    partition_interval = table_info["partition_info"][partition_type]["interval"]

    # Create the main partitioned table
    sql = f"""{build_partitioned_table_sql(target_schema, table_info)}partition by {partition_type} ({partition_key});
"""
    LINFO(f"Creating partitioned table {target_schema}.p_{table_name}...")
    execute(conn, f"drop table if exists {target_schema}.p_{table_name};")
    execute(conn, sql)

    # Create the default partition
    create_table_partition(conn, target_schema, table_name, "default", (), -1, partition_key)

    # Resolve the range generator for the partitions needed
    if partition_type == "range":
        partitoin_range_generator = range_interval_gen(partition_interval_type, partition_interval, partition_values)
    else:
        partitoin_range_generator = iter(partition_values)

    # Now create the actual partitions
    for range_ix, partition_range in enumerate(partitoin_range_generator):
        create_table_partition(
            conn, target_schema, table_name, partition_type, partition_range, range_ix, partition_key
        )

    # Now that the partitioned structures are in place, rename so that the partitioned tables get all of the new inserts.
    # Selects, Updates, and Deletes will fail during the copy.
    # This function will execute a COMMIT
    rename_tables(conn, schema_name, table_name, target_schema, "p_" + table_name)

    # Now comes the copy of the data.
    copy_data(conn, schema_name, "__" + table_name, target_schema, table_name)
    conn.commit()

    # And drop the old source table if we're told to.
    if table_info["partition_info"].get("drop_table", False):
        drop_table(conn, schema_name, "__" + table_name)
        conn.commit()


def create_table_partition(conn, target_schema, table_name, partition_type, partition_range, range_ix, partition_col):
    """
    Create a partition of the partitioned table.
    Args:
        conn (Connection) : Database connection
        target_schema (str) : schema in which the partition should be created
        table_name (str) : name of the source table
        partition_type (str) : "list", "range", "default"
        partition_range (tuple) : For list partition, this should be a collection of discrete values
                                  For range partition, this should be a tuple of (low, high) values
                                  where low <= partition_key_value < high
        range_ix (int) : Used for naming list partitions
        partition_col (str) : Used for tracking
    """
    if partition_type == "list":
        partition_suffix = str(range_ix)
        range_clause = "for values in (%s)"
        values = [tuple(partition_range)]
        partition_parameters = {"in": values[0], "default": False}
    elif partition_type == "default":
        partition_suffix = "default"
        partition_parameters = {"default": True}
        range_clause = "DEFAULT"
        values = None
    else:
        range_clause = "for values from (%s) to (%s)"
        values = partition_range
        partition_parameters = {"from": str(partition_range[0]), "to": str(partition_range[1]), "default": False}

        if isinstance(partition_range[0], (datetime.datetime, datetime.date)):
            # PG version 12+ has better syntax for this statement
            if conn.server_version < 120000:
                values = [str(v) for v in values]
            partition_suffix = f"{partition_range[0].year}_{partition_range[0].month:02d}"
        else:
            partition_suffix = str(partition_range[0])

    sql = f"""
create table {target_schema}.{table_name}_{partition_suffix}
partition of {target_schema}.p_{table_name}
{range_clause};
"""
    LINFO(f"Creating table partition {target_schema}.{table_name}_{partition_suffix}...")
    execute(conn, f"drop table if exists {target_schema}.{table_name}_{partition_suffix};")
    execute(conn, sql, values)

    add_partition_track_record(
        conn,
        {
            "schema_name": target_schema,
            "table_name": f"{table_name}_{partition_suffix}",
            "partition_of_table_name": table_name,  # This is intentional!
            "partition_type": partition_type,
            "partition_col": partition_col,
            "partition_parameters": json_adapter(partition_parameters),
        },
    )


def drop_table(conn, schema_name, table_name):
    """
    Truncate, then drop a specified table
    Args:
        conn (Connection) : Database connection
        schema_name (str) : schema where the target table is located
        table_name (str) : name of the target table
    Returns:
        None
    """
    LINFO(f"Dropping table {schema_name}.{table_name}")
    execute(conn, f"truncate table {schema_name}.{table_name};")
    execute(conn, f"drop table {schema_name}.{table_name};")


def rename_tables(conn, source_schema, source_table, target_schema, target_table):
    """
    Lock source table
    Rename the source table to __<source>
    Rename the partitioned table to the source table.
    This function WILL execute a commit
    Args:
        conn (Connection) : Database connection
        source_schema (str) : schema of source table
        source_table (str) : name of source table
        target_schema (str) : schema of target table
        target_table (str) : name of target table
    Returns:
        None
    """
    LINFO(f"Acquiring table lock on {source_schema}.{source_table}")
    execute(conn, "BEGIN;")  # Done on purpose for script generation
    execute(conn, f"lock table {source_schema}.{source_table};")
    LINFO(f"Rename {source_schema}.{source_table} to {source_schema}.__{source_table}")
    execute(conn, f"alter table {source_schema}.{source_table} rename to __{source_table};")
    LINFO(f"Rename {target_schema}.{target_table} to {target_schema}.{source_table}")
    execute(conn, f"alter table {target_schema}.{target_table} rename to {source_table};")
    execute(conn, "COMMIT;")  # Done on purpose for script generation


def copy_data(conn, source_schema, source_table, target_schema, target_table):
    """
    Copy data from the source table and into the target table
    Args:
        conn (Connection) : Database connection
        source_schema (str) : schema of source table
        source_table (str) : name of source table
        target_schema (str) : schema of target table
        target_table (str) : name of target table
    Returns:
        None
    """
    LINFO(f"Copy data from {source_schema}.{source_table} to {target_schema}.{target_table}")
    execute(conn, f"insert into {target_schema}.{target_table} select * from {source_schema}.{source_table};")


def process_database(db_url, config, sqlfilename=""):
    """
    Processes a database based on the partitioning configuration settings
    Args:
        db_url (str) : The connection string for the database in URL format
        config (dict) : Configuration for the partitioning. See comment at top of file
        sqlfilename (str) : name of a sql file to write commands instead of executing them
    Returns:
        None
    """
    global SQL_SCRIPT_FILE

    if not db_url:
        raise ValueError(f'Bad value for db_url: "{db_url}"')

    if not config:
        raise ValueError(f"Bad or empty config dict")

    if sqlfilename:
        SQL_SCRIPT_FILE = open(sqlfilename, "wt")
    try:
        with connect(db_url) as conn:
            for schema in db_schemas(conn, config):
                create_partition_table_tracker(conn, schema)
                for table_info in partition_table_targets(conn, schema, config):
                    partition_table(conn, schema, table_info)
    finally:
        if SQL_SCRIPT_FILE:
            SQL_SCRIPT_FILE.flush()
            SQL_SCRIPT_FILE.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-d",
        "--database",
        dest="db_url",
        metavar="DB_URL",
        required=False,
        default="",
        help="Database connection string in URL form.",
    )
    parser.add_argument(
        "-c", "--config", dest="config", metavar="CONF", required=False, default="", help="Path to config file (YAML)"
    )
    parser.add_argument(
        "-g",
        "--gen-sample-config",
        action="store_true",
        dest="gen_config",
        required=False,
        default=False,
        help="Generate a sample configuration to stdout",
    )
    parser.add_argument(
        "-s",
        "--sql",
        dest="sqlfile",
        required=False,
        metavar="SQLFILE",
        default="",
        help="Generate a sql script instead of executing commands",
    )

    args = parser.parse_args()

    if args.gen_config:
        generate_sample_config()
    else:
        if not args.config:
            raise ValueError("Empty config file name.")
        process_database(args.db_url, load_config(args.config), args.sqlfile)