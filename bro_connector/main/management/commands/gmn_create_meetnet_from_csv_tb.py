from django.core.management.base import BaseCommand
from gmn.models import (
    GroundwaterMonitoringNet,
    MeasuringPoint,
    GroundwaterMonitoringTubeStatic,
    Subgroup
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

def update_or_create_meetnet(df_sbb: pl.DataFrame, df_nm: pl.DataFrame, df_hzl: pl.DataFrame, meetnet_naam: str, ouput_path: str) -> None:
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
    df_ouput = pl.DataFrame({'put':[], 'peilbuis':[], 'subgroep':[], 'in BRO':[]}, schema={'put':pl.String, 'peilbuis':pl.Int64, 'subgroep':pl.String, 'in BRO':pl.Int64})

    print('')
    print(f'{meetnet_naam} zou {len(df_sbb)+len(df_nm)+len(df_hzl)} peilbuizen moeten bevatten')
    
    # create subgroups
    subgroep_sbb = Subgroup.objects.update_or_create(
        gmn = gmn,
        name = "Staatsbosbeheer (SBB)",
    )[0]
    subgroep_nm = Subgroup.objects.update_or_create(
        gmn = gmn,
        name = "Natuurmomumenten",
    )[0]
    subgroep_hzl = Subgroup.objects.update_or_create(
        gmn = gmn,
        name = "Het Zeeuwse Landschap",
    )[0]

    for row_sbb in df_sbb.iter_rows(named=True):
        well_sbb, tube_sbb = row_sbb['put'], row_sbb['piezometer']
        tube = find_monitoring_tube(well_sbb, tube_sbb)
        if tube:
            measuring_point = MeasuringPoint.objects.update_or_create(
                gmn = gmn,
                groundwater_monitoring_tube = tube,
                subgroup = subgroep_sbb,
                code = tube.__str__()
            )[0]
            print(measuring_point)
            new_row = [{'put':well_sbb, 'peilbuis':tube_sbb, 'subgroep':subgroep_sbb.name, 'in BRO':1}]
        else:
            new_row = [{'put':well_sbb, 'peilbuis':tube_sbb, 'subgroep':subgroep_sbb.name, 'in BRO':0}]
            
        new_df = pl.DataFrame(new_row)
        df_ouput.extend(new_df)

    for row_nm in df_nm.iter_rows(named=True): 
        well_nm, tube_nm = row_nm['NITG-Nr'], row_nm['Buis-Nr']
        tube = find_monitoring_tube(well_nm, tube_nm)
        if tube:
            measuring_point = MeasuringPoint.objects.update_or_create(
                gmn = gmn,
                groundwater_monitoring_tube = tube,
                subgroup = subgroep_nm,
                code = tube.__str__()
            )[0]
            print(measuring_point)
            new_row = [{'put':well_nm, 'peilbuis':tube_nm, 'subgroep':subgroep_nm.name, 'in BRO':1}]
        else:
            new_row = [{'put':well_nm, 'peilbuis':tube_nm, 'subgroep':subgroep_nm.name, 'in BRO':0}]
            
        new_df = pl.DataFrame(new_row)
        df_ouput.extend(new_df)


    for row_hzl in df_hzl.iter_rows(named=True):
        well_hzl, tube_hzl = row_hzl['NITG-Nr'], row_hzl['Buis-Nr']
        tube = find_monitoring_tube(well_hzl, tube_hzl)
        if tube:
            measuring_point = MeasuringPoint.objects.update_or_create(
                gmn = gmn,
                groundwater_monitoring_tube = tube,
                subgroup = subgroep_hzl,
                code = tube.__str__()
            )[0]
            print(measuring_point)
            new_row = [{'put':well_hzl, 'peilbuis':tube_hzl, 'subgroep':subgroep_hzl.name, 'in BRO':1}]
        else:
            new_row = [{'put':well_hzl, 'peilbuis':tube_hzl, 'subgroep':subgroep_hzl.name, 'in BRO':0}]
            
        new_df = pl.DataFrame(new_row)
        df_ouput.extend(new_df)
        
    path = ouput_path + f"\{meetnet_naam}.csv"
    df_ouput.write_csv(path, separator=',')

    print("Operatie succesvol afgerond.")
    
    column_sum = df_ouput.select(pl.sum("in BRO")).item()

    print(column_sum, "tubes are in the BRO out of", len(df_ouput))





class Command(BaseCommand):
    """
    Class to:
        - set up a GMN
        - set up Subgroups
        - check up al existing filters in database
        - create measuringpoints for each filter.
    """
    def add_arguments(self, parser):
        parser.add_argument(
            "--csv",
            type=str,
            help="Het path naar de CSV's met informatie over het terreinbeheer meetnet.",
        )
        parser.add_argument(
            "--output",
            type=str,
            help="Het path waar de output csv files moeten komen waar van alle putten aangegeven staat of ze aan het meetnet zijn toegevoegd",
        )
    
    def handle(self, *args, **options):
        csv_path = str(options["csv"])
        output_path = str(options["output"])
        if not os.path.isdir(output_path):
            raise ValueError("Invalid path to csv's supplied")
        if not os.path.isdir(output_path):
            raise ValueError('Invalid output path supplied')
        

        # read csv's
        df_sbb = pl.read_csv(csv_path + "\SBB_peilbuizen.csv", ignore_errors=True)
        # nm en HZL zijn toegestuurd als xlsx, deze zijn omgezet naar csv
        df_nm = pl.read_csv(csv_path + "\Peilbuizen Natuurmonumenten Zeeland Dino TNO.csv", ignore_errors=True)
        df_hzl = pl.read_csv(csv_path + "\Peilbuizen HZL BRO TNO lijst.csv", ignore_errors=True)

        # filter csv's to only select tubes that need to be put into meetnet 
        df_sbb = df_sbb.filter(pl.col("status") == "Afstoten")
        df_nm = df_nm.filter(pl.col("Opgeruimd") == "Nee")
        df_hzl = df_hzl.filter(pl.col("Opgeruimd") == "Nee")

        update_or_create_meetnet(df_sbb, df_nm, df_hzl, 'terreinbeheerders', output_path)