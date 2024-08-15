from datetime import datetime

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Well(Base):
    __tablename__ = "groundwater_monitoring_well_static"
    groundwater_monitoring_well_static_id: Mapped[int] = mapped_column(primary_key=True)
    bro_id: Mapped[str]
    nitg_code: Mapped[str]
    coordinates: Mapped[str]
    reference_system: Mapped[str]


class TubeStatic(Base):
    __tablename__ = "groundwater_monitoring_tube_static"
    groundwater_monitoring_tube_static_id: Mapped[int] = mapped_column(primary_key=True)
    screen_length: Mapped[float]
    tube_number: Mapped[int]
    groundwater_monitoring_well_static_id: Mapped[int] = mapped_column(
        ForeignKey(
            "groundwater_monitoring_well_static.groundwater_monitoring_well_static_id"
        )
    )


class TubeDynamic(Base):
    __tablename__ = "groundwater_monitoring_tube_dynamic"
    groundwater_monitoring_tube_dynamic_id: Mapped[int] = mapped_column(
        primary_key=True
    )
    tube_top_position: Mapped[float]
    plain_tube_part_length: Mapped[float]
    groundwater_monitoring_tube_static_id: Mapped[int] = mapped_column(
        ForeignKey(
            "groundwater_monitoring_tube_static.groundwater_monitoring_tube_static_id"
        )
    )


class GroundwaterLevelDossier(Base):
    __tablename__ = "groundwater_level_dossier"
    groundwater_level_dossier_id: Mapped[int] = mapped_column(primary_key=True)
    groundwater_monitoring_tube_id: Mapped[int] = mapped_column(
        ForeignKey(
            "groundwater_monitoring_tube_static.groundwater_monitoring_tube_static_id"
        )
    )


class Observation(Base):
    __tablename__ = "observation"
    observation_id: Mapped[int] = mapped_column(primary_key=True)
    groundwater_level_dossier_id: Mapped[int] = mapped_column(
        ForeignKey("groundwater_level_dossier.groundwater_level_dossier_id")
    )
    observation_metadata_id: Mapped[int] = mapped_column(
        ForeignKey("observation_metadata.observation_metadata_id")
    )


class ObservationMetadata(Base):
    __tablename__ = "observation_metadata"
    observation_metadata_id: Mapped[int] = mapped_column(primary_key=True)
    observation_type: Mapped[str]


class MeasurementTvp(Base):
    __tablename__ = "measurement_tvp"
    measurement_tvp_id: Mapped[int] = mapped_column(primary_key=True)
    measurement_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    field_value: Mapped[float]
    field_value_unit: Mapped[str]
    calculated_value: Mapped[float]
    observation_id: Mapped[int] = mapped_column(
        ForeignKey("observation.observation_id")
    )
    measurement_point_metadata_id: Mapped[int] = mapped_column(
        ForeignKey("measurement_point_metadata.measurement_point_metadata_id")
    )


class MeasurementPointMetadata(Base):
    __tablename__ = "measurement_point_metadata"
    measurement_point_metadata_id: Mapped[int] = mapped_column(primary_key=True)
    status_quality_control: Mapped[str]
    censor_reason: Mapped[str]
    censor_reason_artesia: Mapped[str]
    value_limit: Mapped[float]
