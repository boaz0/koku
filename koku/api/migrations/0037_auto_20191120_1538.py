# Generated by Django 2.2.6 on 2019-11-20 15:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0036_auto_20191113_2029'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sources',
            name='koku_uuid',
            field=models.CharField(max_length=512, null=True, unique=True),
        ),
    ]