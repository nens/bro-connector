# Generated by Django 4.0.3 on 2023-10-19 09:29

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('gmn_aanlevering', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='groundwatermonitoringnet',
            options={'managed': True, 'ordering': ('name',), 'verbose_name': 'Groundwater Monitoring Network', 'verbose_name_plural': 'Groundwater Monitoring Networks (2.1)'},
        ),
        migrations.AlterModelOptions(
            name='intermediateevent',
            options={'managed': True, 'ordering': ('event_date',), 'verbose_name': 'GMN Intermediate Event'},
        ),
        migrations.AlterModelOptions(
            name='measuringpoint',
            options={'managed': True, 'ordering': ('code',), 'verbose_name': 'GMN Meetpunt', 'verbose_name_plural': 'GMN Meetpunt (3.1)'},
        ),
    ]