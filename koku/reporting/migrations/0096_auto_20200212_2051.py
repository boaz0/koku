# Generated by Django 2.2.10 on 2020-02-12 20:51
import django.db.models.deletion
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):

    dependencies = [("reporting", "0095_auto_20200212_1606")]

    operations = [
        migrations.AlterField(
            model_name="awscostentrylineitemdaily",
            name="cost_entry_bill",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="reporting.AWSCostEntryBill"),
        ),
        migrations.AlterField(
            model_name="awscostentrylineitemdailysummary",
            name="cost_entry_bill",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="reporting.AWSCostEntryBill"),
        ),
        migrations.AlterField(
            model_name="costsummary",
            name="report_period",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="reporting.OCPUsageReportPeriod"),
        ),
        migrations.AlterField(
            model_name="ocpawscostlineitemdailysummary",
            name="cost_entry_bill",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="reporting.AWSCostEntryBill"),
        ),
        migrations.AlterField(
            model_name="ocpawscostlineitemdailysummary",
            name="report_period",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="reporting.OCPUsageReportPeriod"),
        ),
        migrations.AlterField(
            model_name="ocpawscostlineitemprojectdailysummary",
            name="cost_entry_bill",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="reporting.AWSCostEntryBill"),
        ),
        migrations.AlterField(
            model_name="ocpawscostlineitemprojectdailysummary",
            name="report_period",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="reporting.OCPUsageReportPeriod"),
        ),
        migrations.AlterField(
            model_name="ocpazurecostlineitemdailysummary",
            name="report_period",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="reporting.OCPUsageReportPeriod"),
        ),
        migrations.AlterField(
            model_name="ocpazurecostlineitemprojectdailysummary",
            name="report_period",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="reporting.OCPUsageReportPeriod"),
        ),
        migrations.AlterField(
            model_name="ocpstoragelineitemdaily",
            name="report_period",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="reporting.OCPUsageReportPeriod"),
        ),
        migrations.AlterField(
            model_name="ocpusagelineitemdaily",
            name="report_period",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="reporting.OCPUsageReportPeriod"),
        ),
        migrations.AlterField(model_name="ocpusagelineitemdaily", name="total_seconds", field=models.IntegerField()),
        migrations.AlterField(
            model_name="ocpusagelineitemdailysummary",
            name="report_period",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="reporting.OCPUsageReportPeriod"),
        ),
    ]