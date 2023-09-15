from gld_aanlevering.models import (
    GroundwaterLevelDossier,
    MeasurementPointMetadata,
    MeasurementTvp,
    Observation,
    ObservationMetadata,
    ObservationProcess,
    ResponsibleParty,
    TypeAirPressureCompensation,
    TypeCensoredReasonCode,
    TypeEvaluationProcedure,
    TypeInterpolationCode,
    TypeMeasurementInstrumentType,
    TypeObservationType,
    TypeProcessReference,
    TypeProcessType,
    TypeStatusCode,
    TypeStatusQualityControl,
    DeliveredLocations,
    DeliveredVerticalPositions,
    GroundwaterMonitoringWells,
    GroundwaterMonitoringTubes,
    gld_registration_log,
    gld_addition_log,
)

GLD_MODELS = [
    GroundwaterLevelDossier,
    MeasurementPointMetadata,
    MeasurementTvp,
    Observation,
    ObservationMetadata,
    ObservationProcess,
    ResponsibleParty,
    TypeAirPressureCompensation,
    TypeCensoredReasonCode,
    TypeEvaluationProcedure,
    TypeInterpolationCode,
    TypeMeasurementInstrumentType,
    TypeObservationType,
    TypeProcessReference,
    TypeProcessType,
    TypeStatusCode,
    TypeStatusQualityControl,
]

GWM_MODELS = [
    DeliveredLocations,
    DeliveredVerticalPositions,
    GroundwaterMonitoringWells,
    GroundwaterMonitoringTubes,
]

AANLEVERING_MODELS = [gld_registration_log, gld_addition_log]


class PostgresRouter:
    def db_for_read(self, model, **hints):
        if model in GLD_MODELS:
            return "gld"
        elif model in GWM_MODELS:
            return "gmw"
        elif model in AANLEVERING_MODELS:
            return "aanlevering"
        else:
            return None

    def db_for_write(self, model, **hints):
        if model in GLD_MODELS:
            return "gld"
        elif model in GWM_MODELS:
            return "gmw"
        elif model in AANLEVERING_MODELS:
            return "aanlevering"
        else:
            return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        return True
