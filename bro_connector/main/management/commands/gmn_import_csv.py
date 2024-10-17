from django.core.management.base import BaseCommand
from gmn.models import GroundwaterMonitoringNet, MeasuringPoint
from gmw.models import GroundwaterMonitoringTubeStatic
import polars as pl

def find_monitoring_tube(tube_str: str) -> GroundwaterMonitoringTubeStatic:
    split_string = tube_str.split(sep="-")
    well_code = split_string[0]
    tube_nr = split_string[1]

    print(f'well: {well_code}; tube_nr: {tube_nr}.')

    tube = GroundwaterMonitoringTubeStatic.objects.filter(
        groundwater_monitoring_well_static__nitg_code = well_code,
        tube_number = tube_nr
    ).order_by('groundwater_monitoring_tube_static_id').first()
    return tube

def update_or_create_meetnet(df: pl.DataFrame, kantonnier: str) -> None:
    gmn = GroundwaterMonitoringNet.objects.update_or_create(
        name = kantonnier,
        deliver_to_bro = False,
        description = "Gemaakt ter groepering van meetrondes.",
        quality_regime = "IMBRO/A",
        delivery_context = "waterwetPeilbeheer",
        monitoring_purpose = "strategischBeheerKwantiteitRegionaal",
        groundwater_aspect = "kwantiteit",
    )[0]

    for row in df.iter_rows(named=True):
        tube = find_monitoring_tube(row["unicode"])
        if tube:
            measuring_point = MeasuringPoint.objects.update_or_create(
                gmn = gmn,
                groundwater_monitoring_tube = tube,
                code = tube.__str__()
            )[0]
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
        if not csv_path or not csv_path.endswith('.csv'):
            raise ValueError('Invalid CSV-file supplied.')
        
        df = pl.read_csv(csv_path, ignore_errors=True)
        print(df.columns)

        kantonniers = df.select('kantonnier').unique().drop_nulls()
        for kantonnier in kantonniers.iter_rows():
            kantonnier_naam = kantonnier[0]

            df_kantonier = df.filter(pl.col('kantonnier').eq(kantonnier_naam))
            update_or_create_meetnet(df_kantonier, kantonnier_naam)