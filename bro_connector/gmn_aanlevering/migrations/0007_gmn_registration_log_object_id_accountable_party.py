# Generated by Django 4.0.3 on 2023-10-23 13:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gmn_aanlevering', '0006_rename_gmw_registration_log_gmn_registration_log'),
    ]

    operations = [
        migrations.AddField(
            model_name='gmn_registration_log',
            name='object_id_accountable_party',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]