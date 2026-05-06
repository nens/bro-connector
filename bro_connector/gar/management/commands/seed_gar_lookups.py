import csv
import os
import polars as pl 
from django.apps import apps
from django.core.management.base import BaseCommand
from gar.choices import KLEUR, KLEURSTERKTE
from gar.models import (
    TypeColourStrengths,
    TypeColours,
    TypeParameterlijsten,
    TypeWaardebepalingsmethodes,
    TypeWaardebepalingstechnieken,
)

PARAMS_DIR = os.path.join(apps.get_app_config("gar").path, "params")


def _read_csv(filename: str):
    path = os.path.join(PARAMS_DIR, filename)
    df = pl.read_csv(path, separator=";", has_header=True)

    # filter empty rows column 1 is empty 
    df = df.filter(pl.col(df.columns[0]).is_not_null())

    return df

class Command(BaseCommand):
    help = "Idempotently seed GAR lookup tables from CSV files and choices constants."

    def handle(self, *args, **options):
        self._seed_parameters()
        self._seed_waardebepalingsmethodes()
        self._seed_waardebepalingstechnieken()
        self._seed_colours()
        self._seed_colour_strengths()

    def _seed_parameters(self):
        rows = _read_csv("params.csv")
        print(rows)
        objects = [
            TypeParameterlijsten(
                parameter_id=int(row.get("ID", 1)),
                aquocode=row.get("aquocode") or None,
                cas_nummer=row.get("CASnummer") or None,
                omschrijving=row.get("omschrijving") or None,
                eenheid=row.get("eenheid") or None,
                hoedanigheid=row.get("hoedanigheid") or None,
            )
            for row in rows.iter_rows(named=True)
        ]
        TypeParameterlijsten.objects.bulk_create(objects, ignore_conflicts=True)
        self.stdout.write(f"  Parameters: {len(objects)} rows processed (skipped existing).")

    def _seed_waardebepalingsmethodes(self):
        rows = _read_csv("waardebepalingsprocedure.csv")
        created = updated = 0
        for row in rows.iter_rows(named=True):
            code = row.get("Waarde", "").strip()
            omschrijving = row.get("Omschrijving", "").strip()
            if not code:
                continue
            _, was_created = TypeWaardebepalingsmethodes.objects.update_or_create(
                code=code,
                defaults={"omschrijving": omschrijving},
            )
            if was_created:
                created += 1
            else:
                updated += 1
        self.stdout.write(f"  Waardebepalingsmethodes: {created} created, {updated} updated.")

    def _seed_waardebepalingstechnieken(self):
        rows = _read_csv("waardebepalingstechnieken.csv")
        created = updated = 0
        for row in rows.iter_rows(named=True):
            code = row.get("Waarde", "").strip()
            omschrijving = row.get("Omschrijving", "").strip()
            if not code:
                continue
            _, was_created = TypeWaardebepalingstechnieken.objects.update_or_create(
                code=code,
                defaults={"omschrijving": omschrijving},
            )
            if was_created:
                created += 1
            else:
                updated += 1
        self.stdout.write(f"  Waardebepalingstechnieken: {created} created, {updated} updated.")

    def _seed_colours(self):
        created = 0
        for value, description in KLEUR:
            _, was_created = TypeColours.objects.get_or_create(
                value=value,
                defaults={"description": description},
            )
            if was_created:
                created += 1
        self.stdout.write(f"  TypeColours: {created} created (skipped existing).")

    def _seed_colour_strengths(self):
        created = 0
        for waarde, omschrijving in KLEURSTERKTE:
            _, was_created = TypeColourStrengths.objects.get_or_create(
                waarde=waarde,
                defaults={"omschrijving": omschrijving},
            )
            if was_created:
                created += 1
        self.stdout.write(f"  TypeColourStrengths: {created} created (skipped existing).")
