from django.core.management.base import BaseCommand
from django.contrib.gis.geos import Point
from gmw.models import GroundwaterMonitoringWellStatic, GroundwaterMonitoringTubeStatic
from gmn.models import (
    GroundwaterMonitoringNet,
    MeasuringPoint,
)
import pandas as pd
import os


def find_well(nitg: str) -> GroundwaterMonitoringWellStatic:
    well = (
        GroundwaterMonitoringWellStatic.objects.filter(nitg_code=nitg)
        .order_by("groundwater_monitoring_well_static_id")
        .first()
    )
    return well


def find_tube(well: str, tube: str) -> GroundwaterMonitoringTubeStatic:
    tube = (
        GroundwaterMonitoringTubeStatic.objects.filter(
            groundwater_monitoring_well_static__nitg_code=well, tube_number=tube
        )
        .order_by("groundwater_monitoring_tube_static_id")
        .first()
    )
    return tube


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--csv",
            type=str,
            help="Het path naar de CSV met informatie over de in te spoelen putten.",
        )
        parser.add_argument(
            "--output",
            type=str,
            help="Het path waar de CSV geplaatst wordt met informatie over de ingespoelde putten.",
        )

    def handle(self, *args, **options):
        csv_path = str(options["csv"])
        output_path = str(options["output"])
        if not os.path.isdir(csv_path):
            raise ValueError("Invalid path to csv's supplied")
        if not os.path.isdir(output_path):
            raise ValueError("Invalid output path supplied")

        # full bounding box for Zeeland
        BBOX_SETTINGS = {
            "use_bbox": True,
            "xmin": 10000,
            "xmax": 80000,
            "ymin": 355000,
            "ymax": 420000,
        }

        dino_gmn = GroundwaterMonitoringNet.objects.filter(name="DINO").first()

        # creeër een lege dataframe die gevuld wordt met informatie welke putten en peilbuizen succesvol zijn toegevoegd aan een meetnet
        df_ouput = pd.DataFrame(
            {
                "put": [],
                "peilbuis": [],
                "put toegevoegd aan database": [],
                "peilbuis toegevoegd aan database": [],
            }
        )

        # stap 1 is overbodig door de find_well en find_tube functies
        # 1 maak een lijst van putten die in de database staan
        # wells = GroundwaterMonitoringWellStatic.objects.all()
        # well_list = [{'internal_id': well.internal_id, 'put':well.nitg_code, 'x':well.coordinates.x, 'y':well.coordinates.y} for well in wells]

        # 2 open excel met DINO putten en filter op basis van coordinaten
        DINO = pd.read_csv(
            csv_path + "\Algemene gegevens van putten in DINO (16-5-2024).csv"
        )

        # 3 is de put opgeruimd, neem deze dan niet mee
        DINO_1 = DINO[DINO["Opgeruimd"] == "Nee"]
        # 3.1 filter op basis van coordinaten
        DINO_2 = DINO_1[
            (DINO_1["X-Coordinaat (RD)"] > BBOX_SETTINGS["xmin"])
            & (DINO_1["X-Coordinaat (RD)"] < BBOX_SETTINGS["xmax"])
            & (DINO_1["Y-Coordinaat (RD)"] > BBOX_SETTINGS["ymin"])
            & (DINO_1["Y-Coordinaat (RD)"] < BBOX_SETTINGS["ymax"])
        ]
        # 3.2 staat er een opmerking, filter deze put eruit
        DINO_3 = DINO_2[DINO_2["Opmerking"].isna()]

        # 4 filter op of een rij "Provincie Zeeland" bevat als client, owner of monitor of "PRV_ZEELAND" in CAA set, NIET NODIG
        # DINO_4 = DINO_3[(DINO_3['Beherende inst. (Client)'] == 'Provincie Zeeland') |
        #                 (DINO_3['Opdrachtgevende inst. (Owner)'] == 'Provincie Zeeland') |
        #                 (DINO_3['Waarnemende inst. (Monitor)'] == 'Provincie Zeeland') |
        #                 ('PRV_ZEELAND' in DINO_3['CCA set (Bronhouder waar de put aan is voorgelegd);;'])]

        unique_wells_nitg = DINO_3["NITG-Nr"].unique()

        well_found = 0
        well_not_found = 0
        tube_found = 0
        tube_not_found = 0
        for well_nitg in unique_wells_nitg:
            DINO_5 = DINO_3[DINO_3["NITG-Nr"] == well_nitg]

            well = find_well(well_nitg)

            if well:  # if a well is found
                """
                1. go over all tubes of this well in the DINO document and see if you can find them
                    1.1 if a tube is not found, add it, else do nothing
                """
                for i in range(len(DINO_5)):
                    dino_row = DINO_5.iloc[i]
                    tube = find_tube(dino_row["NITG-Nr"], dino_row["Buis-Nr"])
                    if tube:  # tube found
                        output_row = {
                            "put": dino_row["NITG-Nr"],
                            "peilbuis": dino_row["Buis-Nr"],
                            "put toegevoegd aan database": "nee",
                            "peilbuis toegevoegd aan database": "nee",
                        }
                        df_ouput = pd.concat(
                            [df_ouput, pd.DataFrame([output_row])], ignore_index=True
                        )
                        tube_found += 1
                    else:  # tube not found
                        tube_not_found += 1
                        output_row = {
                            "put": dino_row["NITG-Nr"],
                            "peilbuis": dino_row["Buis-Nr"],
                            "put toegevoegd aan database": "nee",
                            "peilbuis toegevoegd aan database": "ja",
                        }
                        df_ouput = pd.concat(
                            [df_ouput, pd.DataFrame([output_row])], ignore_index=True
                        )

                        tube = GroundwaterMonitoringTubeStatic.objects.update_or_create(
                            groundwater_monitoring_well_static=well,
                            tube_number=int(dino_row["Buis-Nr"]),
                        )[0]

                        if (
                            int(dino_row["Buis-Nr"]) == 1
                        ):  # add the first tube, tube nr 1, to the dino gmn
                            MeasuringPoint.objects.update_or_create(
                                gmn=dino_gmn,
                                groundwater_monitoring_tube=tube,
                                code=tube.__str__(),
                            )[0]
                well_found += 1

            else:  # well was not found
                """
                1. create the well
                2. add all tubes to it from the DINO document
                """
                well_not_found += 1
                x = DINO_5["X-Coordinaat (RD)"].iloc[0]
                y = DINO_5["Y-Coordinaat (RD)"].iloc[0]
                longitude, latitude = x, y
                point = Point(longitude, latitude)

                well = GroundwaterMonitoringWellStatic.objects.update_or_create(
                    nitg_code=well_nitg,
                    coordinates=point,
                    in_management=False,
                )[0]
                well.internal_id = str(well)

                for i in range(len(DINO_5)):
                    dino_row = DINO_5.iloc[i]
                    tube_not_found += 1

                    tube = GroundwaterMonitoringTubeStatic.objects.update_or_create(
                        groundwater_monitoring_well_static=well,
                        tube_number=int(dino_row["Buis-Nr"]),
                    )[0]

                    if (
                        int(dino_row["Buis-Nr"]) == 1
                    ):  # add the first tube, tube nr 1, to the dino gmn
                        MeasuringPoint.objects.update_or_create(
                            gmn=dino_gmn,
                            groundwater_monitoring_tube=tube,
                            code=tube.__str__(),
                        )[0]

                    output_row = {
                        "put": dino_row["NITG-Nr"],
                        "peilbuis": dino_row["Buis-Nr"],
                        "put toegevoegd aan database": "ja",
                        "peilbuis toegevoegd aan database": "ja",
                    }
                    df_ouput = pd.concat(
                        [df_ouput, pd.DataFrame([output_row])], ignore_index=True
                    )

        print(
            f"{well_found} wells found and {well_not_found} wells not found out of {len(unique_wells_nitg)} total wells tried"
        )
        print(
            f"{tube_found} tubes found and {tube_not_found} tubes not found out of {len(DINO_3)} total tubes tried"
        )
        print()
        full_output_path = output_path + "\DINO_inspoelen.csv"
        df_ouput.to_csv(full_output_path, index=False)
        print(f"output file generated: {full_output_path}")
