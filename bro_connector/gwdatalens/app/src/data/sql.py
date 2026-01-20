"""SQLAlchemy statements for querying database Provincie Zeeland."""

# %%
import logging
from typing import Optional, Sequence, Union
from urllib.parse import quote

import pandas as pd
from sqlalchemy import and_, create_engine, func, select
from sqlalchemy.dialects import postgresql

from gwdatalens.app.config import config
from gwdatalens.app.src.data import datamodel

logger = logging.getLogger(__name__)


def _to_int(v):
    try:
        return int(v)
    except ValueError:
        return -1


def sql_get_gmws():
    """Return a statement that builds a metadata table for all observation wells.

    Notes
    -----
    - Rank wells per nitg_code; keep most recent construction_date (well_rank = 1).
    - Rank tube_dynamic per tube_static by date_created, keeping newest.
    - Return one tube_dynamic per well/tube combination with metadata fields.

    """
    # Rank wells per nitg_code, newest construction_date first
    active_well_base = select(
        datamodel.WellStatic.groundwater_monitoring_well_static_id.label(
            "well_static_id"
        ),
        datamodel.WellStatic.nitg_code,
        datamodel.WellStatic.bro_id,
        datamodel.WellStatic.well_code,
        datamodel.WellStatic.construction_date,
        func.row_number()
        .over(
            partition_by=datamodel.WellStatic.nitg_code,
            order_by=[
                datamodel.WellStatic.construction_date.desc().nullslast(),
                datamodel.WellStatic.bro_id.desc(),
            ],
        )
        .label("well_rank"),
    ).subquery("active_well_base")

    active_well_static = (
        select(
            active_well_base.c.well_static_id,
            active_well_base.c.well_rank,
            active_well_base.c.nitg_code,
            active_well_base.c.bro_id,
            active_well_base.c.construction_date,
        )
        .where(active_well_base.c.well_rank == 1)
        .subquery("active_well_static")
    )

    # Rank tube_dynamic rows per tube_static by most recent creation date
    tube_ranked = (
        select(
            datamodel.WellStatic.groundwater_monitoring_well_static_id.label(
                "well_static_id"
            ),
            datamodel.WellStatic.bro_id,
            datamodel.WellStatic.nitg_code,
            datamodel.WellStatic.well_code,
            datamodel.TubeStatic.tube_number,
            datamodel.TubeDynamic.groundwater_monitoring_tube_static_id.label(
                "tube_static_id"
            ),
            datamodel.TubeDynamic.groundwater_monitoring_tube_dynamic_id.label(
                "tube_dynamic_id"
            ),
            datamodel.WellDynamic.ground_level_position,
            datamodel.TubeDynamic.tube_top_position,
            datamodel.TubeDynamic.plain_tube_part_length,
            datamodel.TubeStatic.screen_length,
            datamodel.WellStatic.coordinates,
            datamodel.WellStatic.reference_system,
            datamodel.TubeDynamic.date_created,
            func.row_number()
            .over(
                partition_by=datamodel.TubeDynamic.groundwater_monitoring_tube_static_id,
                order_by=[datamodel.TubeDynamic.date_created.desc().nullslast()],
            )
            .label("tube_dynamic_rank"),
        )
        .select_from(active_well_static)
        .join(
            datamodel.WellStatic,
            datamodel.WellStatic.groundwater_monitoring_well_static_id
            == active_well_static.c.well_static_id,
        )
        .join(
            datamodel.WellDynamic,
            datamodel.WellDynamic.groundwater_monitoring_well_static_id
            == datamodel.WellStatic.groundwater_monitoring_well_static_id,
        )
        .join(
            datamodel.TubeStatic,
            datamodel.TubeStatic.groundwater_monitoring_well_static_id
            == datamodel.WellStatic.groundwater_monitoring_well_static_id,
        )
        .join(
            datamodel.TubeDynamic,
            datamodel.TubeDynamic.groundwater_monitoring_tube_static_id
            == datamodel.TubeStatic.groundwater_monitoring_tube_static_id,
        )
        .subquery("tube_ranked")
    )

    stmt = (
        select(
            tube_ranked.c.well_static_id,
            tube_ranked.c.tube_static_id,
            tube_ranked.c.tube_dynamic_id,
            tube_ranked.c.bro_id,
            tube_ranked.c.nitg_code,
            tube_ranked.c.well_code,
            tube_ranked.c.tube_number,
            tube_ranked.c.ground_level_position,
            tube_ranked.c.tube_top_position,
            tube_ranked.c.plain_tube_part_length,
            tube_ranked.c.screen_length,
            tube_ranked.c.coordinates,
            tube_ranked.c.reference_system,
            tube_ranked.c.date_created,
        )
        .where(tube_ranked.c.tube_dynamic_rank == 1)
        .order_by(tube_ranked.c.well_static_id, tube_ranked.c.tube_static_id)
    )

    return stmt


def sql_get_unique_locations():
    stmt = (
        select(
            datamodel.WellStatic.groundwater_monitoring_well_static_id.label(
                "well_static_id"
            ),
            datamodel.WellStatic.internal_id,
            datamodel.WellStatic.bro_id,
            datamodel.WellStatic.well_code,
            datamodel.WellStatic.nitg_code,
        )
        .distinct()
        .order_by(datamodel.WellStatic.groundwater_monitoring_well_static_id)
    )
    return stmt


def sql_get_observation_wells():
    stmt = select(
        datamodel.WellStatic.groundwater_monitoring_well_static_id.label(
            "well_static_id"
        ),
        datamodel.TubeStatic.groundwater_monitoring_tube_static_id.label(
            "tube_static_id"
        ),
        datamodel.WellStatic.internal_id,
        datamodel.WellStatic.bro_id,
        datamodel.WellStatic.well_code,
        datamodel.WellStatic.nitg_code,
        datamodel.TubeStatic.tube_number,
    ).join(datamodel.TubeStatic)
    return stmt


def sql_get_observation_wells_with_gld():
    stmt = (
        select(
            datamodel.WellStatic.groundwater_monitoring_well_static_id.label(
                "well_static_id"
            ),
            datamodel.TubeStatic.groundwater_monitoring_tube_static_id.label(
                "tube_static_id"
            ),
            datamodel.WellStatic.bro_id,
            datamodel.WellStatic.well_code,
            datamodel.WellStatic.nitg_code,
            datamodel.TubeStatic.tube_number,
            func.count(
                datamodel.GroundwaterLevelDossier.groundwater_level_dossier_id
            ).label("nglds"),
        )
        .join(datamodel.TubeStatic)
        .join(datamodel.WellStatic)
        .group_by(
            datamodel.WellStatic.groundwater_monitoring_well_static_id,
            datamodel.TubeStatic.groundwater_monitoring_tube_static_id,
            datamodel.WellStatic.bro_id,
            datamodel.WellStatic.well_code,
            datamodel.WellStatic.nitg_code,
            datamodel.TubeStatic.tube_number,
        )
        .select_from(datamodel.GroundwaterLevelDossier)
    )
    return stmt


def sql_get_tube_numbers_for_location(well_static_id: int):
    stmt = (
        select(datamodel.TubeStatic.tube_number)
        .join(
            datamodel.WellStatic,
            datamodel.TubeStatic.groundwater_monitoring_well_static_id
            == datamodel.WellStatic.groundwater_monitoring_well_static_id,
        )
        .where(
            datamodel.WellStatic.groundwater_monitoring_well_static_id
            == _to_int(well_static_id)
        )
        .order_by(datamodel.TubeStatic.tube_number)
    )
    return stmt


def sql_count_measurements():
    """Count measurements per well/tube for both observation types.

    Returns counts for both 'reguliereMeting' and 'controlemeting' observation types
    as separate columns on the same row for each well/tube combination.
    """
    from sqlalchemy import case

    measurements_per_observation = (
        select(
            datamodel.MeasurementTvp.observation_id,
            func.count(func.distinct(datamodel.MeasurementTvp.measurement_time)).label(
                "number_of_measurements"
            ),
        )
        .select_from(datamodel.MeasurementTvp)
        .group_by(datamodel.MeasurementTvp.observation_id)
        .cte("measurements_count_per_observation")
    )

    measurements_per_tube_static = (
        select(
            datamodel.WellStatic.groundwater_monitoring_well_static_id.label(
                "well_static_id"
            ),
            datamodel.TubeStatic.groundwater_monitoring_tube_static_id.label(
                "tube_static_id"
            ),
            datamodel.WellStatic.bro_id,
            datamodel.WellStatic.well_code,
            datamodel.WellStatic.nitg_code,
            datamodel.TubeStatic.tube_number,
            func.sum(
                case(
                    (
                        datamodel.ObservationMetadata.observation_type
                        == "reguliereMeting",
                        measurements_per_observation.c.number_of_measurements,
                    ),
                    else_=0,
                )
            ).label("metingen"),
            func.sum(
                case(
                    (
                        datamodel.ObservationMetadata.observation_type
                        == "controlemeting",
                        measurements_per_observation.c.number_of_measurements,
                    ),
                    else_=0,
                )
            ).label("controlemetingen"),
        )
        .select_from(measurements_per_observation)
        .join(
            datamodel.Observation,
            datamodel.Observation.observation_id
            == measurements_per_observation.c.observation_id,
        )
        .join(
            datamodel.ObservationMetadata,
            datamodel.ObservationMetadata.observation_metadata_id
            == datamodel.Observation.observation_metadata_id,
        )
        .join(
            datamodel.GroundwaterLevelDossier,
            datamodel.GroundwaterLevelDossier.groundwater_level_dossier_id
            == datamodel.Observation.groundwater_level_dossier_id,
        )
        .join(
            datamodel.TubeStatic,
            datamodel.TubeStatic.groundwater_monitoring_tube_static_id
            == datamodel.GroundwaterLevelDossier.groundwater_monitoring_tube_id,
        )
        .join(
            datamodel.WellStatic,
            datamodel.WellStatic.groundwater_monitoring_well_static_id
            == datamodel.TubeStatic.groundwater_monitoring_well_static_id,
        )
        .group_by(
            datamodel.WellStatic.groundwater_monitoring_well_static_id,
            datamodel.TubeStatic.groundwater_monitoring_tube_static_id,
            datamodel.WellStatic.bro_id,
            datamodel.WellStatic.well_code,
            datamodel.WellStatic.nitg_code,
            datamodel.TubeStatic.tube_number,
        )
        .cte("measurements_count_per_tube_static")
    )

    stmt = select(measurements_per_tube_static)

    return stmt


def sql_observations_for_well_and_tube(well_static_id: int, tube_number: int):
    """Return observations for a specific well_static_id and tube_number.

    Useful for exploring why there are multiple counts for certain tubes.
    Shows all tube_static records (even duplicates) linked to observations
    for the given well and tube_number.

    Parameters
    ----------
    well_static_id : int
        The groundwater_monitoring_well_static_id to filter by.
    tube_number : int
        The tube_number to filter by.

    Returns
    -------
    sqlalchemy.sql.Select
        A statement that returns observation_id, tube_static_id, and measurement count.
    """
    stmt = (
        select(
            datamodel.Observation.observation_id,
            datamodel.TubeStatic.groundwater_monitoring_tube_static_id.label(
                "tube_static_id"
            ),
            func.count(func.distinct(datamodel.MeasurementTvp.measurement_time)).label(
                "number_of_measurements"
            ),
        )
        .select_from(datamodel.MeasurementTvp)
        .join(
            datamodel.Observation,
            datamodel.Observation.observation_id
            == datamodel.MeasurementTvp.observation_id,
        )
        .join(
            datamodel.GroundwaterLevelDossier,
            datamodel.GroundwaterLevelDossier.groundwater_level_dossier_id
            == datamodel.Observation.groundwater_level_dossier_id,
        )
        .join(
            datamodel.TubeStatic,
            datamodel.TubeStatic.groundwater_monitoring_tube_static_id
            == datamodel.GroundwaterLevelDossier.groundwater_monitoring_tube_id,
        )
        .join(
            datamodel.WellStatic,
            datamodel.WellStatic.groundwater_monitoring_well_static_id
            == datamodel.TubeStatic.groundwater_monitoring_well_static_id,
        )
        .where(
            (
                datamodel.WellStatic.groundwater_monitoring_well_static_id
                == well_static_id
            )
            & (datamodel.TubeStatic.tube_number == tube_number)
        )
        .group_by(
            datamodel.Observation.observation_id,
            datamodel.TubeStatic.groundwater_monitoring_tube_static_id,
        )
        .order_by(
            datamodel.Observation.observation_id,
            datamodel.TubeStatic.groundwater_monitoring_tube_static_id,
        )
    )
    return stmt


def sql_measurements_for_observation(observation_id: int):
    """Return all measurements for a specific observation.

    Useful for inspecting the actual measurement data for a given observation.

    Parameters
    ----------
    observation_id : int
        The observation_id to retrieve measurements for.

    Returns
    -------
    sqlalchemy.sql.Select
        A statement that returns all measurement details for the observation.
    """
    stmt = (
        select(
            datamodel.MeasurementTvp.measurement_tvp_id,
            datamodel.MeasurementTvp.measurement_time,
            datamodel.MeasurementTvp.field_value,
            datamodel.MeasurementTvp.field_value_unit,
            datamodel.MeasurementTvp.calculated_value,
        )
        .select_from(datamodel.MeasurementTvp)
        .where(datamodel.MeasurementTvp.observation_id == observation_id)
        .order_by(datamodel.MeasurementTvp.measurement_time)
    )
    return stmt


def sql_get_timeseries(
    well_static_id: int,
    tube_static_id: int,
    observation_type: Optional[Union[str, Sequence[str]]],
):
    stmt = (
        select(
            datamodel.MeasurementTvp.measurement_time,
            datamodel.MeasurementTvp.field_value,
            datamodel.MeasurementTvp.calculated_value,
            datamodel.MeasurementPointMetadata.status_quality_control,
            datamodel.MeasurementPointMetadata.status_quality_control_reason_datalens,
            datamodel.MeasurementPointMetadata.censor_reason,
            datamodel.MeasurementPointMetadata.value_limit,
            datamodel.MeasurementTvp.field_value_unit,
            datamodel.MeasurementTvp.measurement_tvp_id,
            datamodel.MeasurementTvp.measurement_point_metadata_id,
            # datamodel.MeasurementTvp.value_to_be_corrected,
            datamodel.MeasurementTvp.initial_calculated_value,
            datamodel.MeasurementTvp.correction_reason,
            datamodel.MeasurementTvp.correction_time,
            datamodel.ObservationMetadata.observation_type,
        )
        .join(datamodel.MeasurementPointMetadata)
        .join(datamodel.Observation)
        .join(datamodel.ObservationMetadata)
        .join(datamodel.GroundwaterLevelDossier)
        .join(datamodel.TubeStatic)
        .join(datamodel.WellStatic)
        .filter(
            and_(
                datamodel.WellStatic.groundwater_monitoring_well_static_id
                == _to_int(well_static_id),
            ),
            datamodel.TubeStatic.groundwater_monitoring_tube_static_id
            == _to_int(tube_static_id),
        )
        .order_by(datamodel.MeasurementTvp.measurement_time)
    )

    # Apply observation_type filter only when provided; allow lists/tuples
    if observation_type is not None:
        if isinstance(observation_type, str):
            stmt = stmt.filter(
                datamodel.ObservationMetadata.observation_type == observation_type
            )
        else:
            stmt = stmt.filter(
                datamodel.ObservationMetadata.observation_type.in_(
                    list(observation_type)
                )
            )

    return stmt


# =============================================================================
# DIAGNOSTIC QUERIES TO EXPLORE DATABASE STRUCTURE
# =============================================================================


def sql_gld_per_tube_dynamic():
    """Show GroundwaterLevelDossier per TubeDynamic with context.

    Returns all TubeDynamic records with their linked TubeStatic, Well, and GLD info.
    """
    stmt = (
        select(
            datamodel.TubeDynamic.groundwater_monitoring_tube_dynamic_id.label(
                "tube_dynamic_id"
            ),
            datamodel.TubeDynamic.tube_top_position,
            datamodel.TubeDynamic.plain_tube_part_length,
            datamodel.TubeDynamic.date_created,
            datamodel.TubeStatic.groundwater_monitoring_tube_static_id.label(
                "tube_static_id"
            ),
            datamodel.TubeStatic.tube_number,
            datamodel.WellStatic.groundwater_monitoring_well_static_id.label(
                "well_static_id"
            ),
            datamodel.WellStatic.bro_id,
            datamodel.WellStatic.nitg_code,
            datamodel.GroundwaterLevelDossier.groundwater_level_dossier_id.label(
                "gld_id"
            ),
        )
        .select_from(datamodel.TubeDynamic)
        .join(
            datamodel.TubeStatic,
            datamodel.TubeStatic.groundwater_monitoring_tube_static_id
            == datamodel.TubeDynamic.groundwater_monitoring_tube_static_id,
        )
        .join(
            datamodel.WellStatic,
            datamodel.WellStatic.groundwater_monitoring_well_static_id
            == datamodel.TubeStatic.groundwater_monitoring_well_static_id,
        )
        .outerjoin(
            datamodel.GroundwaterLevelDossier,
            datamodel.GroundwaterLevelDossier.groundwater_monitoring_tube_id
            == datamodel.TubeStatic.groundwater_monitoring_tube_static_id,
        )
        .order_by(
            datamodel.WellStatic.groundwater_monitoring_well_static_id,
            datamodel.TubeStatic.tube_number,
            datamodel.TubeDynamic.date_created.desc(),
        )
    )
    return stmt


def sql_observations_per_gld():
    """Show all Observations per GroundwaterLevelDossier with full context."""
    stmt = (
        select(
            datamodel.GroundwaterLevelDossier.groundwater_level_dossier_id.label(
                "gld_id"
            ),
            datamodel.Observation.observation_id,
            datamodel.ObservationMetadata.observation_type,
            datamodel.TubeStatic.groundwater_monitoring_tube_static_id.label(
                "tube_static_id"
            ),
            datamodel.TubeStatic.tube_number,
            datamodel.TubeDynamic.groundwater_monitoring_tube_dynamic_id.label(
                "tube_dynamic_id"
            ),
            datamodel.TubeDynamic.tube_top_position,
            datamodel.TubeDynamic.date_created.label("tube_dynamic_date_created"),
            datamodel.WellStatic.groundwater_monitoring_well_static_id.label(
                "well_static_id"
            ),
            datamodel.WellStatic.bro_id,
            datamodel.WellStatic.nitg_code,
            datamodel.WellDynamic.ground_water_monitoring_well_dynamic_id.label(
                "well_dynamic_id"
            ),
            datamodel.WellDynamic.ground_level_position,
        )
        .select_from(datamodel.GroundwaterLevelDossier)
        .join(
            datamodel.Observation,
            datamodel.Observation.groundwater_level_dossier_id
            == datamodel.GroundwaterLevelDossier.groundwater_level_dossier_id,
        )
        .join(
            datamodel.ObservationMetadata,
            datamodel.ObservationMetadata.observation_metadata_id
            == datamodel.Observation.observation_metadata_id,
        )
        .join(
            datamodel.TubeStatic,
            datamodel.TubeStatic.groundwater_monitoring_tube_static_id
            == datamodel.GroundwaterLevelDossier.groundwater_monitoring_tube_id,
        )
        .join(
            datamodel.TubeDynamic,
            datamodel.TubeDynamic.groundwater_monitoring_tube_static_id
            == datamodel.TubeStatic.groundwater_monitoring_tube_static_id,
        )
        .join(
            datamodel.WellStatic,
            datamodel.WellStatic.groundwater_monitoring_well_static_id
            == datamodel.TubeStatic.groundwater_monitoring_well_static_id,
        )
        .outerjoin(
            datamodel.WellDynamic,
            datamodel.WellDynamic.groundwater_monitoring_well_static_id
            == datamodel.WellStatic.groundwater_monitoring_well_static_id,
        )
        .order_by(
            datamodel.GroundwaterLevelDossier.groundwater_level_dossier_id,
            datamodel.Observation.observation_id,
        )
    )
    return stmt


def sql_all_observations_overview():
    """Overview of all observations with GLD and Well info."""
    stmt = (
        select(
            datamodel.Observation.observation_id,
            datamodel.GroundwaterLevelDossier.groundwater_level_dossier_id.label(
                "gld_id"
            ),
            datamodel.WellStatic.groundwater_monitoring_well_static_id.label(
                "well_static_id"
            ),
            datamodel.WellStatic.bro_id,
            datamodel.WellStatic.nitg_code,
            datamodel.TubeStatic.tube_number,
            datamodel.ObservationMetadata.observation_type,
        )
        .select_from(datamodel.Observation)
        .join(
            datamodel.ObservationMetadata,
            datamodel.ObservationMetadata.observation_metadata_id
            == datamodel.Observation.observation_metadata_id,
        )
        .join(
            datamodel.GroundwaterLevelDossier,
            datamodel.GroundwaterLevelDossier.groundwater_level_dossier_id
            == datamodel.Observation.groundwater_level_dossier_id,
        )
        .join(
            datamodel.TubeStatic,
            datamodel.TubeStatic.groundwater_monitoring_tube_static_id
            == datamodel.GroundwaterLevelDossier.groundwater_monitoring_tube_id,
        )
        .join(
            datamodel.WellStatic,
            datamodel.WellStatic.groundwater_monitoring_well_static_id
            == datamodel.TubeStatic.groundwater_monitoring_well_static_id,
        )
        .order_by(datamodel.Observation.observation_id)
    )
    return stmt


def sql_tube_dynamics_per_tube_static():
    """Count and list TubeDynamics per TubeStatic."""
    stmt = (
        select(
            datamodel.TubeStatic.groundwater_monitoring_tube_static_id.label(
                "tube_static_id"
            ),
            datamodel.TubeStatic.tube_number,
            datamodel.WellStatic.groundwater_monitoring_well_static_id.label(
                "well_static_id"
            ),
            datamodel.WellStatic.bro_id,
            func.count(
                datamodel.TubeDynamic.groundwater_monitoring_tube_dynamic_id
            ).label("num_tube_dynamics"),
        )
        .select_from(datamodel.TubeStatic)
        .join(
            datamodel.WellStatic,
            datamodel.WellStatic.groundwater_monitoring_well_static_id
            == datamodel.TubeStatic.groundwater_monitoring_well_static_id,
        )
        .outerjoin(
            datamodel.TubeDynamic,
            datamodel.TubeDynamic.groundwater_monitoring_tube_static_id
            == datamodel.TubeStatic.groundwater_monitoring_tube_static_id,
        )
        .group_by(
            datamodel.TubeStatic.groundwater_monitoring_tube_static_id,
            datamodel.TubeStatic.tube_number,
            datamodel.WellStatic.groundwater_monitoring_well_static_id,
            datamodel.WellStatic.bro_id,
        )
        .order_by(
            datamodel.WellStatic.groundwater_monitoring_well_static_id,
            datamodel.TubeStatic.tube_number,
        )
    )
    return stmt


def sql_well_dynamics_per_well():
    """Count and list WellDynamics per Well."""
    stmt = (
        select(
            datamodel.WellStatic.groundwater_monitoring_well_static_id.label(
                "well_static_id"
            ),
            datamodel.WellStatic.bro_id,
            datamodel.WellStatic.nitg_code,
            func.count(
                datamodel.WellDynamic.ground_water_monitoring_well_dynamic_id
            ).label("num_well_dynamics"),
        )
        .select_from(datamodel.WellStatic)
        .outerjoin(
            datamodel.WellDynamic,
            datamodel.WellDynamic.groundwater_monitoring_well_static_id
            == datamodel.WellStatic.groundwater_monitoring_well_static_id,
        )
        .group_by(
            datamodel.WellStatic.groundwater_monitoring_well_static_id,
            datamodel.WellStatic.bro_id,
            datamodel.WellStatic.nitg_code,
        )
        .order_by(datamodel.WellStatic.groundwater_monitoring_well_static_id)
    )
    return stmt


def sql_tubes_per_well():
    """Show all TubeStatic records per Well with counts."""
    stmt = (
        select(
            datamodel.WellStatic.groundwater_monitoring_well_static_id.label(
                "well_static_id"
            ),
            datamodel.WellStatic.bro_id,
            datamodel.WellStatic.nitg_code,
            datamodel.TubeStatic.tube_number,
            datamodel.TubeStatic.groundwater_monitoring_tube_static_id.label(
                "tube_static_id"
            ),
            func.count(
                datamodel.TubeDynamic.groundwater_monitoring_tube_dynamic_id
            ).label("num_tube_dynamics"),
            func.count(
                func.distinct(
                    datamodel.GroundwaterLevelDossier.groundwater_level_dossier_id
                )
            ).label("num_glds"),
        )
        .select_from(datamodel.WellStatic)
        .join(
            datamodel.TubeStatic,
            datamodel.TubeStatic.groundwater_monitoring_well_static_id
            == datamodel.WellStatic.groundwater_monitoring_well_static_id,
        )
        .outerjoin(
            datamodel.TubeDynamic,
            datamodel.TubeDynamic.groundwater_monitoring_tube_static_id
            == datamodel.TubeStatic.groundwater_monitoring_tube_static_id,
        )
        .outerjoin(
            datamodel.GroundwaterLevelDossier,
            datamodel.GroundwaterLevelDossier.groundwater_monitoring_tube_id
            == datamodel.TubeStatic.groundwater_monitoring_tube_static_id,
        )
        .group_by(
            datamodel.WellStatic.groundwater_monitoring_well_static_id,
            datamodel.WellStatic.bro_id,
            datamodel.WellStatic.nitg_code,
            datamodel.TubeStatic.tube_number,
            datamodel.TubeStatic.groundwater_monitoring_tube_static_id,
        )
        .order_by(
            datamodel.WellStatic.groundwater_monitoring_well_static_id,
            datamodel.TubeStatic.tube_number,
        )
    )
    return stmt


def sql_duplicate_tube_numbers_per_well():
    """Identify wells with duplicate tube_numbers (potential issue)."""
    subq = (
        select(
            datamodel.WellStatic.groundwater_monitoring_well_static_id.label(
                "well_static_id"
            ),
            datamodel.TubeStatic.tube_number,
            func.count(
                datamodel.TubeStatic.groundwater_monitoring_tube_static_id
            ).label("count_tube_statics"),
        )
        .select_from(datamodel.WellStatic)
        .join(
            datamodel.TubeStatic,
            datamodel.TubeStatic.groundwater_monitoring_well_static_id
            == datamodel.WellStatic.groundwater_monitoring_well_static_id,
        )
        .group_by(
            datamodel.WellStatic.groundwater_monitoring_well_static_id,
            datamodel.TubeStatic.tube_number,
        )
        .subquery("tube_counts")
    )

    stmt = (
        select(
            subq.c.well_static_id,
            datamodel.WellStatic.bro_id,
            datamodel.WellStatic.nitg_code,
            subq.c.tube_number,
            subq.c.count_tube_statics,
        )
        .select_from(subq)
        .join(
            datamodel.WellStatic,
            datamodel.WellStatic.groundwater_monitoring_well_static_id
            == subq.c.well_static_id,
        )
        .where(subq.c.count_tube_statics > 1)
        .order_by(subq.c.well_static_id, subq.c.tube_number)
    )
    return stmt


def run_sql(stmt, print_sql: bool = False):
    dbconfig = config.get_database_config()
    user = dbconfig.get("user")
    password = dbconfig.get("password")
    host = dbconfig.get("host")
    port = dbconfig.get("port")
    database = dbconfig.get("database")

    # URL-encode the password
    encoded_password = quote(password, safe="")
    connection_string = (
        f"postgresql+psycopg2://{user}:{encoded_password}@{host}:{port}/{database}"
    )
    engine = create_engine(
        connection_string,
        connect_args={"options": "-csearch_path=gmw,gld,public,django_admin"},
    )
    if print_sql:
        compiled = stmt.compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": False}
        )
        logger.debug("\nCompiled SQL (PostgreSQL dialect):\n")
        logger.debug(compiled)

    with engine.connect() as conn:
        df = pd.read_sql(stmt, con=conn)
    return df


# %%
if __name__ == "__main__":
    # # Minimal test: print the compiled SQL and optionally run when DATABASE_URL is set
    # stmt = sql_get_gmws()
    # compiled = stmt.compile(
    #     dialect=postgresql.dialect(), compile_kwargs={"literal_binds": False}
    # )
    # print("\nCompiled SQL (PostgreSQL dialect):\n")
    # print(compiled)

    # with engine.connect() as conn:
    #     df = gpd.read_postgis(stmt, con=conn, geom_col="coordinates")
    #     print("\nSample result (head):\n", df.head())

    # Test count
    df = run_sql(sql_count_measurements(), print_sql=True)
    print("\nSample result (head):\n", df.head())

# %%
