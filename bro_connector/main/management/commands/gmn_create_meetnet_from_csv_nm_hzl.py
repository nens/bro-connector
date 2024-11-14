from django.core.management.base import BaseCommand
from gmn.models import (
    GroundwaterMonitoringNet,
    MeasuringPoint,
    GroundwaterMonitoringTubeStatic,
)
import polars as pl
import os

def find_monitoring_tube(well: str, tube: str) -> GroundwaterMonitoringTubeStatic:
    print(f'well: {well}; tube_nr: {tube}.')

    tube = GroundwaterMonitoringTubeStatic.objects.filter(
        groundwater_monitoring_well_static__nitg_code = well,
        tube_number = tube
    ).order_by('groundwater_monitoring_tube_static_id').first()
    return tube

def update_or_create_meetnet(df: pl.DataFrame, meetnet_naam: str, ouput_path: str) -> None:
    groundwater_aspect = "kwantiteit"

    gmn = GroundwaterMonitoringNet.objects.update_or_create(
        name = meetnet_naam,
        deliver_to_bro = False,
        description = "Gemaakt voor het inspoelen van KRW en PMG kwaliteit en kwantiteit per jaar",
        quality_regime = "IMBRO/A",
        delivery_context = "waterwetPeilbeheer",
        monitoring_purpose = "strategischBeheerKwantiteitRegionaal",
        groundwater_aspect = groundwater_aspect
    )[0]
    
    # creeër een lege dataframe die gevuld wordt met informatie welke putten en peilbuizen succesvol zijn toegevoegd aan een meetnet
    df_ouput = pl.DataFrame({'put':[], 'peilbuis':[], 'in BRO':[]}, schema={'put':pl.String, 'peilbuis':pl.Int64, 'in BRO':pl.Int64})

    print('')
    print(f'{meetnet_naam} zou {len(df)} peilbuizen moeten bevatten')
    
    for row in df.iter_rows(named=True):
        if row['Opgeruimd'] == 'Nee':
            well_id = row['NITG-Nr']
            tube_nr = row['Buis-Nr']
            tube = find_monitoring_tube(well_id, tube_nr)
            if tube:
                measuring_point = MeasuringPoint.objects.update_or_create(
                    gmn = gmn,
                    groundwater_monitoring_tube = tube,
                    code = tube.__str__()
                )[0]
                print(measuring_point)
                new_row = [{'put':well_id, 'peilbuis':tube_nr, 'in BRO':1}]

            else:
                new_row = [{'put':well_id, 'peilbuis':tube_nr, 'in BRO':0}]
            
            new_df = pl.DataFrame(new_row)
            df_ouput.extend(new_df)
        else:
            print(f"put {row['NITG-Nr']} is opgeruimd")

    path = ouput_path + f"\{meetnet_naam}.csv"
    df_ouput.write_csv(path, separator=',')

    print("")
    print(f'voor {len(df_ouput)} putten werd een poging gedaan om het toe te voegen aan het meetnet')
    print(f'bij {df_ouput.select(pl.sum("in BRO")).item()} is dit ook daadwerkelijk gelukt')

    print("Operatie succesvol afgerond.")




class Command(BaseCommand):
    """
    Class to:
        - set up a GMN
        - check up al existing filters in database
        - create measuringpoints for each filter.
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv",
            type=str,
            help="Het path naar de CSV met informatie over het SBB meetnet.",
        )
        parser.add_argument(
            "--output",
            type=str,
            help="Het path waar de output csv files moeten komen waar van alle putten aangegeven staat of ze aan het meetnet zijn toegevoegd",
        )
    
    def handle(self, *args, **options):
        csv_path = str(options["csv"])
        output_path = str(options["output"])
        if not csv_path or not csv_path.endswith('.csv'):
            raise ValueError('Invalid CSV-file supplied.')
        if not os.path.isdir(output_path):
            raise ValueError('Invalid output path supplied')
        
        df = pl.read_csv(csv_path, ignore_errors=True)

        # check the name of the csv file to determine if it is for Natuurmonumenten or Het Zeeuwse Landschap
        print(csv_path)
        if "Natuurmonumenten" in str(csv_path):
            print("adding Natuurmonumenten meetnet")
            update_or_create_meetnet(df, 'Natuurmonumenten', output_path)
        elif "HZL" in str(csv_path):
            print("adding Het Zeeuwse Landschap meetnet")
            update_or_create_meetnet(df, 'Het Zeeuwse Landschap', output_path)
        else:
            print("The provided csv-file does not contain Natuurmonumenten or HZL in the name, so it is unclear which meetnet to add it to")
