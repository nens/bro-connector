# Generated by Django 4.0.3 on 2024-02-08 09:02

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('gmn', '0001_initial'),
        ('gmw', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='CalculatedFormationresistanceMethod',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('responsible_party', models.CharField(max_length=200, null=True)),
                ('assessment_procedure', models.CharField(choices=[('QCProtocolFormatieweerstandonderzoek2021', 'QCProtocolFormatieweerstandonderzoek2021'), ('oordeelDeskundige', 'oordeelDeskundige'), ('vergelijkVoorgaandeMetingen', 'vergelijkVoorgaandeMetingen'), ('onbekend', 'onbekend')], max_length=235)),
            ],
            options={
                'verbose_name_plural': 'Calculated Formationresistance Method',
                'db_table': 'frd"."calculated_formationresistance_method',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='ElectrodePair',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
            options={
                'verbose_name_plural': 'Electrode Pair',
                'db_table': 'frd"."electrode_pair',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='ElectromagneticMeasurementMethod',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('measurement_date', models.DateField(blank=True)),
                ('measuring_responsible_party', models.TextField(blank=True, max_length=200)),
                ('measuring_procedure', models.CharField(choices=[('geen', 'geen'), ('werkinstructieWaternet', 'werkinstructieWaternet'), ('manualOpnameZoutwachterOasen', 'manualOpnameZoutwachterOasen'), ('onbekend', 'onbekend')], max_length=235)),
                ('assessment_procedure', models.CharField(choices=[('QCProtocolFormatieweerstandonderzoek2021', 'QCProtocolFormatieweerstandonderzoek2021'), ('oordeelDeskundige', 'oordeelDeskundige'), ('vergelijkVoorgaandeMetingen', 'vergelijkVoorgaandeMetingen'), ('onbekend', 'onbekend')], max_length=235)),
            ],
            options={
                'verbose_name_plural': 'Electromagnetic Measurement Method',
                'db_table': 'frd"."electromagnetic_measurement_method',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='FormationResistanceDossier',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('frd_bro_id', models.CharField(blank=True, max_length=200, null=True, verbose_name='Bro-ID FRD')),
                ('delivery_accountable_party', models.CharField(max_length=200, null=True)),
                ('object_id_accountable_party', models.CharField(max_length=200, null=True)),
                ('delivery_responsible_party', models.CharField(max_length=255, null=True)),
                ('quality_regime', models.CharField(choices=[('IMBRO', 'IMBRO'), ('IMBRO/A', 'IMBRO/A')], max_length=255, null=True)),
                ('assessment_type', models.CharField(blank=True, choices=[('elektromagnetischeBepaling', 'elektromagnetischeBepaling'), ('geoohmkabelBepaling', 'geoohmkabelBepaling')], max_length=255, null=True)),
                ('deliver_to_bro', models.BooleanField(null=True)),
                ('groundwater_monitoring_net', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='gmn.groundwatermonitoringnet')),
                ('groundwater_monitoring_tube', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='gmw.groundwatermonitoringtubestatic')),
            ],
            options={
                'verbose_name': 'Formationresistance Dossier',
                'verbose_name_plural': 'Formationresistance Dossier',
                'db_table': 'frd"."formationresistance_dossier',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='GeoOhmMeasurementMethod',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('bro_id', models.CharField(blank=True, max_length=254, null=True)),
                ('measurement_date', models.DateField(blank=True)),
                ('measuring_responsible_party', models.CharField(max_length=235)),
                ('measuring_procedure', models.CharField(choices=[('geen', 'geen'), ('werkinstructieWaternet', 'werkinstructieWaternet'), ('manualOpnameZoutwachterOasen', 'manualOpnameZoutwachterOasen'), ('onbekend', 'onbekend')], max_length=235)),
                ('assessment_procedure', models.CharField(choices=[('QCProtocolFormatieweerstandonderzoek2021', 'QCProtocolFormatieweerstandonderzoek2021'), ('oordeelDeskundige', 'oordeelDeskundige'), ('vergelijkVoorgaandeMetingen', 'vergelijkVoorgaandeMetingen'), ('onbekend', 'onbekend')], max_length=235)),
                ('formation_resistance_dossier', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='frd.formationresistancedossier')),
            ],
            options={
                'verbose_name_plural': 'Geo Ohm Measurement Method',
                'db_table': 'frd"."geo_ohm_measurement_method',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='GMWElectrodeReference',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cable_number', models.IntegerField(blank=True, null=True)),
                ('electrode_number', models.IntegerField(blank=True, null=True)),
            ],
            options={
                'verbose_name_plural': 'GMW Electrode Reference',
                'db_table': 'frd"."gmw_electrode_reference',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='MeasurementConfiguration',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('bro_id', models.CharField(blank=True, max_length=254, null=True)),
                ('configuration_name', models.CharField(max_length=40, unique=True)),
                ('flowcurrent_pair', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='flowcurrent_pair', to='frd.electrodepair')),
                ('formation_resistance_dossier', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='frd.formationresistancedossier')),
                ('measurement_pair', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='measurement_pair', to='frd.electrodepair')),
            ],
            options={
                'verbose_name_plural': 'Measurement Configuration',
                'db_table': 'frd"."measurement_configuration',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='InstrumentConfiguration',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('configuration_name', models.TextField(max_length=40)),
                ('relative_position_send_coil', models.DecimalField(blank=True, decimal_places=3, max_digits=6, null=True)),
                ('relative_position_receive_coil', models.DecimalField(blank=True, decimal_places=3, max_digits=6, null=True)),
                ('secondary_receive_coil', models.CharField(blank=True, choices=[('Indicatie', 'Indicatie'), ('Ja', 'Ja'), ('Nee', 'Nee'), ('Onbekend', 'Onbekend')], max_length=200, null=True)),
                ('relative_position_secondary_coil', models.DecimalField(blank=True, decimal_places=3, max_digits=6, null=True)),
                ('coilfrequency_known', models.CharField(blank=True, choices=[('Indicatie', 'Indicatie'), ('Ja', 'Ja'), ('Nee', 'Nee'), ('Onbekend', 'Onbekend')], max_length=200, null=True)),
                ('coilfrequency', models.DecimalField(blank=True, decimal_places=3, max_digits=6, null=True, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)])),
                ('instrument_length', models.DecimalField(blank=True, decimal_places=3, max_digits=6, null=True, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(300)])),
                ('electromagnetic_measurement_method', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='frd.electromagneticmeasurementmethod')),
                ('formation_resistance_dossier', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='frd.formationresistancedossier')),
            ],
            options={
                'verbose_name_plural': 'Instrument Configurations',
                'db_table': 'frd"."instrument_configuration',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='GeoOhmMeasurementValue',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('formationresistance', models.DecimalField(decimal_places=3, max_digits=6, validators=[django.core.validators.MinValueValidator(0)])),
                ('datetime', models.DateTimeField()),
                ('geo_ohm_measurement_method', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='frd.geoohmmeasurementmethod')),
                ('measurement_configuration', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='frd.measurementconfiguration')),
            ],
            options={
                'verbose_name_plural': 'Geo Ohm Measurement Value',
                'db_table': 'frd"."geo_ohm_measurement_value',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='FrdSyncLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('synced', models.BooleanField(default=False)),
                ('date_modified', models.DateTimeField(auto_now=True)),
                ('bro_id', models.CharField(blank=True, max_length=254, null=True)),
                ('event_type', models.CharField(choices=[('FRD_StartRegistration', 'FRD_StartRegistration'), ('FRD_GEM_MeasurementConfiguration', 'FRD_GEM_MeasurementConfiguration')], max_length=40)),
                ('process_status', models.CharField(blank=True, max_length=254, null=True)),
                ('comment', models.CharField(blank=True, max_length=10000, null=True)),
                ('xml_filepath', models.CharField(blank=True, max_length=254, null=True)),
                ('delivery_status', models.IntegerField(blank=True, choices=[(0, 'Nog niet aangeleverd'), (1, '1 keer gefaald'), (2, '2 keer gefaald'), (3, '3 keer gefaald'), (4, 'Succesvol aangeleverd')], default=0, null=True)),
                ('delivery_status_info', models.CharField(blank=True, max_length=254, null=True)),
                ('delivery_id', models.CharField(blank=True, max_length=254, null=True)),
                ('delivery_type', models.CharField(choices=[('register', 'register'), ('replace', 'replace'), ('insert', 'insert'), ('move', 'move'), ('delete', 'delete')], max_length=40)),
                ('frd', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='frd.formationresistancedossier')),
            ],
            options={
                'verbose_name': 'FRD Synchronisatie Log',
                'verbose_name_plural': 'FRD Synchronisatie Logs',
                'db_table': 'frd"."frd_sync_log',
            },
        ),
        migrations.CreateModel(
            name='FormationresistanceSeries',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('calculated_formationresistance', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='frd.calculatedformationresistancemethod')),
            ],
            options={
                'verbose_name_plural': 'Formationresistance Series',
                'db_table': 'frd"."formationresistance_series',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='FormationresistanceRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('vertical_position', models.DecimalField(decimal_places=3, max_digits=6, validators=[django.core.validators.MinValueValidator(-750), django.core.validators.MaxValueValidator(325)])),
                ('formationresistance', models.DecimalField(decimal_places=3, max_digits=6, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(10000)])),
                ('status_qualitycontrol', models.CharField(choices=[('afgekeurd', 'afgekeurd'), ('goedgekeurd', 'goedgekeurd'), ('onbeslist', 'onbeslist'), ('onbekend', 'onbekend')], max_length=235)),
                ('series', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='frd.formationresistanceseries')),
            ],
            options={
                'verbose_name_plural': 'Formationresistance Records',
                'db_table': 'frd"."formationresistance_record',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='ElectromagneticSeries',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('electromagnetic_measurement_method', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='frd.electromagneticmeasurementmethod')),
            ],
            options={
                'verbose_name_plural': 'Electromagnetic Series',
                'db_table': 'frd"."electromagnetic_series',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='ElectromagneticRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('vertical_position', models.DecimalField(decimal_places=3, max_digits=6, validators=[django.core.validators.MinValueValidator(-750), django.core.validators.MaxValueValidator(325)])),
                ('primary_measurement', models.DecimalField(decimal_places=3, max_digits=6, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(3000)])),
                ('secondary_measurement', models.DecimalField(blank=True, decimal_places=3, max_digits=6, null=True, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(3000)])),
                ('series', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='frd.electromagneticseries')),
            ],
            options={
                'verbose_name_plural': 'Electromagnetic Records',
                'db_table': 'frd"."electromagnetic_record',
                'managed': True,
            },
        ),
        migrations.AddField(
            model_name='electromagneticmeasurementmethod',
            name='formation_resistance_dossier',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='frd.formationresistancedossier'),
        ),
        migrations.AddField(
            model_name='electrodepair',
            name='elektrode1',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='electrode_one', to='frd.gmwelectrodereference'),
        ),
        migrations.AddField(
            model_name='electrodepair',
            name='elektrode2',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='electrode_two', to='frd.gmwelectrodereference'),
        ),
        migrations.AddField(
            model_name='calculatedformationresistancemethod',
            name='electromagnetic_measurement_method',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='frd.electromagneticmeasurementmethod'),
        ),
        migrations.AddField(
            model_name='calculatedformationresistancemethod',
            name='geo_ohm_measurement_method',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='frd.geoohmmeasurementmethod'),
        ),
    ]
