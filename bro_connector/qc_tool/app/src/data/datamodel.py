from datetime import datetime
from typing import List

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Well(Base):
    __tablename__ = "groundwater_monitoring_well_static"

    groundwater_monitoring_well_static_id: Mapped[int] = mapped_column(primary_key=True)
    bro_id: Mapped[str]
    nitg_code: Mapped[str]
    tubes: Mapped[List["TubeStatic"]] = relationship(
        back_populates="groundwater_monitoring_well", cascade="all, delete-orphan"
    )
    coordinates: Mapped[str]
    reference_system: Mapped[str]

    # groundwater_monitoring_tube_static_id: Mapped[int]


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
    groundwater_monitoring_well: Mapped["Well"] = relationship(back_populates="tubes")
    dynamic: Mapped[List["TubeDynamic"]] = relationship(
        back_populates="groundwater_monitoring_tube_static",
        cascade="all, delete-orphan",
    )
    groundwater_level_dossiers: Mapped[List["GroundwaterLevelDossier"]] = relationship(
        back_populates="groundwater_monitoring_tube_static",
        cascade="all, delete-orphan",
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
    groundwater_monitoring_tube_static: Mapped["TubeStatic"] = relationship(
        back_populates="dynamic"
    )


class GroundwaterLevelDossier(Base):
    __tablename__ = "groundwater_level_dossier"
    groundwater_level_dossier_id: Mapped[int] = mapped_column(primary_key=True)
    gmw_bro_id: Mapped[str]
    # tube_number: Mapped[int]
    groundwater_monitoring_tube_id: Mapped[int] = mapped_column(
        ForeignKey(
            "groundwater_monitoring_tube_static.groundwater_monitoring_tube_static_id"
        )
    )
    groundwater_monitoring_tube_static: Mapped["TubeStatic"] = relationship(
        back_populates="groundwater_level_dossiers"
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
