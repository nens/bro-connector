from django.core.management.base import BaseCommand
from gmn.models import GroundwaterMonitoringNet, MeasuringPoint, Subgroup
from gmw.models import GroundwaterMonitoringTubeStatic
import polars as pl


def find_monitoring_tube(tube_str: str) -> GroundwaterMonitoringTubeStatic:
    split_string = tube_str.split(sep="-")
    well_code = split_string[0]
    tube_nr = split_string[1]

    print(f"well: {well_code}; tube_nr: {tube_nr}.")

    tube = (
        GroundwaterMonitoringTubeStatic.objects.filter(
            groundwater_monitoring_well_static__nitg_code=well_code, tube_number=tube_nr
        )
        .order_by("groundwater_monitoring_tube_static_id")
        .first()
    )
    return tube


def update_or_create_subgroup(df: pl.DataFrame, subgroup: Subgroup) -> None:
    for row in df.iter_rows(named=True):
        tube = find_monitoring_tube(row["unicode"])
        if tube:
            measuring_point = MeasuringPoint.objects.update_or_create(
                gmn=subgroup.gmn,
                groundwater_monitoring_tube=tube,
                defaults={
                    "code": tube.__str__(),
                }
            )[0]
            measuring_point.subgroup.add(subgroup)
            print(measuring_point)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--csv",
            type=str,
            help="Het path naar de CSV met informatie over de meetnetten.",
        )

    def handle(self, *args, **options):
        csv_path = str(options["csv"])
        if not csv_path or not csv_path.endswith(".csv"):
            raise ValueError("Invalid CSV-file supplied.")

        df = pl.read_csv(csv_path, separator=";", ignore_errors=True, truncate_ragged_lines=True, has_header=True)
        print(df.columns)

        gmn = GroundwaterMonitoringNet.objects.update_or_create(
            name="Meetrondes Kantonniers",
            deliver_to_bro=False,
            description="Hoofgroepering van de Meetrondes.",
            quality_regime="IMBRO/A",
            delivery_context="waterwetPeilbeheer",
            monitoring_purpose="strategischBeheerKwantiteitRegionaal",
            groundwater_aspect="kwantiteit",
        )[0]

        kantonniers = df.select("kantonnier").unique().drop_nulls()
        for kantonnier in kantonniers.iter_rows():
            kantonnier_naam = kantonnier[0]
            df_kantonier = df.filter(pl.col("kantonnier").eq(kantonnier_naam))

            subgroup = Subgroup.objects.update_or_create(
                gmn=gmn,
                name=kantonnier_naam,
            )[0]
            update_or_create_subgroup(df_kantonier, subgroup)
