from django.db.models.signals import (
    pre_save,
)
from .models import GLDImport
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from io import BytesIO
import csv
import zipfile

@receiver(pre_save, sender=GLDImport)
def validate_and_process_file(sender, instance, **kwargs):
    # Ensure the file exists
    if not instance.file:
        raise ValidationError("Geen file geupload.")
    
    if instance.file.name.endswith('.zip'):
        process_zip_file(instance)
    elif instance.file.name.endswith('.csv'):
        process_csv_file(instance)
    else:
        raise ValidationError("Ongeldig bestandstype. Alleen ZIP- of CSV-bestanden zijn toegestaan.")    
    
def process_zip_file(instance):
    # Read ZIP file
    zip_buffer = BytesIO(instance.file.read())
    try:
        with zipfile.ZipFile(zip_buffer) as zip_file:
            # Check for CSV files inside the ZIP
            csv_files = [f for f in zip_file.namelist() if f.endswith('.csv')]
            if not csv_files:
                raise ValidationError("Geen CSV-bestanden gevonden in het ZIP-bestand.")
            for filename in csv_files:
                with zip_file.open(filename) as csv_file:
                    validate_csv(csv_file)
    except zipfile.BadZipFile:
        raise ValidationError("Ongeldig ZIP-bestand.")
    finally:
        zip_buffer.close()

def process_csv_file(instance):
    # Validate CSV file
    validate_csv(instance.file)

def validate_csv(file):
    try:
        reader = csv.DictReader(file.read().decode('utf-8').splitlines())
        # required_columns = ['filter', # first required to help find the correct tube
        #                     'bro_id'
        #                     'nitg',
        #                     'x',
        #                     'y',
        #                     # namen vragen, overgenomen uit GLDImport
        #                     'organisatie',
        #                     'observation_type',
        #                     'status',
        #                     'process_reference',
        #                     'measurement_instrument_type',
        #                     'air_pressure_compensation_type',
        #                     'process_type',
        #                     'evaluation_procedure',
        #                     'validated',
        #                     'executed',
        #                     'report']
        required_columns = ['time', 'value']
        missing_columns = [col for col in required_columns if col not in reader.fieldnames]
        if missing_columns:
            raise ValidationError(f"Missende verplichte kolommen: {', '.join(missing_columns)}")
    except Exception as e:
        raise ValidationError(f"CSV processing error: {e}") 





