# Generated by Django 4.0.3 on 2023-10-26 11:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gmn_aanlevering', '0011_gmn_registration_log_levering_status_info_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='gmn_registration_log',
            name='last_changed',
            field=models.CharField(blank=True, max_length=254, null=True),
        ),
    ]