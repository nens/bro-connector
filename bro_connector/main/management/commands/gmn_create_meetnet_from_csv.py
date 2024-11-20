from django.core.management.base import BaseCommand
from gmn.models import (
    GroundwaterMonitoringNet,
    MeasuringPoint,
    GroundwaterMonitoringTubeStatic,
)
import polars as pl
import os

def find_monitoring_tube(tube_str: str) -> GroundwaterMonitoringTubeStatic:
    split_string = tube_str.split(sep="-")
    well_code = split_string[0]
    tube_nr = split_string[1]

    # print(f'well: {well_code}; tube_nr: {tube_nr}.')

    tube = GroundwaterMonitoringTubeStatic.objects.filter(
        groundwater_monitoring_well_static__nitg_code = well_code,
        tube_number = tube_nr
    ).order_by('groundwater_monitoring_tube_static_id').first()
    return tube

def find_measuringpoint(gmn: GroundwaterMonitoringNet, tube: GroundwaterMonitoringTubeStatic) -> MeasuringPoint:
    measuring_point = MeasuringPoint.objects.filter(
        gmn = gmn,
        groundwater_monitoring_tube = tube,
    ).first()
    return measuring_point

def update_or_create_meetnet(df: pl.DataFrame, meetnet_naam: str, ouput_path: str) -> None:
    if "kwal" in meetnet_naam:
        groundwater_aspect = "kwaliteit"
    if "kwan" in meetnet_naam:
        groundwater_aspect = "kwantiteit"

    gmn = GroundwaterMonitoringNet.objects.update_or_create(
        name = meetnet_naam,
        deliver_to_bro = False,
        description = "Gemaakt voor het inspoelen van KRW en PMG kwaliteit en kwantiteit per jaar",
        quality_regime = "IMBRO/A",
        delivery_context = "waterwetPeilbeheer",
        monitoring_purpose = "strategischBeheerKwantiteitRegionaal",
        groundwater_aspect = groundwater_aspect,
    )[0]
    
    # creeër een lege dataframe die gevuld wordt met informatie welke putten en peilbuizen succesvol zijn toegevoegd aan een meetnet
    df_ouput = pl.DataFrame({'put':[], 'peilbuis':[], 'in BRO':[]}, schema={'put':pl.String, 'peilbuis':pl.String, 'in BRO':pl.Int64})

    # filter op peilbuizen die in meetnet zitten
    df_filtered = df.filter(pl.col(meetnet_naam) == 1)
    print('')
    print(f'{meetnet_naam} zou {len(df_filtered)} peilbuizen moeten bevatten')

    already_in_meetnet = 0
    
    for row in df_filtered.iter_rows(named=True):
        tube = find_monitoring_tube(row["unicode"])
        split_string = row['unicode'].split(sep="-")
        well_code = split_string[0]
        tube_nr = split_string[1]
        # if the tube exists
        if tube:
            # find if the measuring_point already exists for this gmn and tube
            measuring_point = find_measuringpoint(gmn, tube)
            # if so, print that it is already in the gmn and don't add a new measuring point with update_or_create()
            if measuring_point:
                # print(f'well: {well_code}; tube_nr: {tube_nr} \t already in gmn.')
                already_in_meetnet += 1
            # if no measuring_point exists yet for this gmn and tube, create it
            else:
                # print(f'well: {well_code}; tube_nr: {tube_nr} \t not in gmn.')
                measuring_point = MeasuringPoint.objects.update_or_create(
                    gmn = gmn,
                    groundwater_monitoring_tube = tube,
                    code = tube.__str__()
                )[0]
            new_row = [{'put':well_code, 'peilbuis':tube_nr, 'in BRO':1}]

        else:
            new_row = [{'put':well_code, 'peilbuis':tube_nr, 'in BRO':0}]
        
        new_df = pl.DataFrame(new_row)
        df_ouput.extend(new_df)

    path = ouput_path + f"\{meetnet_naam}.csv"
    df_ouput.write_csv(path, separator=',')

    print("")
    print(f'voor {len(df_ouput)} putten werd een poging gedaan om het toe te voegen aan het meetnet')
    print(f'bij {df_ouput.select(pl.sum("in BRO")).item()} is dit ook daadwerkelijk gelukt waarvan {already_in_meetnet} er al in stonden')

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
            help="Het path naar de CSV met informatie over de meetnetten.",
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

        column_name_list = ['pmg_kwantiteit', 'krw_kwantiteit', 'pmg_kwal_2006', 'krw_kwal_2006', 'pmg_kwal_2015', 'krw_kwal_2015', 'pmg_kwal_2012', 'krw_kwal_2012', 'pmg_kwal_2017', 'krw_kwal_2017', 'krw_kwantiteit2019']

        for c in column_name_list:
            update_or_create_meetnet(df, c, output_path)