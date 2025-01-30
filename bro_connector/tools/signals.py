from django.db.models.signals import (
    pre_save,
    post_save,
)
from datetime import datetime, timedelta
from .models import GLDImport
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from io import BytesIO
import csv
import zipfile
import pandas as pd
from gld.models import Observation, MeasurementTvp, ObservationProcess, ObservationMetadata

@receiver(pre_save, sender=GLDImport)
def validate_and_process_file(sender, instance: GLDImport, **kwargs):
    # Reset the report field to start fresh for each save attempt
    instance.report = """"""  
    instance.validated = True
    
    if not instance.file:
        instance.validated = False
        instance.report += f"Geen bestand geupload. Alleen ZIP- of CSV-bestanden zijn toegestaan.\n"
    elif instance.file.name.endswith('.zip'):
        process_zip_file(instance)  # Process the ZIP file and update 'instance' as needed
    elif instance.file.name.endswith('.csv'):
        process_csv_file(instance)  # Process the CSV file and update 'instance' as needed
    else:
        instance.validated = False
        instance.report += f"Ongeldig bestandstype. Alleen ZIP- of CSV-bestanden zijn toegestaan.\n"    

    # Log the validated state
    # instance.report += f"instance.validated = {instance.validated}\n"

# @receiver(post_save, sender=GLDImport)
# def show_message(sender, instance: GLDImport, **kwargs):
#     if not instance.validated:
#         raise ValidationError("importeren niet gelukt, check logging")

def process_zip_file(instance: GLDImport):
    # Read ZIP file
    zip_buffer = BytesIO(instance.file.read())
    try:
        with zipfile.ZipFile(zip_buffer) as zip_file:
            # Get all files inside the ZIP
            all_files = zip_file.namelist()
            
            # Filter out CSV files
            csv_files = [f for f in all_files if f.endswith('.csv')]
            
            # Identify non-CSV files
            non_csv_files = [f for f in all_files if not f.endswith('.csv')]

            if not csv_files:
                instance.report += "Geen CSV-bestanden gevonden in het ZIP-bestand.\n"
                instance.validated = False
                
            if non_csv_files:
                instance.report += f"Niet-CSV bestanden in ZIP: {', '.join(non_csv_files)}\n" 

            for filename in csv_files:
                with zip_file.open(filename) as csv_file:
                    validate_csv(csv_file, filename, instance)

    except zipfile.BadZipFile:
        instance.report += "Ongeldig ZIP-bestand.\n"
        instance.validated = False
    finally:
        zip_buffer.close()


def process_csv_file(instance: GLDImport):
    # Validate CSV file
    validate_csv(instance.file, instance.file.name, instance)

    if instance.validated:
        # Create ObservationProces
        Obs_Pro = ObservationProcess.objects.update_or_create(
            process_reference = instance.process_reference,
            measurement_instrument_type = instance.measurement_instrument_type,
            air_pressure_compensation_type = instance.air_pressure_compensation_type,
            process_type = instance.process_type,
            evaluation_procedure = instance.evaluation_procedure,
        )[0]

        # Create ObservationMetadata
        Obs_Meta = ObservationMetadata.objects.update_or_create(
            date_stamp = datetime.today(), # creatiedatum van de metadata over de observatie
            observation_type = instance.observation_type,
            status = instance.status,
            responsible_party = instance.responsible_party,
        )[0]

        # Create Observation
        Obs = Observation.objects.update_or_create(
            observation_metadata = Obs_Meta,
            observation_process = Obs_Pro,
            # observation_starttime = , # DateTimeField: first observation
            # observation_endtime = , # DateTimeField: last observation

            # observationperiod = observation_endtime - observation_starttime, # TimeDelta object: De periode waarover de tijd-meetwaardereeks, die het resultaat is van de observatie, van toepassing is.

            # result_time notes:
            # Bij een controlemeting, is dit het tijdstip waarop de meting is uitgevoerd.
            # Bij een reguliere tijd-meetwaardereeks met een mate beoordeling:
            # voorlopig, is dit het tijdstip van de laatste meting van de reeks.
            # Bij een volledig beoordeelde meetreeks is dit het tijdstip waarop de beoordeling is afgerond.
            # Niet bedoeld wordt het tijdstip waarop de resultaten worden aangeboden bij het bronhouderportaal of de LV-BRO.
            # Dit is in WaterML een verplicht attribuut.
            # result_time = ,
            
            # up_to_date_in_bro = False,
        )[0]

        instance.executed = True
        instance.name = f"({Obs_Meta.date_stamp.strftime('%Y-%m-%d')}) - ({instance.file.name})"
    else:
        instance.name = f"({datetime.today().strftime('%Y-%m-%d')}) - ({instance.file.name})"


def validate_csv(file, filename: str, instance: GLDImport):
    try:
        reader = pd.read_csv(file)
        required_columns = ['time', 'value']
        missing_columns = [col for col in required_columns if col not in reader.columns]
        if missing_columns:
            instance.validated = False
            instance.report += f"Missende verplichte kolommen in {filename}: {', '.join(missing_columns)}\n"
        
        # Check if CSV has any rows
        if reader.empty:
            instance.validated = False
            instance.report += f"{filename} bevat geen gegevens.\n"
        
        # Validate 'time' column format
        if 'time' in reader.columns:
            try:
                reader['time'] = pd.to_datetime(reader['time'], errors='raise')  # This will raise an error if invalid format
            except Exception as e:
                instance.validated = False
                instance.report += f"Fout in 'time' kolom van {filename}: {str(e)}\n"
        
        # Validate 'value' column format (numeric values)
        if 'value' in reader.columns:
            if not pd.to_numeric(reader['value'], errors='coerce').notnull().all():  # Check if all values are numeric
                instance.validated = False
                instance.report += f"Fout in 'value' kolom van {filename}: Bevat niet-numerieke waarden.\n"
        
    except Exception as e:
        instance.validated = False
        instance.report += f"CSV processing error in {filename}: {e}\n"
    





