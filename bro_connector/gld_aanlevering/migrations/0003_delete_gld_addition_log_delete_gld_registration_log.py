# Generated by Django 4.0.3 on 2022-09-09 12:46

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('gld_aanlevering', '0002_rename_registration_object_id_deliveredlocations_groundwater_monitoring_well_id_and_more'),
    ]

    operations = [
        migrations.DeleteModel(
            name='gld_addition_log',
        ),
        migrations.DeleteModel(
            name='gld_registration_log',
        ),
    ]