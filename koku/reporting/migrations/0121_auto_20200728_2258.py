# Generated by Django 2.2.14 on 2020-07-28 22:58
import pkgutil

from django.db import connection
from django.db import migrations
from django.db import models

from reporting.provider.all.openshift.models import VIEWS as OCP_ALL_VIEWS
from reporting.provider.azure.openshift.models import VIEWS as OCP_AZURE_VIEWS


def add_views(apps, schema_editor):
    """Create database VIEWS from files."""
    for view in OCP_AZURE_VIEWS:
        view_sql = pkgutil.get_data("reporting.provider.azure.openshift", f"sql/views/{view}.sql")
        view_sql = view_sql.decode("utf-8")
        with connection.cursor() as cursor:
            cursor.execute(view_sql)

    for view in OCP_ALL_VIEWS:
        view_sql = pkgutil.get_data("reporting.provider.all.openshift", f"sql/views/{view}.sql")
        view_sql = view_sql.decode("utf-8")
        with connection.cursor() as cursor:
            cursor.execute(view_sql)


class Migration(migrations.Migration):

    dependencies = [("reporting", "0120_auto_20200724_1354")]

    operations = [
        migrations.RunSQL(
            """

                DROP INDEX IF EXISTS ocpall_compute_summary;
                DROP MATERIALIZED VIEW IF EXISTS reporting_ocpall_compute_summary;

                DROP INDEX IF EXISTS ocpall_cost_summary;
                DROP MATERIALIZED VIEW IF EXISTS reporting_ocpall_cost_summary;

                DROP INDEX IF EXISTS ocpall_cost_summary_account;
                DROP MATERIALIZED VIEW IF EXISTS reporting_ocpall_cost_summary_by_account;

                DROP INDEX IF EXISTS ocpall_cost_summary_region;
                DROP MATERIALIZED VIEW IF EXISTS reporting_ocpall_cost_summary_by_region;

                DROP INDEX IF EXISTS ocpall_cost_summary_service;
                DROP MATERIALIZED VIEW IF EXISTS reporting_ocpall_cost_summary_by_service;

                DROP INDEX IF EXISTS ocpall_database_summary;
                DROP MATERIALIZED VIEW IF EXISTS reporting_ocpall_database_summary;

                DROP INDEX IF EXISTS ocpall_network_summary;
                DROP MATERIALIZED VIEW IF EXISTS reporting_ocpall_network_summary;

                DROP INDEX IF EXISTS ocpall_storage_summary;
                DROP MATERIALIZED VIEW IF EXISTS reporting_ocpall_storage_summary;

                DROP INDEX IF EXISTS ocpall_cost_daily_summary;
                DROP INDEX IF EXISTS ocpallcstdlysumm_node;
                DROP INDEX IF EXISTS ocpallcstdlysumm_node_like;
                DROP INDEX IF EXISTS ocpallcstdlysumm_nsp;
                DROP INDEX IF EXISTS ocpall_product_code_ilike;

                DROP MATERIALIZED VIEW IF EXISTS reporting_ocpallcostlineitem_daily_summary;

                DROP INDEX IF EXISTS ocpall_cost_project_daily_summary;
                DROP INDEX IF EXISTS ocpallcstprjdlysumm_node;
                DROP INDEX IF EXISTS ocpallcstprjdlysumm_nsp;
                DROP INDEX IF EXISTS ocpallcstprjdlysumm_node_like;
                DROP INDEX IF EXISTS ocpallcstprjdlysumm_nsp_like;
                DROP INDEX IF EXISTS ocpall_product_family_ilike;
                DROP MATERIALIZED VIEW IF EXISTS reporting_ocpallcostlineitem_project_daily_summary;

                DROP INDEX IF EXISTS ocpazure_compute_summary;
                DROP MATERIALIZED VIEW IF EXISTS reporting_ocpazure_compute_summary;

                DROP INDEX IF EXISTS ocpazure_cost_summary;
                DROP MATERIALIZED VIEW IF EXISTS reporting_ocpazure_cost_summary;

                DROP INDEX IF EXISTS ocpazure_cost_summary_account;
                DROP MATERIALIZED VIEW IF EXISTS reporting_ocpazure_cost_summary_by_account;

                DROP INDEX IF EXISTS ocpazure_cost_summary_location;
                DROP MATERIALIZED VIEW IF EXISTS reporting_ocpazure_cost_summary_by_location;

                DROP INDEX IF EXISTS ocpazure_cost_summary_service;
                DROP MATERIALIZED VIEW IF EXISTS reporting_ocpazure_cost_summary_by_service;

                DROP INDEX IF EXISTS ocpazure_database_summary;
                DROP MATERIALIZED VIEW IF EXISTS reporting_ocpazure_database_summary;

                DROP INDEX IF EXISTS ocpazure_network_summary;
                DROP MATERIALIZED VIEW IF EXISTS reporting_ocpazure_network_summary;

                DROP INDEX IF EXISTS ocpazure_storage_summary;
                DROP MATERIALIZED VIEW IF EXISTS reporting_ocpazure_storage_summary;
            """
        ),
        migrations.AlterField(
            model_name="ocpazurecostlineitemdailysummary", name="currency", field=models.TextField(null=True)
        ),
        migrations.AlterField(
            model_name="ocpazurecostlineitemdailysummary", name="instance_type", field=models.TextField(null=True)
        ),
        migrations.AlterField(
            model_name="ocpazurecostlineitemdailysummary", name="resource_location", field=models.TextField(null=True)
        ),
        migrations.AlterField(
            model_name="ocpazurecostlineitemdailysummary", name="service_name", field=models.TextField(null=True)
        ),
        migrations.AlterField(
            model_name="ocpazurecostlineitemdailysummary", name="subscription_guid", field=models.TextField()
        ),
        migrations.AlterField(
            model_name="ocpazurecostlineitemdailysummary", name="unit_of_measure", field=models.TextField(null=True)
        ),
        migrations.AlterField(
            model_name="ocpazurecostlineitemprojectdailysummary", name="currency", field=models.TextField(null=True)
        ),
        migrations.AlterField(
            model_name="ocpazurecostlineitemprojectdailysummary",
            name="instance_type",
            field=models.TextField(null=True),
        ),
        migrations.AlterField(
            model_name="ocpazurecostlineitemprojectdailysummary",
            name="resource_location",
            field=models.TextField(null=True),
        ),
        migrations.AlterField(
            model_name="ocpazurecostlineitemprojectdailysummary",
            name="service_name",
            field=models.TextField(null=True),
        ),
        migrations.AlterField(
            model_name="ocpazurecostlineitemprojectdailysummary", name="subscription_guid", field=models.TextField()
        ),
        migrations.AlterField(
            model_name="ocpazurecostlineitemprojectdailysummary",
            name="unit_of_measure",
            field=models.TextField(null=True),
        ),
        migrations.RunPython(add_views),
    ]
