# Generated by Django 4.0.3 on 2024-02-08 09:02

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('gmw', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='GroundwaterMonitoringNet',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('deliver_to_bro', models.BooleanField(null=True)),
                ('gmn_bro_id', models.CharField(blank=True, editable=False, max_length=255, null=True, verbose_name='Broid GMN')),
                ('delivery_accountable_party', models.CharField(max_length=255, null=True)),
                ('delivery_responsible_party', models.CharField(max_length=255, null=True)),
                ('quality_regime', models.CharField(choices=[('IMBRO', 'IMBRO'), ('IMBRO/A', 'IMBRO/A')], max_length=255, null=True)),
                ('object_id_accountable_party', models.CharField(max_length=255, null=True)),
                ('name', models.CharField(max_length=255, null=True, verbose_name='Naam')),
                ('delivery_context', models.CharField(choices=[('waterwetStrategischGrondwaterbeheer', 'waterwetStrategischGrondwaterbeheer'), ('waterwetGrondwaterzorgplicht', 'waterwetGrondwaterzorgplicht'), ('waterwetOnttrekkingInfiltratie', 'waterwetOnttrekkingInfiltratie'), ('waterwetPeilbeheer', 'waterwetPeilbeheer'), ('waterwetWaterstaatswerkAanlegWijziging', 'waterwetWaterstaatswerkAanlegWijziging'), ('waterwetWaterstaatswerkIngreep', 'waterwetWaterstaatswerkIngreep'), ('waterwetWaterstaatswerkBeheer', 'waterwetWaterstaatswerkBeheer'), ('kaderrichtlijnWater', 'kaderrichtlijnWater'), ('waterschapswet', 'waterschapswet'), ('drinkwaterwet', 'drinkwaterwet'), ('ontgrondingenwet', 'ontgrondingenwet'), ('wetNatuurbescherming', 'wetNatuurbescherming')], max_length=235, verbose_name='Kader aanlevering')),
                ('monitoring_purpose', models.CharField(choices=[('strategischBeheerKwaliteitLandelijk', 'strategischBeheerKwaliteitLandelijk'), ('strategischBeheerKwantiteitLandelijk', 'strategischBeheerKwantiteitLandelijk'), ('strategischBeheerKwaliteitRegionaal', 'strategischBeheerKwaliteitRegionaal'), ('strategischBeheerKwantiteitRegionaal', 'strategischBeheerKwantiteitRegionaal'), ('beheersingStedelijkGebied', 'beheersingStedelijkGebied'), ('gevolgenOnttrekkingKwaliteit', 'gevolgenOnttrekkingKwaliteit'), ('gevolgenOnttrekkingKwantiteit', 'gevolgenOnttrekkingKwantiteit'), ('gevolgenPeilbeheer', 'gevolgenPeilbeheer'), ('gevolgenWaterstaatswerkKwaliteit', 'gevolgenWaterstaatswerkKwaliteit'), ('gevolgenWaterstaatswerkKwantiteit', 'gevolgenWaterstaatswerkKwantiteit'), ('waterstaatswerkBeheerKwaliteit', 'waterstaatswerkBeheerKwaliteit'), ('waterstaatswerkBeheerKwantiteit', 'waterstaatswerkBeheerKwantiteit'), ('veiligstellingGrondwaterKwaliteit', 'veiligstellingGrondwaterKwaliteit'), ('veiligstellingGrondwaterKwantiteit', 'veiligstellingGrondwaterKwantiteit'), ('waterstaatkundigeVerzorgingKwaliteit', 'waterstaatkundigeVerzorgingKwaliteit'), ('waterstaatkundigeVerzorgingKwantiteit', 'waterstaatkundigeVerzorgingKwantiteit'), ('veiligstellingDrinkwatervoorzieningKwaliteit', 'veiligstellingDrinkwatervoorzieningKwaliteit'), ('veiligstellingDrinkwatervoorzieningKwantiteit', 'veiligstellingDrinkwatervoorzieningKwantiteit'), ('gevolgenOntgronding', 'gevolgenOntgronding'), ('natuurbescherming', 'natuurbescherming'), ('natuurbeheer', 'natuurbeheer')], max_length=235, verbose_name='Monitoringdoel')),
                ('groundwater_aspect', models.CharField(choices=[('kwaliteit', 'kwaliteit'), ('kwantiteit', 'kwantiteit')], max_length=235, verbose_name='Grondwateraspect')),
                ('start_date_monitoring', models.DateField(null=True)),
                ('end_date_monitoring', models.DateField(blank=True, help_text='Als een Meetnet verwijderd moet worden uit de BRO, verwijder het dan NIET uit de BRO-Connector. Vul dit veld in om de verwijdering uit de BRO te realiseren.', null=True)),
                ('removed_from_BRO', models.BooleanField(default=False, editable=False, null=True)),
            ],
            options={
                'verbose_name': 'Groundwatermonitoring Meetnet',
                'verbose_name_plural': 'Groundwatermonitoring Meetnetten',
                'db_table': 'gmn"."groundwater_monitoring_net',
                'ordering': ('name',),
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='MeasuringPoint',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(blank=True, editable=False, max_length=255, null=True, verbose_name='Meetpunt naam')),
                ('synced_to_bro', models.BooleanField(default=False, editable=False, null=True)),
                ('added_to_gmn_date', models.DateField(null=True)),
                ('deleted_from_gmn_date', models.DateField(blank=True, help_text='Als een Meetpunt van een meetnet verwijderd moet worden, verwijder het object dan NIET uit de BRO-Connector, maar vul dit veld in!', null=True)),
                ('removed_from_BRO_gmn', models.BooleanField(default=False, editable=False, null=True)),
                ('gmn', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='gmn.groundwatermonitoringnet')),
                ('groundwater_monitoring_tube', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='gmw.groundwatermonitoringtubestatic')),
            ],
            options={
                'verbose_name': 'Meetpunt',
                'verbose_name_plural': 'Meetpunten',
                'db_table': 'gmn"."measuring_point',
                'ordering': ('code',),
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='IntermediateEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event_type', models.CharField(choices=[('GMN_StartRegistration', 'Start Registration'), ('GMN_MeasuringPoint', 'Add MeasuringPoint'), ('GMN_MeasuringPointEndDate', 'Remove MeasuringPoint'), ('GMN_Closure', 'GMN Closure')], max_length=25, null=True)),
                ('event_date', models.DateField(null=True)),
                ('synced_to_bro', models.BooleanField(default=False, null=True)),
                ('deliver_to_bro', models.BooleanField(default=True, null=True)),
                ('gmn', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='gmn.groundwatermonitoringnet')),
                ('measuring_point', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='gmn.measuringpoint')),
            ],
            options={
                'verbose_name': 'Tussentijdse Gebeurtenis',
                'db_table': 'gmn"."intermediate_event',
                'ordering': ('event_date',),
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='gmn_bro_sync_log',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_modified', models.DateField(blank=True, null=True)),
                ('event_type', models.CharField(choices=[('GMN_StartRegistration', 'Start Registration'), ('GMN_MeasuringPoint', 'Add MeasuringPoint'), ('GMN_MeasuringPointEndDate', 'Remove MeasuringPoint'), ('GMN_Closure', 'GMN Closure')], max_length=25, null=True)),
                ('gmn_bro_id', models.CharField(blank=True, max_length=254, null=True)),
                ('object_id_accountable_party', models.CharField(blank=True, max_length=255, null=True)),
                ('validation_status', models.CharField(blank=True, max_length=254, null=True)),
                ('levering_id', models.CharField(blank=True, max_length=254, null=True)),
                ('levering_status', models.CharField(blank=True, choices=[('0', 'Nog niet aangeleverd'), ('1', '1 keer gefaald'), ('2', '2 keer gefaald'), ('3', '3 keer gefaald'), ('4', 'Succesvol aangeleverd')], default=0, max_length=10, null=True)),
                ('levering_status_info', models.CharField(blank=True, max_length=254, null=True)),
                ('comments', models.CharField(blank=True, max_length=10000, null=True)),
                ('last_changed', models.CharField(blank=True, max_length=254, null=True)),
                ('corrections_applied', models.BooleanField(blank=True, null=True)),
                ('timestamp_end_registration', models.DateTimeField(blank=True, null=True)),
                ('quality_regime', models.CharField(blank=True, max_length=254, null=True)),
                ('file', models.CharField(blank=True, max_length=254, null=True)),
                ('process_status', models.CharField(blank=True, max_length=254, null=True)),
                ('measuringpoint', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='gmn.measuringpoint')),
            ],
            options={
                'verbose_name': 'GMN Synchronisatie Log',
                'verbose_name_plural': 'GMN Synchronisatie Logs',
                'db_table': 'gmn"."gmn_bro_sync_log',
            },
        ),
    ]
