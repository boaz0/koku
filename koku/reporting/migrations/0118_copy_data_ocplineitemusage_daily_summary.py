# Generated by Django 2.2.13 on 2020-06-17 22:54
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [("reporting", "0117_make_partitions_ocplineitemusage_daily_summary")]

    operations = [
        migrations.RunSQL(
            """
-- ========================================
--    Copy the data from the old table to the new table
-- ========================================
INSERT INTO reporting_ocpusagelineitem_daily_summary SELECT *
  FROM __reporting_ocpusagelineitem_daily_summary;
            """
        )
    ]
