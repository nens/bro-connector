import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationInfo, field_validator, model_validator

from .type_helpers import (
    BroDomainOptions,
    CorrectionReasonOptions,
    DesignLoopTypeOptions,
    DisplacementDirectionOptions,
    FilterTypeOptions,
    GUFDeliveryContextOptions,
    IndicationYesNoOptions,
    InstallationFunctionOptions,
    LegalTypeOptions,
    LimitSymbolOptions,
    MethodOptions,
    PubliclyAvailableOptions,
    QualityRegimeOptions,
    RegistrationTypeOptions,
    RelativeTemperatureOptions,
    RequestTypeOptions,
    TemperatureOptions,
    UsageTypeOptions,
    WaterInOutOptions,
    WellFunctionOptions,
)


## Uploadtask models
def to_camel(string: str) -> str:
    parts = string.split("_")
    return parts[0] + "".join(word.capitalize() for word in parts[1:])


class CamelModel(BaseModel):
    class Config:
        validate_by_name = True
        extra = "ignore"

        # Ensure aliasing works for all fields with underscores
        @staticmethod
        def alias_generator(field_name: str) -> str:
            return to_camel(field_name)


## Uploadtask models
class UploadTaskMetadata(CamelModel):
    request_reference: str
    delivery_accountable_party: str | None = None
    bro_id: str | None = None
    quality_regime: QualityRegimeOptions
    correction_reason: CorrectionReasonOptions | None = None


class GARBulkUploadMetadata(CamelModel):
    request_reference: str
    quality_regime: QualityRegimeOptions
    delivery_accountable_party: str | None = None
    quality_control_method: str | None = None
    groundwater_monitoring_nets: list[str] = []
    sampling_operator: int | None = None


class GLDBulkUploadMetadata(CamelModel):
    request_reference: str
    quality_regime: QualityRegimeOptions
    delivery_accountable_party: str | None = None
    bro_id: str


class GMNBulkUploadMetadata(CamelModel):
    request_reference: str
    quality_regime: QualityRegimeOptions
    delivery_accountable_party: str | None = None
    bro_id: str


class GLDBulkUploadSourcedocumentData(CamelModel):
    validation_status: str | None = None
    investigator_kvk: str
    observation_type: str
    evaluation_procedure: str
    measurement_instrument_type: str
    process_reference: str
    air_pressure_compensation_type: str | None = None
    begin_position: str | None = None
    end_position: str | None = None
    result_time: str | None = None


# GMN sourcedocs_data
class MeasuringPoint(CamelModel):
    measuring_point_code: str
    bro_id: str
    tube_number: int


class GMNStartregistration(CamelModel):
    object_id_accountable_party: str
    name: str
    delivery_context: str
    monitoring_purpose: str
    groundwater_aspect: str
    start_date_monitoring: str
    measuring_points: list[MeasuringPoint]


class GMNMeasuringPoint(CamelModel):
    event_date: str
    measuring_point_code: str
    bro_id: str
    tube_number: int


class GMNMeasuringPointEndDate(CamelModel):
    event_date: str | None = None
    measuring_point_code: str


class GMNTubeReference(CamelModel):
    event_date: str
    measuring_point_code: str
    bro_id: str
    tube_number: int


class GMNClosure(CamelModel):
    end_date_monitoring: str


# GMW sourcedocs_data
class Electrode(CamelModel):
    electrode_number: int
    electrode_packing_material: str
    electrode_status: str
    electrode_position: float | None = None


class GeoOhmCable(CamelModel):
    cable_number: int
    electrodes: list[Electrode]


class MonitoringTube(CamelModel):
    tube_number: int
    tube_type: str
    artesian_well_cap_present: str
    sediment_sump_present: str
    number_of_geo_ohm_cables: int = 0
    tube_top_diameter: int | None = None
    variable_diameter: str | None = None
    tube_status: str
    tube_top_position: float
    tube_top_positioning_method: str
    tube_packing_material: str
    tube_material: str
    glue: str
    screen_length: float
    sock_material: str
    plain_tube_part_length: float
    sediment_sump_length: float | None = None
    geo_ohm_cables: list[GeoOhmCable] | None = None

    # Newly added in GMW1.1
    screen_protection: str | None = None


class GMWConstruction(CamelModel):
    object_id_accountable_party: str
    delivery_context: str
    construction_standard: str
    initial_function: str
    number_of_monitoring_tubes: int
    ground_level_stable: str
    nitg_code: str | None = None
    well_stability: str | None = None
    owner: str | None = None
    maintenance_responsible_party: str | None = None
    well_head_protector: str
    well_construction_date: str
    delivered_location: str  # X -7000 to 289000 and Y 289000 629000
    horizontal_positioning_method: str
    local_vertical_reference_point: str = "NAP"
    offset: float = 0.000
    vertical_datum: str = "NAP"
    ground_level_position: float | None = None
    ground_level_positioning_method: str
    monitoring_tubes: list["MonitoringTube"]
    date_to_be_corrected: str | None = None

    # Newly added in GMW1.1
    geometric_data_publicly_available: str | None = None
    is_abroad: str | None = None
    related_surveys: list[str] | None = None


# noqa: N815 - Using mixedCase to match API requirements
class GMWEvent(CamelModel):
    event_date: str


class ElectrodeStatusElectrode(CamelModel):
    cable_number: int
    electrode_number: int
    tube_number: int
    electrode_status: str


# noqa: N815 - Using mixedCase to match API requirements
class GMWElectrodeStatus(GMWEvent):
    electrodes: list[ElectrodeStatusElectrode]


class GMWGroundLevel(GMWEvent):
    well_stability: Literal["stabielNAP"] = "stabielNAP"
    ground_level_stable: Literal["nee"] = "nee"
    ground_level_position: float
    ground_level_positioning_method: str


class GMWGroundLevelMeasuring(GMWEvent):
    ground_level_position: float
    ground_level_positioning_method: str


class GMWInsertionTube(CamelModel):
    tube_number: int
    tube_top_position: float
    tube_top_positioning_method: str
    inserted_part_length: float
    inserted_part_diameter: int
    inserted_part_material: str


class GMWInsertion(GMWEvent):
    monitoring_tubes: list[GMWInsertionTube]


class MonitoringTubeLengthening(CamelModel):
    tube_number: int
    variable_diameter: str | None = None
    tube_top_diameter: int | None = None
    tube_top_position: float
    tube_top_positioning_method: str
    tube_material: str | None = None
    glue: str | None = None
    plain_tube_part_length: float


class GMWLengthening(GMWEvent):
    well_head_protector: str | None = None
    monitoring_tubes: list[MonitoringTubeLengthening]


class GMWMaintainer(GMWEvent):
    maintenance_responsible_party: str


class GMWOwner(GMWEvent):
    owner: str


class MonitoringTubePositions(CamelModel):
    tube_number: int
    tube_top_position: float
    tube_top_positioning_method: str

    @field_validator("tube_top_positioning_method")
    def validate_tube_top_positioning_method(cls, value):
        if value == "afgeleidSbl":
            raise ValueError(
                "tubeTopPositioningMethod mag niet de waarde 'afgeleidSbl' hebben"
            )
        return value


class GMWPositions(GMWEvent):
    well_stability: Literal["nee"] = "nee"
    ground_level_stable: Literal["instabiel"] = "instabiel"
    ground_level_position: float
    ground_level_positioning_method: str
    monitoring_tubes: list[MonitoringTubePositions]

    ## Add more validation, ground_level_positioning_method cannot be 'geen'
    @field_validator("ground_level_positioning_method")
    def validate_ground_level_positioning_method(cls, value):
        if value == "geen":
            raise ValueError(
                "groundLevelPositioningMethod mag niet de waarde 'geen' hebben"
            )
        return value

    ## And the tube numbers within monitoring_tubes should be unique
    @field_validator("monitoring_tubes")
    def validate_unique_tube_numbers(cls, value):
        tube_numbers = [tube.tube_number for tube in value]
        if len(tube_numbers) != len(set(tube_numbers)):
            raise ValueError("De buizen moeten unieke nummers hebben")
        return value


class GMWPositionsMeasuring(GMWEvent):
    monitoring_tubes: list[MonitoringTubePositions]
    ground_level_position: float | None = None
    ground_level_positioning_method: str | None = None


class GMWRemoval(GMWEvent):
    pass


class GMWSubsequentAdditionalSurvey(GMWEvent):
    related_surveys: list[str]


class GMWShift(GMWEvent):
    ground_level_position: float
    ground_level_positioning_method: str


class MonitoringTubeShortening(CamelModel):
    tube_number: int
    tube_top_position: float
    tube_top_positioning_method: str
    plain_tube_part_length: float


class GMWShortening(GMWEvent):
    well_head_protector: str | None = None
    monitoring_tubes: list[MonitoringTubeShortening]


class MonitoringTubeStatus(CamelModel):
    tube_number: int
    tube_status: str


class GMWTubeStatus(GMWEvent):
    monitoring_tubes: list[MonitoringTubeStatus]


class GMWWellHeadProtector(GMWEvent):
    well_head_protector: str


class RelatedSurvey(CamelModel):
    bro_id: str


class GMWAdditionalSurvey(GMWEvent):
    related_surveys: list[RelatedSurvey]


class FieldMeasurement(CamelModel):
    parameter: int
    unit: str
    field_measurement_value: float
    quality_control_status: str


class FieldResearch(CamelModel):
    sampling_date_time: str | datetime
    sampling_operator: str | None = None
    sampling_standard: str = "onbekend"
    pump_type: str = "onbekend"
    primary_colour: str | None = None
    secondary_colour: str | None = None
    colour_strength: str | None = None
    abnormality_in_cooling: str = "onbekend"
    abnormality_in_device: str = "onbekend"
    polluted_by_engine: str = "onbekend"
    filter_aerated: str = "onbekend"
    ground_water_level_dropped_too_much: str = "onbekend"
    abnormal_filter: str = "onbekend"
    sample_aerated: str = "onbekend"
    hose_reused: str = "onbekend"
    temperature_difficult_to_measure: str = "onbekend"
    field_measurements: list[FieldMeasurement] | None = None

    @field_validator("sampling_date_time", mode="before")
    def format_datetime(cls, value):
        if isinstance(value, datetime):
            return value.isoformat(sep="T", timespec="seconds")
        return value


class Analysis(CamelModel):
    parameter: str | int
    unit: str
    analysis_measurement_value: float | None = None
    limit_symbol: LimitSymbolOptions | None = None
    reporting_limit: str | float | None = None
    quality_control_status: str


class AnalysisProcess(CamelModel):
    date: str | date
    analytical_technique: str | None = None
    valuation_method: str | None = None
    analyses: list[Analysis]

    @field_validator("date", mode="before")
    def format_date(cls, value):
        if isinstance(value, date):
            return value.strftime("%Y-%m-%d")
        return value


class LaboratoryAnalysis(CamelModel):
    responsible_laboratory_kvk: str | None = None
    analysis_processes: list[AnalysisProcess] = []


class GAR(CamelModel):
    object_id_accountable_party: str
    quality_control_method: str = "onbekend"  # Beoordelingsprocedure
    groundwater_monitoring_nets: list[str] = []
    gmw_bro_id: str
    tube_number: str | int
    field_research: FieldResearch
    laboratory_analyses: list[LaboratoryAnalysis] = []


class GLDStartregistration(CamelModel):
    object_id_accountable_party: str | None = None
    groundwater_monitoring_nets: list[str] = []
    gmw_bro_id: str
    tube_number: str | int


class TimeValuePair(CamelModel):
    time: str
    value: float | None = None
    status_quality_control: str = "onbekend"
    censor_reason: str | None = None
    censoring_limitvalue: float | None = None

    @field_validator("time", mode="before")
    def format_datetime(cls, value):
        if isinstance(value, datetime):
            return value.isoformat(sep="T", timespec="seconds")
        return value

    @field_validator("value", "censoring_limitvalue", mode="before")
    def parse_comma_decimal(cls, value):
        """Convert strings like '1,32' or '-0,5' into floats."""
        if isinstance(value, str):
            value = value.strip()
            if value == "" or value.lower() == "null":
                return None
            # Replace comma with dot if needed
            value = value.replace(",", ".")
            try:
                return float(value)
            except ValueError:
                raise ValueError(f"Invalid numeric value: {value!r}")
        return value


class GLDAddition(CamelModel):
    date: str | None = None
    observation_id: str | None = None
    observation_process_id: str | None = None
    measurement_timeseries_id: str | None = None
    validation_status: str | None = None
    investigator_kvk: str
    observation_type: str
    evaluation_procedure: str | None
    measurement_instrument_type: str | None
    process_reference: str | None
    air_pressure_compensation_type: str | None = None
    begin_position: str
    end_position: str
    result_time: str | None = None
    time_value_pairs: list[TimeValuePair]

    # New
    repeat_procedure: bool = False  # Indicates if the observation_process_id alone should be used as a repeat.

    @model_validator(mode="before")
    def generate_missing_ids(cls, data):
        if isinstance(data, dict):
            if not data.get("observation_id"):
                data["observation_id"] = f"_{uuid.uuid4()}"

            if not data.get("observation_process_id"):
                data["observation_process_id"] = f"_{uuid.uuid4()}"

            if not data.get("measurement_timeseries_id"):
                data["measurement_timeseries_id"] = f"_{uuid.uuid4()}"

            # Handle validation status
            if data.get("observation_type") == "reguliereMeting" and not data.get(
                "validation_status"
            ):
                data["validation_status"] = "onbekend"
            elif data.get("observation_type") == "controlemeting":
                data["validation_status"] = None

        return data

    @model_validator(mode="after")
    def correct_air_pressure_compensation_type(cls, model):
        if model.measurement_instrument_type not in ["druksensor", "stereoDruksensor"]:
            model.air_pressure_compensation_type = None

        if model.air_pressure_compensation_type in ["", "None"]:
            model.air_pressure_compensation_type = None

        return model


class GLDClosure(CamelModel):
    event_date: str


class FRDStartRegistration(CamelModel):
    object_id_accountable_party: str | None = None
    groundwater_monitoring_nets: list[str] = []
    gmw_bro_id: str
    tube_number: int


class MeasurementConfiguration(CamelModel):
    measurement_configuration_id: str
    measurement_e1_cable_number: int
    measurement_e1_electrode_number: int
    measurement_e2_cable_number: int
    measurement_e2_electrode_number: int
    current_e1_cable_number: int
    current_e1_electrode_number: int
    current_e2_cable_number: int
    current_e2_electrode_number: int


class FRDGemMeasurementConfiguration(CamelModel):
    measurement_configurations: list[MeasurementConfiguration]


class FRDEmmInstrumentConfiguration(CamelModel):
    instrument_configuration_id: str
    relative_position_transmitter_coil: str | int
    relative_position_primary_receiver_coil: str | int
    secondary_receiver_coil_available: str
    relative_position_secondary_receiver_coil: str | int | None = None
    coil_frequency_known: str
    coil_frequency: int | None = None
    instrument_length: int


class FRDEmmMeasurement(CamelModel):
    measurement_date: date | str
    measurement_operator_kvk: str
    determination_procedure: str
    measurement_evaluation_procedure: str
    measurement_series_count: int
    measurement_series_values: str
    related_instrument_configuration_id: str
    calculation_operator_kvk: str
    calculation_evaluation_procedure: str
    calculation_count: int
    calculation_values: str


class GemMeasurement(CamelModel):
    value: float
    unit: str = "Ohm"
    configuration: str


class RelatedCalculatedApparentFormationResistance(CamelModel):
    calculation_operator_kvk: str
    evaluation_procedure: str
    element_count: int
    values: str


class FRDGemMeasurement(CamelModel):
    measurement_date: str | date
    measurement_operator_kvk: str
    determination_procedure: str
    evaluation_procedure: str
    measurements: list[GemMeasurement]
    related_calculated_apparent_formation_resistance: (
        RelatedCalculatedApparentFormationResistance | None
    ) = None


class UploadTask(BaseModel):
    bro_domain: BroDomainOptions
    project_number: str
    registration_type: RegistrationTypeOptions
    request_type: RequestTypeOptions
    sourcedocument_data: Any
    metadata: UploadTaskMetadata


### CPT
class RemovedLayer(CamelModel):
    sequence_number: int
    upper_boundary: float
    lower_boundary: float
    description: str


class AdditionalInvestigation(CamelModel):
    investigation_date: str
    conditions: str | None = None
    surface_description: str | None = None
    groundwater_level: float | None = None
    removed_layers: list[RemovedLayer] = []


class ZeroLoadMeasurement(CamelModel):
    cone_resistance_before: float
    cone_resistance_after: float
    electrical_conductivity_before: float | None = None
    electrical_conductivity_after: float | None = None
    inclination_ew_before: float | None = None
    inclination_ew_after: float | None = None
    inclination_ns_before: float | None = None
    inclination_ns_after: float | None = None
    inclination_resultant_before: float | None = None
    inclination_resultant_after: float | None = None
    local_friction_before: float
    local_friction_after: float
    pore_pressure_u1_before: float | None = None
    pore_pressure_u1_after: float | None = None
    pore_pressure_u2_before: float | None = None
    pore_pressure_u2_after: float | None = None
    pore_pressure_u3_before: float | None = None
    pore_pressure_u3_after: float | None = None


class ConePenetrometer(CamelModel):
    description: str = "onbekend"
    cone_penetrometer_type: str
    cone_surface_area: float
    cone_diameter: float
    cone_surface_quotient: float
    cone_to_friction_sleeve_distance: float
    friction_sleeve_surface_area: float
    friction_sleeve_surface_quotient: float
    zero_load_measurement: ZeroLoadMeasurement


class Trajectory(CamelModel):
    predrilled_depth: float
    final_depth: float


class Parameters(CamelModel):
    penetration_length: str
    depth: str
    elapsed_time: str | None = None
    cone_resistance: str
    corrected_cone_resistance: str | None = None
    net_cone_resistance: str | None = None
    magnetic_field_strength_x: str | None = None
    magnetic_field_strength_y: str | None = None
    magnetic_field_strength_z: str | None = None
    magnetic_field_strength_total: str | None = None
    electrical_conductivity: str | None = None
    inclination_ew: str | None = None
    inclination_ns: str | None = None
    inclination_x: str | None = None
    inclination_y: str | None = None
    inclination_resultant: str | None = None
    magnetic_inclination: str | None = None
    magnetic_declination: str | None = None
    local_friction: str
    pore_ratio: str | None = None
    temperature: str | None = None
    pore_pressure_u1: str | None = None
    pore_pressure_u2: str | None = None
    pore_pressure_u3: str | None = None
    friction_ratio: str | None = None


class Procedure(CamelModel):
    interruption_processing_performed: str
    expert_correction_performed: str
    signal_processing_performed: str


class ConePenetrationTestResult(CamelModel):
    """Represents the parsed CPT test result values"""

    values: str  # Comma-separated values as string
    element_count: int


class DissipationTestResult(CamelModel):
    """Represents the parsed dissipation test result values"""

    values: str  # Comma-separated values as string
    element_count: int


class DissipationTest(CamelModel):
    result_time: str | None = None
    procedure: str | None = None
    observed_property: str | None = None
    feature_of_interest: str | None = None
    phenomenon_time: str  # ISO-8601 datetime
    penetration_length: float
    dissipation_test_result: list[DissipationTestResult] = []


class ConePenetrometerSurvey(CamelModel):
    dissipation_test_performed: str
    final_processing_date: str
    cpt_method: str
    quality_class: str
    stop_criterion: str
    sensor_azimuth: float | None = None
    trajectory: Trajectory
    cone_penetrometer: ConePenetrometer
    cone_penetration_test_result: ConePenetrationTestResult
    dissipation_tests: list[DissipationTest] = []
    procedure: Procedure
    parameters: Parameters
    phenomenon_time: str  # ISO-8601 datetime


class CPT(CamelModel):
    object_id_accountable_party: str
    delivery_context: str
    survey_purpose: str
    research_report_date: str
    cpt_standard: str
    additional_investigation_performed: str
    research_operator: str | None = None
    delivered_location: str  # Location coordinates as string
    horizontal_positioning_date: str
    horizontal_positioning_method: str
    horizontal_positioning_operator: str | None = None
    local_vertical_reference_point: str
    offset: float
    water_depth: float | None = None
    vertical_datum: str
    vertical_positioning_date: str
    vertical_positioning_method: str
    vertical_positioning_operator: str | None = None
    additional_investigation: AdditionalInvestigation | None = None
    cone_penetrometer_survey: ConePenetrometerSurvey


### Add BHR and GUF models below


class BHRP(CamelModel):
    object_id_accountable_party: str


class BHRG(CamelModel):
    object_id_accountable_party: str


class BHRGT(CamelModel):
    object_id_accountable_party: str


class SFR(CamelModel):
    object_id_accountable_party: str


# Updated DesignLoop class
class DesignLoop(CamelModel):
    """Design loop information for installations"""

    gml_id: str = Field(default_factory=lambda: f"_{uuid.uuid4()}")
    design_loop_id: str
    design_loop_pos: str  # Position coordinates for LineString geometry

    loop_type: DesignLoopTypeOptions | None = None  # Added: soil loop type

    # Lifespan is formatted from these two fields - ISO-8601 date string
    # Lifespan is not allowed to be present for NewLicense
    start_date: str | None
    end_date: str | None

    geometry_type: Literal["Point", "LineString"] = "Point"  # Type of geometry

    @field_validator("gml_id", mode="before")
    def generate_gml_id(cls, v):
        if v is None or v == "":
            return f"_{uuid.uuid4()}"
        return v


# Updated DesignScreen class
class DesignScreen(CamelModel):
    """Design screen information for a well"""

    screen_type: FilterTypeOptions
    design_screen_top: float  # meters
    design_screen_bottom: float | None = (
        None  # meters (mandatory if screenType is verticaal)
    )


# Updated DesignWell class
class DesignWell(CamelModel):
    """Design well within an installation"""

    gml_id: str = Field(default_factory=lambda: f"_{uuid.uuid4()}")
    design_well_id: str
    well_functions: list[WellFunctionOptions] = Field(min_length=1)
    height: float  # meters

    well_pos: str  # Position coordinates
    geometry_publicly_available: PubliclyAvailableOptions

    maximum_well_depth: float | None = None  # meters
    maximum_well_depth_publicly_available: PubliclyAvailableOptions = None

    maximum_well_capacity: float | None = None  # m3/h
    relative_temperature: RelativeTemperatureOptions | None = None

    design_screen: DesignScreen | None = None
    design_screen_publicly_available: PubliclyAvailableOptions = None

    @field_validator("gml_id", mode="before")
    def generate_gml_id(cls, v):
        raise Exception(f"generating gmlid: {v}")
        if v is None or v == "":
            return f"_{uuid.uuid4()}"
        return v


class DesignSurfaceInfiltration(CamelModel):
    """Design surface infiltration information for installations"""

    gml_id: str = Field(default_factory=lambda: f"_{uuid.uuid4()}")
    design_surface_infiltration_id: str
    design_surface_infiltration_pos: str  # Position coordinates for Polygon geometry

    @field_validator("gml_id", mode="before")
    @classmethod
    def generate_gml_id(cls, v):
        if v is None or v == "":
            return f"_{uuid.uuid4()}"
        return v


class EnergyCharacteristics(CamelModel):
    """
    Energy characteristics for a ground-source heat pump installation.
    Maps to «Gegevensgroeptype» Energiekenmerken.
    """

    # energie koude per jaar
    energy_cold: float | None = Field(
        default=None,
        description="energie koude per jaar",
    )

    # energie warmte per jaar
    energy_warm: float | None = Field(
        default=None,
        description="energie warmte per jaar",
    )

    # maximale infiltratietemperatuur warm
    maximum_infiltration_temperature_warm: float | None = Field(
        default=None,
        description="maximale infiltratietemperatuur warm",
    )

    # jaargemiddelde infiltratietemperatuur koud [0..1]
    average_infiltration_temperature_cold: float | None = Field(
        default=None,
        description="jaargemiddelde infiltratietemperatuur koud",
    )

    # jaargemiddelde infiltratietemperatuur warm [0..1]
    average_infiltration_temperature_warm: float | None = Field(
        default=None,
        description="jaargemiddelde infiltratietemperatuur warm",
    )

    # bodemzijdig vermogen koud [0..1]
    power_cold: float | None = Field(
        default=None,
        description="bodemzijdig vermogen koud",
    )

    # bodemzijdig vermogen warm [0..1]
    power_warm: float | None = Field(
        default=None,
        description="bodemzijdig vermogen warm",
    )

    # bodemzijdig vermogen [0..1]
    power: float | None = Field(
        default=None,
        description="bodemzijdig vermogen",
    )

    # gemiddeld jaarvolume koud [0..1]
    average_cold_water: float | None = Field(
        default=None,
        description="gemiddeld jaarvolume koud",
    )

    # gemiddeld jaarvolume warm [0..1]
    average_warm_water: float | None = Field(
        default=None,
        description="gemiddeld jaarvolume warm",
    )

    # maximaal jaarvolume koud [0..1]
    maximum_year_quantity_cold: float | None = Field(
        default=None,
        description="maximaal jaarvolume koud",
    )

    # maximaal jaarvolume warm [0..1]
    maximum_year_quantity_warm: float | None = Field(
        default=None,
        description="maximaal jaarvolume warm",
    )


# Updated DesignInstallation class
class DesignInstallation(CamelModel):
    """Design installation containing wells"""

    gml_id: str = Field(default_factory=lambda: f"_{uuid.uuid4()}")
    design_installation_id: str
    installation_function: InstallationFunctionOptions = "onttrekking"
    design_installation_pos: str  # Position coordinates
    licensed_quantities: list["LicensedQuantity"] = []
    energy_characteristics: EnergyCharacteristics | None = None  # For energy systems
    design_loops: list[DesignLoop] = []
    design_surface_infiltrations: list[DesignSurfaceInfiltration] = []
    design_wells: list[DesignWell] = []

    @field_validator("gml_id", mode="before")
    @classmethod
    def generate_gml_id(cls, v):
        if v is None or v == "":
            return f"_{uuid.uuid4()}"
        return v

    # Add validator, if installation_function in 'openBodemenergiesysteem' or 'geslotenBodemenergiesysteem', then energy_characteristics must be provided
    @field_validator("energy_characteristics", mode="before")
    @classmethod
    def validate_energy_characteristics(cls, v, info: ValidationInfo):
        installation_function = info.data.get("installation_function")
        if (
            installation_function
            in ["openBodemenergiesysteem", "geslotenBodemenergiesysteem"]
            and v is None
        ):
            raise ValueError(
                "energy_characteristics must be provided when installation_function is 'openBodemenergiesysteem' or 'geslotenBodemenergiesysteem'"
            )
        return v


# Updated LicensedQuantity class
class LicensedQuantity(CamelModel):
    """Licensed quantity information"""

    licensed_in_out: DisplacementDirectionOptions

    maximum_per_hour: int | None = None
    maximum_per_day: int | None = None
    maximum_per_month: int | None = None
    maximum_per_quarter: int | None = None
    maximum_per_year: int | None = None


# Updated GUFStartRegistration class
class GUFStartRegistration(CamelModel):
    """Source document data for GUF_StartRegistration"""

    object_id_accountable_party: str
    delivery_context: GUFDeliveryContextOptions
    start_time: str = Field(
        ...,
        description="Can be YYYY-MM-DD (10 chars), YYYY-MM (7 chars), or YYYY (4 chars)",
    )
    licence_gml_id: str = Field(default_factory=lambda: f"_{uuid.uuid4()}")
    identification_licence: str
    legal_type: LegalTypeOptions
    primary_usage_type: UsageTypeOptions
    secondary_usage_types: list[UsageTypeOptions] = []
    human_consumption: IndicationYesNoOptions
    licensed_quantities: list[LicensedQuantity] = []
    design_installations: list[DesignInstallation] = []

    @field_validator("licence_gml_id", mode="before")
    @classmethod
    def generate_licence_gml_id(cls, v):
        if not v:
            return f"_{uuid.uuid4()}"
        return v


# Updated GUFNewLicence class
class GUFNewLicence(CamelModel):
    """Source document data for GUF_NewLicence"""

    licence_gml_id: str = Field(default_factory=lambda: f"_{uuid.uuid4()}")
    identification_licence: str
    legal_type: LegalTypeOptions
    primary_usage_type: UsageTypeOptions
    secondary_usage_types: list[UsageTypeOptions] = []
    human_consumption: IndicationYesNoOptions
    licensed_quantities: list[LicensedQuantity] = []
    start_time: str = Field(
        ...,
        description="Can be YYYY-MM-DD (10 chars), YYYY-MM (7 chars), or YYYY (4 chars)",
    )
    design_installations: list[DesignInstallation] = []

    @field_validator("licence_gml_id", mode="before")
    @classmethod
    def generate_licence_gml_id(cls, v):
        if v is None or v == "":
            return f"_{uuid.uuid4()}"
        return v


# Updated RealisedLoop class
class RealisedLoop(CamelModel):
    """Realised loop information for installations"""

    gml_id: str = Field(default_factory=lambda: f"_{uuid.uuid4()}")
    realised_loop_id: str
    end_depth_bottom: float  # meters
    realised_loop_pos: str | None = None  # Position coordinates for Point geometry
    segments: str | None = None  # For Curve geometry
    geometry_type: Literal["Point", "Curve"] = "Point"
    loop_type: DesignLoopTypeOptions | None = None  # Added: soil loop type

    @field_validator("gml_id", mode="before")
    @classmethod
    def generate_gml_id(cls, v):
        if v is None or v == "":
            return f"_{uuid.uuid4()}"
        return v


class RealisedScreenChanges(CamelModel):
    realised_screen_id: str
    top_screen_depth: float  # meters


# Updated GUFHeight class
class GUFHeight(CamelModel):
    """Source document data for GUF_Height"""

    realised_well_id: str
    height: float  # meters
    well_depth: float | None = None
    start_validity: str = Field(
        ...,
        description="Can be YYYY-MM-DD (10 chars), YYYY-MM (7 chars), or YYYY (4 chars)",
    )
    realised_screens: list[RealisedScreenChanges] = []


# Updated RealisedScreen class
class RealisedScreen(CamelModel):
    """Realised screen information for wells"""

    gml_id: str = Field(default_factory=lambda: f"_{uuid.uuid4()}")
    realised_screen_id: str
    screen_type: FilterTypeOptions
    top_screen_depth: float  # meters
    length: float  # meters
    realised_screen_pos: str | None = None  # For Point geometry
    segments: str | None = None  # For Curve geometry
    geometry_type: Literal["Point", "Curve"] = "Point"

    @field_validator("gml_id", mode="before")
    @classmethod
    def handle_empty_gml_id(cls, v):
        return v if v is not None and v != "" else f"_{uuid.uuid4()}"


# Updated RealisedWell class
class RealisedWell(CamelModel):
    """Realised well information"""

    gml_id: str = Field(default_factory=lambda: f"_{uuid.uuid4()}")
    realised_well_id: str
    well_functions: list[WellFunctionOptions] = Field(min_length=1, max_length=2)
    height: float  # meters
    well_depth: float  # meters
    wellPos: str
    publicly_available: PubliclyAvailableOptions = None
    relative_temperature: RelativeTemperatureOptions | None = None
    validity: str | None = None  # Not allowed in ExpandRealisedInstallation
    lifespan: str | None = None  # Not allowed in ExpandRealisedInstallation
    realised_screens: list[RealisedScreen] = []

    @field_validator("gml_id", mode="before")
    @classmethod
    def handle_empty_gml_id(cls, v):
        return v if v is not None and v != "" else f"_{uuid.uuid4()}"


class RealisedSurfaceInfiltration(CamelModel):
    """Realised surface infiltration information for installations"""

    gml_id: str = Field(default_factory=lambda: f"_{uuid.uuid4()}")
    realised_surface_infiltration_id: str
    realised_surface_infiltration_pos: str  # Position coordinates for Polygon geometry

    @field_validator("gml_id", mode="before")
    @classmethod
    def generate_gml_id(cls, v):
        if v is None or v == "":
            return f"_{uuid.uuid4()}"
        return v


# Updated GUFAddRealisedInstallation class
class GUFAddRealisedInstallation(CamelModel):
    """Source document data for GUF_AddRealisedInstallation"""

    realised_installation_id: str
    installation_function: InstallationFunctionOptions
    realised_loop_pos: str  # Position coordinates
    start_validity: str = Field(
        ...,
        description="Can be YYYY-MM-DD (10 chars), YYYY-MM (7 chars), or YYYY (4 chars)",
    )
    realised_loops: list[RealisedLoop] = []
    realised_surface_infiltrations: list[RealisedSurfaceInfiltration] = []
    realised_wells: list[RealisedWell] = []


# Updated GUFExpandedRealisedInstallation class
class GUFExpandedRealisedInstallation(CamelModel):
    """Source document data for GUF_ExpandRealisedInstallation"""

    realised_installation_id: str
    installation_function: InstallationFunctionOptions
    realised_loop_pos: str  # Position coordinates
    start_validity: str = Field(
        ...,
        description="Can be YYYY-MM-DD (10 chars), YYYY-MM (7 chars), or YYYY (4 chars)",
    )
    realised_loops: list[RealisedLoop] = []
    realised_surface_infiltrations: list[RealisedSurfaceInfiltration] = []
    realised_wells: list[RealisedWell] = []


# Updated RealisedInstallationFunction class
class RealisedInstallationFunction(CamelModel):
    realised_installation_id: str
    installation_function: InstallationFunctionOptions


# Updated GUFWellFunction class
class GUFWellFunction(CamelModel):
    """Source document data for GUF_WellFunction"""

    realised_well_id: str
    well_functions: list[WellFunctionOptions] = Field(min_length=1, max_length=2)
    relative_temperature: RelativeTemperatureOptions | None = None
    event_date: str = Field(
        ...,
        description="Can be YYYY-MM-DD (10 chars), YYYY-MM (7 chars), or YYYY (4 chars)",
    )
    realised_installation_function: RealisedInstallationFunction | None = None


class RealisedWellClosurePart(CamelModel):
    """Part of realised well for closure operations"""

    gml_id: str = Field(default_factory=lambda: f"_{uuid.uuid4()}")
    realised_well_id: str

    @field_validator("gml_id", mode="before")
    @classmethod
    def handle_empty_gml_id(cls, v):
        return v if v is not None and v != "" else f"_{uuid.uuid4()}"


# Updated GUFClosureRealisedPart class
class GUFClosureRealisedPart(CamelModel):
    """Source document data for GUF_ClosureRealisedPart"""

    realised_installation_id: str
    installation_function: InstallationFunctionOptions | None = None
    well_pos: str | None = None
    end_time: str = Field(
        ...,
        description="Can be YYYY-MM-DD (10 chars), YYYY-MM (7 chars), or YYYY (4 chars)",
    )
    realised_wells: list[RealisedWellClosurePart] = []


class GUFClosure(CamelModel):
    """Source document data for GUF_Closure"""

    end_time: str = Field(
        ...,
        description="Can be YYYY-MM-DD (10 chars), YYYY-MM (7 chars), or YYYY (4 chars)",
    )


class GPDStartRegistration(CamelModel):
    object_id_accountable_party: str
    publicly_available: PubliclyAvailableOptions = (
        None  # Only registered for drinkwater
    )


class VolumeSeries(CamelModel):
    water_in_out: WaterInOutOptions
    volume: float  # in m3
    temperature: TemperatureOptions = None
    begin_date: str = Field(
        ...,
        description="YYYY-MM-DD",
    )
    end_date: str = Field(
        ...,
        description="YYYY-MM-DD",
    )


class GPDAddReport(CamelModel):
    report_id: str
    method: MethodOptions = "onbekend"
    volume_series: list[VolumeSeries]
    groundwater_usage_facility_bro_id: str  # BRO-ID of GUF


class GPDEndRegistration(CamelModel):
    # Empty class as no data is needed
    pass
