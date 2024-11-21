from django.core.management.base import BaseCommand
from gmn.models import (
    GroundwaterMonitoringNet,
    MeasuringPoint,
    GroundwaterMonitoringTubeStatic,
    Subgroup,
)
import polars as pl
import os

def find_monitoring_tube(tube_str: str, subgroup = False) -> GroundwaterMonitoringTubeStatic:
    split_string = tube_str.split(sep="-")
    well_code = split_string[0]
    tube_nr = split_string[1]

    if not subgroup:
        tube = GroundwaterMonitoringTubeStatic.objects.filter(
            groundwater_monitoring_well_static__nitg_code = well_code,
            tube_number = tube_nr
        ).order_by('groundwater_monitoring_tube_static_id').first()
    else:
        tube = GroundwaterMonitoringTubeStatic.objects.filter(
            groundwater_monitoring_well_static__nitg_code = well_code,
            subgroup = subgroup,
            tube_number = tube_nr
        ).order_by('groundwater_monitoring_tube_static_id').first()
    return tube

def create_measuring_point (gmn: GroundwaterMonitoringNet, tube: GroundwaterMonitoringTubeStatic, subgroup = False) -> MeasuringPoint:
    if not subgroup:
        measuring_point = MeasuringPoint.objects.update_or_create(
            gmn = gmn,
            groundwater_monitoring_tube = tube,
            code = tube.__str__()
        )[0]
    else:
        measuring_point = MeasuringPoint.objects.update_or_create(
            gmn = gmn,
            groundwater_monitoring_tube = tube,
            subgroup = subgroup,
            code = tube.__str__()
        )[0]
    return measuring_point

def find_measuringpoint(gmn: GroundwaterMonitoringNet, tube: GroundwaterMonitoringTubeStatic) -> MeasuringPoint:
    measuring_point = MeasuringPoint.objects.filter(
        gmn = gmn,
        groundwater_monitoring_tube = tube,
    ).first()
    return measuring_point

def update_or_create_meetnet(df: pl.DataFrame, meetnet_naam: str, ouput_path: str) -> None:
    groundwater_aspect = "kwaliteit"

    gmn = GroundwaterMonitoringNet.objects.update_or_create(
        name = meetnet_naam,
        deliver_to_bro = False,
        description = "Gemaakt voor het inspoelen van KRW en PMG kwaliteit en kwantiteit per jaar",
        quality_regime = "IMBRO/A",
        delivery_context = "waterwetPeilbeheer",
        monitoring_purpose = "strategischBeheerKwantiteitRegionaal",
        groundwater_aspect = groundwater_aspect,
    )[0]

    # create subgroups
    subgroep_P2 = Subgroup.objects.update_or_create(
        gmn = gmn,
        name = meetnet_naam+"_Perceel_2",
    )[0]
    subgroep_P3 = Subgroup.objects.update_or_create(
        gmn = gmn,
        name = meetnet_naam+"_Perceel_3",
    )[0]
    subgroep_P4 = Subgroup.objects.update_or_create(
        gmn = gmn,
        name = meetnet_naam+"_Perceel_4",
    )[0]
    subgroep_P5 = Subgroup.objects.update_or_create(
        gmn = gmn,
        name = meetnet_naam+"_Perceel_5",
    )[0]
    
    # creeër een lege dataframe die gevuld wordt met informatie welke putten en peilbuizen succesvol zijn toegevoegd aan een meetnet
    df_ouput = pl.DataFrame({'put':[], 'peilbuis':[], 'in BRO':[]}, schema={'put':pl.String, 'peilbuis':pl.String, 'in BRO':pl.Int64})

    print('')
    print(f'{meetnet_naam} zou {len(df)} peilbuizen moeten bevatten')

    done = 0

    for row in df.iter_rows(named=True):
        # to catch if the NITGcode is incorrect and does not contain
        try:
            tube = find_monitoring_tube(row["NITGcode"])
        except:
            print(f"NITGcode: {row['NITGcode']} is of incorrect format")
            continue

        split_string = row['NITGcode'].split(sep="-")
        well_code = split_string[0]
        tube_nr = split_string[1]

        p1, p2, p3, p4, p5 = 0, 0, 0, 0, 0

        # if the tube exists
        if tube:
            
            p1, p2, p3, p4, p5 = "-", "-", "-", "-", "-"

            # find if the measuring_point already exists for this gmn and tube, main group
            measuring_point = find_measuringpoint(gmn, tube)
            # if so, print that it is already in the gmn and don't add a new measuring point with update_or_create()
            if measuring_point:
                p1 = "A"
            # if no measuring_point exists yet for this gmn and tube, create it
            if not measuring_point:
                measuring_point = create_measuring_point(gmn, tube)
                p1 = "C"


            # add subgroups to measuring_point if needed
            if row["Perceel 2"] == 1:
                # find if the measuring_point already has this subgroup
                if measuring_point.subgroup.filter(id=subgroep_P2.id).exists():
                    # if so, print that it was already in
                    p2 = "A"
                else:
                    # else, add it and print that it was created
                    measuring_point.subgroup.add(subgroep_P2)
                    p2 = "C"

            if row["Perceel 3"] == 1:
                # find if the measuring_point already has this subgroup
                if measuring_point.subgroup.filter(id=subgroep_P3.id).exists():
                    # if so, print that it was already in
                    p3 = "A"
                else:
                    # else, add it and print that it was created
                    measuring_point.subgroup.add(subgroep_P3)
                    p3 = "C"

            if row["Perceel 4"] == 1:
                # find if the measuring_point already has this subgroup
                if measuring_point.subgroup.filter(id=subgroep_P4.id).exists():
                    # if so, print that it was already in
                    p4 = "A"
                else:
                    # else, add it and print that it was created
                    measuring_point.subgroup.add(subgroep_P4)
                    p4 = "C"

            if row["Perceel 5"] == 1:
                # find if the measuring_point already has this subgroup
                if measuring_point.subgroup.filter(id=subgroep_P5.id).exists():
                    # if so, print that it was already in
                    p5 = "A"
                else:
                    # else, add it and print that it was created
                    measuring_point.subgroup.add(subgroep_P5)
                    p5 = "C"

            new_row = [{'put':well_code, 'peilbuis':tube_nr, 'in BRO':1}]

        else:
            new_row = [{'put':well_code, 'peilbuis':tube_nr, 'in BRO':0}]
        

        print(f"{well_code}-{tube_nr}: \tP1:{p1}\tP2:{p2}\tP3:{p3}\tP4:{p4}\tP5:{p5},")
        new_df = pl.DataFrame(new_row)
        df_ouput.extend(new_df)

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
        if not os.path.isdir(csv_path):
            raise ValueError("Invalid path to csv's supplied")
        if not os.path.isdir(output_path):
            raise ValueError('Invalid output path supplied')
        

        df_2021 = pl.read_csv(csv_path + "\GWMeetnetZld Bemonsteringsronde 2021 tbv json FieldForm.csv", ignore_errors=True)
        df_2024 = pl.read_csv(csv_path + "\Bijlage 1 GWMeetnetZld Bemonsteringsronde 2024 tbv offerte.csv", ignore_errors=True)

        df_2024 = df_2024.rename({"P1": "Perceel 1", "P2": "Perceel 2", "P3": "Perceel 3", "P4": "Perceel 4", "P5":"Perceel 5"})


        print("A meaning it is already in the gmn (or gmn with subgroup), C that it is created")
        print("0 meaning that the tube was not found, - that the tube was found but nothing had to be done for this subgroup")
        update_or_create_meetnet(df_2024, "GAR_2024", output_path)

        print("")
        print("")
        print("A meaning it is already in the gmn (or gmn with subgroup), C that it is created")
        print("0 meaning that the tube was not found, - that the tube was found but nothing had to be done for this subgroup")
        update_or_create_meetnet(df_2021, "GAR_2021", output_path)