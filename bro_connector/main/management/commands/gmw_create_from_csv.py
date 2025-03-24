from django.core.management.base import BaseCommand
from django.contrib.gis.geos import Point
from gmw.models import GroundwaterMonitoringWellStatic
from gmn.models import (
    GroundwaterMonitoringNet,
    GroundwaterMonitoringTubeStatic,
    MeasuringPoint,
)
import polars as pl
import os


def find_well(well_coordinates: Point, nitg: str) -> GroundwaterMonitoringWellStatic:
    if (nitg is not None) and (nitg != "[onbekend]"):
        well = (
            GroundwaterMonitoringWellStatic.objects.filter(nitg_code=nitg)
            .order_by("groundwater_monitoring_well_static_id")
            .first()
        )
    else:
        well = (
            GroundwaterMonitoringWellStatic.objects.filter(coordinates=well_coordinates)
            .order_by("groundwater_monitoring_well_static_id")
            .first()
        )
    return well


# make function to create gmw
def create_monitoring_well(df: pl.DataFrame):
    opgeruimd = 0
    dino = 0
    dino_e = 0
    unknown = 0
    unkown_e = 0
    surface = 0
    surface_e = 0
    normal = 0
    normal_e = 0

    groundwater_aspect = "kwantiteit"

    dino_gmn = GroundwaterMonitoringNet.objects.update_or_create(
        name="DINO",
        deliver_to_bro=False,
        description="Gemaakt voor het inspoelen van lege putten uit DINO",
        quality_regime="IMBRO/A",
        delivery_context="waterwetPeilbeheer",
        monitoring_purpose="strategischBeheerKwantiteitRegionaal",
        groundwater_aspect=groundwater_aspect,
    )[0]

    surface_gmn = GroundwaterMonitoringNet.objects.update_or_create(
        name="Oppervlakte",
        deliver_to_bro=False,
        description="Gemaakt voor het inspoelen van oppervlakte put locaties",
        quality_regime="IMBRO/A",
        delivery_context="waterwetPeilbeheer",
        monitoring_purpose="strategischBeheerKwantiteitRegionaal",
        groundwater_aspect=groundwater_aspect,
    )[0]

    unknown_gmn = GroundwaterMonitoringNet.objects.update_or_create(
        name="[onbekend] nieuw",
        deliver_to_bro=False,
        description="Gemaakt voor het inspoelen van [onbekend] putten die nog niet in de database stonden",
        quality_regime="IMBRO/A",
        delivery_context="waterwetPeilbeheer",
        monitoring_purpose="strategischBeheerKwantiteitRegionaal",
        groundwater_aspect=groundwater_aspect,
    )[0]

    for row in df.iter_rows(named=True):
        # if Opgeruimd is "Ja", the well no longer exists and should be skipped
        if row["Opgeruimd"] == "Ja":
            opgeruimd += 1
            continue
        else:
            nitg_code = row["NITG-Nr"]
            # select buis-nr, but missing in "Peilbuizen natuur.csv", so if not available, assume buis-nr = 1
            try:
                tube_nr = int(row["Buis-Nr"])
            except AttributeError:
                tube_nr = 1
            x = row["Xcoord RD"]
            y = row["Ycoord RD"]
            longitude, latitude = x, y
            point = Point(longitude, latitude)

            well = find_well(point, nitg_code)

            if well and row["NITG-Nr"] is not None:
                print(f"{x:.2f}\t{y:.2f}\t exists, NITG is:\t {row['NITG-Nr']}")
            elif well:
                print(f"{x:.2f}\t{y:.2f}\t exists, NITG is:\t None")
            else:
                print(f"{x:.2f}\t{y:.2f}\t does not exist for NITG:\t {row['NITG-Nr']}")

            # if the nitg code is empty add it to new DINO gmn.
            if (nitg_code is None) and (well is None):
                dino += 1
                # logica:
                # maak put aan, gebruik __str__() daarna om de internal_id te updaten als dat kan
                # maak één tube aan als dat nog niet erin zit
                # maak measuring point aan
                # voeg measuring point toe aan dino gmn

                well = GroundwaterMonitoringWellStatic.objects.update_or_create(
                    coordinates=point,
                    in_management=False,
                )[0]
                well.internal_id = str(well)

                tube = GroundwaterMonitoringTubeStatic.objects.update_or_create(
                    groundwater_monitoring_well_static=well, tube_number=tube_nr
                )[0]

                MeasuringPoint.objects.update_or_create(
                    gmn=dino_gmn, groundwater_monitoring_tube=tube, code=tube.__str__()
                )[0]

            elif nitg_code is None:
                dino_e += 1
                # do nothing

            # if nitg '[onbekend]', add to new unknown gmn.
            elif (nitg_code == "[onbekend]") and (well is None):
                unknown += 1
                # logica:
                # maak put aan, gebruik __str__() daarna om de internal_id te updaten als dat kan
                # maak één tube aan als dat nog niet erin zit
                # maak measuring point aan
                # voeg measuring point toe aan unknown gmn

                well = GroundwaterMonitoringWellStatic.objects.update_or_create(
                    coordinates=point,
                    in_management=False,
                )[0]
                well.internal_id = str(well)

                tube = GroundwaterMonitoringTubeStatic.objects.update_or_create(
                    groundwater_monitoring_well_static=well, tube_number=tube_nr
                )[0]

                MeasuringPoint.objects.update_or_create(
                    gmn=unknown_gmn,
                    groundwater_monitoring_tube=tube,
                    code=tube.__str__(),
                )[0]

            elif nitg_code == "[onbekend]":
                unkown_e += 1
                # do nothing

            elif (nitg_code[0] == "P") and (well is None):
                surface += 1
                # logica:
                # maak put aan, gebruik __str__() daarna om de internal_id te updaten als dat kan
                # doe ook iets met de is_surface command in gmw
                # maak één tube aan als dat nog niet erin zit
                # maak measuring point aan
                # voeg measuring point toe aan surface gmn

                well = GroundwaterMonitoringWellStatic.objects.update_or_create(
                    nitg_code=nitg_code,
                    coordinates=point,
                    in_management=False,
                )[0]
                well.internal_id = str(well)

                tube = GroundwaterMonitoringTubeStatic.objects.update_or_create(
                    groundwater_monitoring_well_static=well, tube_number=tube_nr
                )[0]

                MeasuringPoint.objects.update_or_create(
                    gmn=surface_gmn,
                    groundwater_monitoring_tube=tube,
                    code=tube.__str__(),
                )[0]

            elif nitg_code[0] == "P":
                surface_e += 1
                # do nothing

            elif (nitg_code[0] == "B") and (well is None):
                normal += 1
                # logica:
                # maak put aan, gebruik __str__() daarna om de internal_id te updaten als dat nodig is

                well = GroundwaterMonitoringWellStatic.objects.update_or_create(
                    nitg_code=nitg_code,
                    coordinates=point,
                )[0]
                well.internal_id = str(well)

            elif nitg_code[0] == "B":
                normal_e += 1
                # do nothing

    print("")
    print(f"{opgeruimd}\tputten waren opgeruimd")
    print(f"{dino}\tputten nieuw in dino gmn")
    print(f"{dino_e}\tputten al in dino gmn")
    print(f"{unknown}\tputten nieuw in unknown gmn")
    print(f"{unkown_e}\tputten al in unknown gmn")
    print(f"{surface}\tputten nieuw in surface gmn")
    print(f"{surface_e}\tputten al in surface gmn")
    print(f"{normal}\tputten nieuw met NITG code")
    print(f"{normal_e}\tputten bestonden al met NITG code")

    som = (
        opgeruimd
        + dino
        + dino_e
        + unknown
        + unkown_e
        + surface
        + surface_e
        + normal
        + normal_e
    )
    print("")
    print(f"{len(df)} lengte dataframe")
    print(f"{som} ")
    print("")


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--csv",
            type=str,
            help="Het path naar de CSV met informatie over de GMW's die toegevoegd moeten worden.",
        )

    def handle(self, *args, **options):
        csv_path = str(options["csv"])
        if not os.path.isdir(csv_path):
            raise ValueError("Invalid path to csv's supplied")

        df_1 = pl.read_csv(csv_path + "\Peilbuizen natuur.csv", ignore_errors=True)
        # this csv does not have the column "Opgeruimd" so adding it with "Nee" as value for further processing
        df_1 = df_1.with_columns(pl.lit("Nee").alias("Opgeruimd"))
        create_monitoring_well(df_1)

        df_2 = pl.read_csv(
            csv_path + "\Peilbuizen Natuurmonumenten Zeeland Dino TNO.csv",
            ignore_errors=True,
        )
        create_monitoring_well(df_2)
