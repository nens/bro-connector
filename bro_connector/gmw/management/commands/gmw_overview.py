import datetime
import os

import pandas as pd
from django.core.management.base import BaseCommand
from gmn.models import MeasuringPoint
from gmw.models import GroundwaterMonitoringWellStatic


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            type=str,
            help="Path to save the CSV file with missing information about the wells.",
        )

    def handle(self, *args, **options):
        output_path = str(options["output"])

        # Validate the output path
        if not os.path.isdir(output_path):
            raise ValueError("Invalid output path supplied")

        wells = GroundwaterMonitoringWellStatic.objects.all()

        # Define the columns for the DataFrame
        columns = [
            "Interne Putcode",
            "BRO ID",
            "NITG-code",
            "Tube nummer",
            "RD_X",
            "RD_Y",
            "Bronhouder",
            "Meetnetten",
            "Subgroepen",
            "Moet naar de BRO",
            "BRO Compleet",
            "Lengte stijgbuis [m]",
            "Diameter buis [mm]",
            "Bovenkant buis [mNAP]",
            "Bovenkant filter [mNAP]",
            "Onderkant filter [mNAP]",
        ]
        df = pd.DataFrame(columns=columns)

        # Process each well
        for well in wells:
            well_data = self.get_well_data(well)
            df = pd.concat([df, pd.DataFrame(well_data)], ignore_index=True)

        # Save the DataFrame as a CSV file
        date_string = datetime.datetime.now().strftime("%Y%m%d")
        save_path = os.path.join(output_path, f"putten_overzicht_{date_string}.csv")
        df.to_csv(save_path, index=False)
        self.stdout.write(f"File saved at {save_path}")

    def get_well_data(self, well):
        # Extract well-specific details
        well_code = well.well_code
        bro_id = well.bro_id
        nitg_code = well.nitg_code
        coordinates = well.coordinates
        RD_X, RD_Y = str(coordinates[0]), str(coordinates[1])
        delivery_accountable_party = well.delivery_accountable_party
        deliver_gmw_to_bro = well.deliver_gmw_to_bro
        complete_bro = well.complete_bro

        # Process all tubes for the well
        tube_data_list = []
        for tube in well.tube.all():
            tube_data = self.get_tube_data(tube)
            tube_data.update(
                {
                    "Interne Putcode": well_code,
                    "BRO ID": bro_id,
                    "NITG-code": nitg_code,
                    "RD_X": RD_X,
                    "RD_Y": RD_Y,
                    "Bronhouder": delivery_accountable_party,
                    "Moet naar de BRO": deliver_gmw_to_bro,
                    "BRO Compleet": complete_bro,
                }
            )
            tube_data_list.append(tube_data)

        return tube_data_list

    def get_tube_data(self, tube):
        # Extract tube-specific details
        tube_number = tube.tube_number
        tube_state = tube.state.order_by("date_from").last()

        # Extract attributes from the tube state
        tube_data = {
            "Tube nummer": str(tube_number),
            "Lengte stijgbuis [m]": self.round_value(
                getattr(tube_state, "plain_tube_part_length", None)
            ),
            "Diameter buis [mm]": self.round_value(
                getattr(tube_state, "tube_top_diameter", None)
            ),
            "Bovenkant buis [mNAP]": self.round_value(
                getattr(tube_state, "tube_top_position", None)
            ),
            "Bovenkant filter [mNAP]": self.round_value(
                getattr(tube_state, "screen_top_position", None)
            ),
            "Onderkant filter [mNAP]": self.round_value(
                getattr(tube_state, "screen_bottom_position", None)
            ),
        }

        # Process related MeasuringPoints
        measuring_points = MeasuringPoint.objects.filter(
            groundwater_monitoring_tube=tube
        )
        tube_data.update(
            {
                "Meetnetten": self.collect_names(measuring_points, "gmn"),
                "Subgroepen": self.collect_names(measuring_points, "subgroup"),
            }
        )

        return tube_data

    def collect_names(self, objects, field_name):
        names = []
        for obj in objects:
            field = getattr(obj, field_name, None)

            if field:  # Only proceed if the field exists
                if hasattr(field, "all"):  # Handle ManyToMany relationships
                    for related in field.all():
                        name = getattr(related, "name", None)
                        if name and name not in names:
                            names.append(str(name))  # Ensure it's a string
                else:  # For non-ManyToMany fields
                    name = (
                        getattr(field, "name", field)
                        if hasattr(field, "name")
                        else field
                    )
                    if name and name not in names:
                        names.append(str(name))  # Ensure it's a string

        return " ".join(names)

    @staticmethod
    def round_value(value, precision=2):
        if value is None:
            return None
        return round(value, precision)
