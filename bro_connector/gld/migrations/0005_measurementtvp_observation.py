# Generated by Django 4.0.3 on 2023-11-28 15:18

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('gld', '0004_remove_measurementtvp_observation'),
    ]

    operations = [
        migrations.AddField(
            model_name='measurementtvp',
            name='observation',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='gld.observation'),
        ),
    ]