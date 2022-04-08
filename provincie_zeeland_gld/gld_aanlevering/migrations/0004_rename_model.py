from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('gld_aanlevering', '0003_remove_measurementtimeseries_filter_nr_and_more'),
    ]

    operations = [
        migrations.RenameModel("TypeMeasementInstrumentType", "TypeMeasurementInstrumentType")
    ]
