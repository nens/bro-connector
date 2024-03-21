# This script monitors the measurements of each observation
# Measurements that are not checked yet, will be checked for quality
# Measurements are only checked within their own observation

# Checks included are
# - Min/max value specific for the observation filter/location
# - Max changes in values between values
# - 'Flatline' check

# After an observation is checked the following will happen
# - Indivual mesaurements will get type_status_quality_control 'goedgekeurd', 'afgekeurd' , they enter the database with type 'nogNietBeoordeeld'
# - The observation will get metadata status 'voorlopigBeoordeeld
# - The observation status will change to 'observation_qc_completed'

# After this the observation is picked up by the create_sourcedocs module

# If values are corrected these will be flagged in the observation
# A new delivery will have to be made to deliver the corrected values
# If values are flagged for deletion, this will also have to flagged in the observation

# Censor values outside measuring range, include parameters for this in 'aanlevering' schema?

from django.core.management.base import BaseCommand
import datetime
import logging
import pandas as pd

logger = logging.getLogger(__name__)

from main.settings import base as settings
from gld import models
from main.management.commands.gld_additions_create import (
    get_measurement_point_metadata_for_measurement,
)

# from create_addition_sourcedocs import get_measurement_point_metadata_for_measurement, get_timeseries_tvp_for_measurement_time_series_id

field_value_division_dict = {"cm": 100, "mm": 1000, "m": 1}

status_quality_control_values = {
    1: "afgekeurd",
    2: "goedgekeurd",
    3: "nogNietBeoordeeld",
    4: "onbeslist",
    9: "onbekend",
}


def get_previous_valid_observation(observation):
    # Get the previous valid observation for this
    pass


def min_max_check(single_measurement_value, min_value, max_value):
    # Check of de waarde niet hoger is dan de bovenkant of lager dan de onderkant van de buis

    if single_measurement_value >= max_value:
        # Een waarde boven bovenkant buis wordt afgekeurd
        check = 1
    elif single_measurement_value <= min_value:
        # Een waarde onder onderkant buis wordt afgekeurd
        check = 1
    else:
        # waarde voldoet aan min_max_check
        check = 2

    return check


def jump_check(
    measurement_value_difference, measurement_time_difference, jump_slope_limit
):
    # Controleer of de helling tussen twee opeenvolgende metingen niet te groot is

    measurement_slope = measurement_value_difference / measurement_time_difference
    if measurement_slope >= jump_slope_limit:
        check = 1
    else:
        check = 2

    # print(measurement_slope, check)
    return check


def long_term_measurement_change_check(past_ten_values):
    # Controleer of de afgelopen tien waardes hetzelfde zijn

    flatline_check = past_ten_values.count(past_ten_values[0]) == len(past_ten_values)
    if flatline_check == True:
        # Als de afgelopen tien waardes hetzelfde zijn, wordt de laatste waarde afgekeurd
        check = 1
    else:
        check = 2

    return check


def QC_check_main(observation, qc_settings):
    # Obtain timeseriesset belonging to the current observation
    timeseries_set = models.MeasurementTvp.objects.filter(
        observation_id=observation.observation_id
    )
    field_value_division_dict = {"cm": 100, "mm": 1000, "m": 1}

    # Create measurement list with all values of the timeseriesset
    measurements_list = []
    for tvp in timeseries_set:
        measurement_point_metadata_id = tvp.measurement_point_metadata_id
        metadata = get_measurement_point_metadata_for_measurement(
            measurement_point_metadata_id
        )
        waterstand_waarde = float(tvp.calculated_value)
        waterstand_waarde_converted = (
            waterstand_waarde / field_value_division_dict[tvp.field_value_unit]
        )  # cm or mm to m
        measurement_data = {
            "metadata_id": tvp.measurement_point_metadata_id,
            "time": tvp.measurement_time.isoformat(),
            "value": waterstand_waarde_converted,
            "metadata": metadata,
        }

        measurements_list += [measurement_data]

    # Perform calculations on the observation measurements
    measurements_df = pd.DataFrame(measurements_list)
    # min_value_observation = min(measurements_df.value)
    # max_value_observation = max(measurements_df.value)

    # Get monitoring tube information related to the current observation
    gwl_dossier_id = observation.groundwater_level_dossier_id
    try:
        gwl_dossier = models.GroundwaterLevelDossier.objects.get(
            groundwater_level_dossier_id=gwl_dossier_id
        )
        gw_monitoring_tube_id = gwl_dossier.groundwater_monitoring_tube_id
        # print(gw_monitoring_tube_id)
        gw_monitoring_tube = models.GroundwaterMonitoringTubes.objects.get(
            groundwater_monitoring_tube_id=gw_monitoring_tube_id
        )
        tube_top_position = gw_monitoring_tube.tube_top_position
        screen_length = gw_monitoring_tube.screen_length
        plain_tube_part_length = gw_monitoring_tube.plain_tube_part_length
        # print(tube_top_position, screen_length, plain_tube_part_length)

        # Calculate bottom of monitoring tube based on the information above
        tube_bottom_position = tube_top_position - (
            screen_length + plain_tube_part_length
        )
    except:
        print(
            "Observation id:",
            observation.observation_id,
            "is niet gekoppeld aan een bestaand dossier of buis,",
            "controleer of dossier ",
            gwl_dossier_id,
            "bestaat en of de bijbehorende buis bestaat.",
            "De min/max-check gaat voor deze observatie uit van een minimale waarde van -10m en een maximale waarde van 10m.",
        )
        tube_bottom_position = -10
        tube_top_position = 10

    # Run the invididual checks for the measurememnts
    ## checks = {}
    min_value = tube_bottom_position
    max_value = tube_top_position
    afgekeurd_counter = 0
    goedgekeurd_counter = 0
    for rij in range(len(measurements_df)):  # 1 rij = 1 tvp
        single_measurement_value = measurements_df.loc[rij, "value"]
        single_measurement_time = measurements_df.loc[rij, "time"]
        single_measurement_time = datetime.datetime.strptime(
            single_measurement_time, "%Y-%m-%dT%H:%M:%S+00:00"
        )
        try:
            previous_measurement_value = measurements_df.loc[rij - 1, "value"]
            previous_measurement_time = measurements_df.loc[rij - 1, "time"]
            previous_measurement_time = datetime.datetime.strptime(
                previous_measurement_time, "%Y-%m-%dT%H:%M:%S+00:00"
            )
            value_difference = abs(
                single_measurement_value - previous_measurement_value
            )
            time_difference = single_measurement_time - previous_measurement_time
            time_difference = time_difference.total_seconds()
        except:
            # als er geen eerdere waarde is in de meetreeks, zet dan het verschil op 0
            value_difference = 0
            time_difference = 1

        # Long term measurement change check
        if rij >= 9:
            past_ten_values = []
            for value_counter in range(10):
                # waardes worden afgerond op mm nauwkeurigheid
                # verander round(value,3) naar round(value,2) voor cm nauwkeurigheid
                past_ten_values.append(
                    round(measurements_df.loc[rij - value_counter, "value"], 3)
                )
            flatline_return = long_term_measurement_change_check(past_ten_values)
        else:
            # Voor de eerste 9 waarden kunnen we geen flatline check doen
            flatline_return = 2

        # Min max check
        min_max_return = min_max_check(single_measurement_value, min_value, max_value)

        # Jump check
        jump_return = jump_check(
            value_difference, time_difference, qc_settings["jump_slope_limit"]
        )

        if (min_max_return == 1) | (jump_return == 1) | (flatline_return == 1):
            # Als aan een van de checks niet wordt voldaan, dan voldoet het tijdmeetwaardepaar niet
            StatusQualityControl = 1
            afgekeurd_counter = afgekeurd_counter + 1
        else:
            StatusQualityControl = 2
            goedgekeurd_counter = goedgekeurd_counter + 1

        # Set qc-check outcome to metadata point
        # print('measurement id:',measurements_df.loc[rij,'id'])
        tvp_metadata = models.MeasurementPointMetadata.objects.get(
            measurement_point_metadata_id=measurements_df.loc[rij, "metadata_id"]
        )
        tvp_metadata.qualifier_by_quantity = StatusQualityControl
        record, created = models.MeasurementPointMetadata.objects.update_or_create(
            measurement_point_metadata_id=measurements_df.loc[rij, "metadata_id"],
            defaults={
                "qualifier_by_category_id": StatusQualityControl,
            },
        )

    # If one of the checks fails set the measurement metadata type_status_quality_control to 1 (afgekeurd)
    # Otherwise 2 (goedgekeurd)

    return afgekeurd_counter, goedgekeurd_counter


class Command(BaseCommand):
    def handle(self, *args, **options):
        qc_settings = settings.QUICK_SCAN_SETTINGS
        observation_set = models.Observation.objects.all()
        # Is the observation

        for observation in observation_set:
            # Perform qc-check only if the observation is not checked yet
            if observation.status != None:
                continue

            # Perform qc-check only if the observation contains a timeseries
            observation_tvps = models.MeasurementTvp.objects.filter(
                observation_id=observation.observation_id
            )
            if not observation_tvps:  # if there are no tvps in the observation
                continue

            # Get the observation metadata
            observation_id = observation.observation_id
            observation_metadata_id = observation.observation_metadata_id
            observation_metadata = models.ObservationMetadata.objects.get(
                observation_metadata_id=observation_metadata_id
            )
            observation_type = models.TypeObservationType.objects.get(
                id=observation_metadata.parameter_measurement_serie_type_id
            ).value

            # Perform qc-check only on observations that are reguliere meting
            if observation_type != "reguliereMeting":
                continue

            # observation_metadata = models.ObservationMetadata.objects.get(id=observation_metadata_id)
            # observation_type = models.TypeObservationType.objects.get(id=observation_metadata.parameter_measurement_serie_type)

            # if observation.status is None and observation_type == 'reguliereMeting':
            #     _ = QC_check_main(observation, qc_settings)
            afgekeurd_counter, goedgekeurd_counter = QC_check_main(
                observation, qc_settings
            )

            # after qc-check has happened, change observation status
            record, created = models.Observation.objects.update_or_create(
                observation_id=observation_id,
                defaults={"status": "observation_qc_completed"},
            )

            # after qc-check has happened, change observation metadata status
            record, created = models.ObservationMetadata.objects.update_or_create(
                observation_metadata_id=observation_metadata_id,
                defaults={"status_id": "2"},  # status is voorlopigBeoordeeld (2)
            )
            # print('Voor observatie id', observation_id,'aantal afgekeurde meetparen =', afgekeurd_counter, 'en aantal goedgekeurd =', goedgekeurd_counter)
            # break

        # delvertpos = models.DeliveredVerticalPositions()
        # hoogte = delvertpos.ground_level_position
        # hoogte_id = delvertpos.registration_object_id
