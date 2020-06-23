# Generated by Django 2.2.13 on 2020-06-17 22:54
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [("api", "0021_db_functions"), ("reporting", "0115_populate_source_uuid")]

    operations = [
        migrations.RunSQL(
            """
-- ===================================
--  Create tracking table
-- ===================================

CREATE TABLE IF NOT EXISTS partitioned_tables (
    id serial PRIMARY KEY,
    schema_name text NOT NULL default current_schema,
    table_name text NOT NULL,
    partition_of_table_name text NOT NULL,
    partition_type text NOT NULL,
    partition_col text NOT NULL,
    partition_parameters JSONB NOT NULL,
    CONSTRAINT table_partition_unique UNIQUE (schema_name, table_name)
 );

CREATE INDEX "partable_table"
    ON partitioned_tables (table_name, schema_name);

CREATE INDEX "partable_partition_parameters"
    ON partitioned_tables USING GIN (partition_parameters);

CREATE INDEX "partable_partition_type"
    ON partitioned_tables (partition_type);

-- ===================================
--   Create the new partitioned table
-- ===================================

-- Rename the original table's sequence object. Looks strange, but it ends up making things easier later
ALTER SEQUENCE reporting_ocpusagelineitem_daily_summary_id_seq
      RENAME TO __reporting_ocpusagelineitem_daily_summary_id_seq ;

CREATE TABLE IF NOT EXISTS p_reporting_ocpusagelineitem_daily_summary (
    LIKE reporting_ocpusagelineitem_daily_summary INCLUDING ALL
);

ALTER TABLE p_reporting_ocpusagelineitem_daily_summary ADD
CONSTRAINT p_reporting_ocpusagelineitem_daily_summary_pkey PRIMARY KEY (usage_start, id) ;

ALTER TABLE p_reporting_ocpusagelineitem_daily_summary ADD
CONSTRAINT p_reporting_ocpusageli_report_period_id_fc68baea_fk_reporting
FOREIGN KEY (report_period_id) REFERENCES reporting_ocpusagereportperiod(id) DEFERRABLE INITIALLY DEFERRED ;

CREATE INDEX p_pod_labels_idx
    ON p_reporting_ocpusagelineitem_daily_summary USING gin (pod_labels) ;

CREATE INDEX p_summary_data_source_idx
    ON p_reporting_ocpusagelineitem_daily_summary USING btree (data_source) ;

CREATE INDEX p_reporting_ocpusagelineitem_report_period_id_fc68baea
    ON p_reporting_ocpusagelineitem_daily_summary USING btree (report_period_id) ;

CREATE INDEX p_summary_ocp_usage_idx
    ON p_reporting_ocpusagelineitem_daily_summary USING btree (usage_start) ;

CREATE INDEX p_summary_namespace_idx
    ON p_reporting_ocpusagelineitem_daily_summary USING btree (namespace varchar_pattern_ops) ;

CREATE INDEX p_summary_node_idx
    ON p_reporting_ocpusagelineitem_daily_summary USING btree (node varchar_pattern_ops) ;

CREATE INDEX p_ocp_summary_namespace_like_idx
    ON p_reporting_ocpusagelineitem_daily_summary USING gin (upper((namespace)::text) gin_trgm_ops) ;

CREATE INDEX p_ocp_summary_node_like_idx
    ON p_reporting_ocpusagelineitem_daily_summary USING gin (upper((node)::text) gin_trgm_ops) ;


-- ===================================
--  Create default partition
-- ===================================
CREATE TABLE reporting_ocpusagelineitem_daily_summary_default
PARTITION OF p_reporting_ocpusagelineitem_daily_summary DEFAULT;

INSERT INTO partitioned_tables (
    schema_name,
    table_name,
    partition_of_table_name,
    partition_type,
    partition_col,
    partition_parameters
)
VALUES (
    current_schema,
    'reporting_ocpusagelineitem_daily_summary_default',
    'reporting_ocpusagelineitem_daily_summary',
    'default',
    'usage_start',
    '{"default": true}'::jsonb
);
            """
        )
    ]
