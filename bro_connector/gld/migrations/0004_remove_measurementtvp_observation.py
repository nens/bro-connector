# Generated by Django 4.0.3 on 2023-11-28 15:18

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('gld', '0003_groundwaterleveldossier_tube_number_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='measurementtvp',
            name='observation',
        ),
    ]