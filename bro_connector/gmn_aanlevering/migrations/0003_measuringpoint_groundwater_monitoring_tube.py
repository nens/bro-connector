# Generated by Django 4.0.3 on 2023-10-19 09:30

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('gmw_aanlevering', '0003_remove_groundwatermonitoringtubesstatic_gmn_measuring_point'),
        ('gmn_aanlevering', '0002_alter_groundwatermonitoringnet_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='measuringpoint',
            name='groundwater_monitoring_tube',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='gmw_aanlevering.groundwatermonitoringtubesstatic'),
        ),
    ]