from pydantic import BaseModel, Field, field_validator


class ElectrodeModel(BaseModel):
    electrodePackingMaterial: str
    electrodePosition: float
    electrodeNumber: int
    electrodeStatus: str

    @field_validator("electrodePosition")
    def parse_position(cls, v):
        if isinstance(v, str):
            return float(v.replace(",", "."))
        return v


class GeoOhmCableModel(BaseModel):
    cableNumber: int
    electrodes: dict[int, ElectrodeModel] = Field(default_factory=dict)


class ScreenModel(BaseModel):
    screenLength: float | None
    sockMaterial: str | None


class SedimentSumpModel(BaseModel):
    sedimentSumpLength: float | None


class TubeStaticModel(BaseModel):
    tubeNumber: int
    tubeType: str
    artesianWellCapPresent: str
    sedimentSumpPresent: str
    numberOfGeoOhmCables: int
    tubeMaterial: str
    screen: ScreenModel
    sedimentSump: SedimentSumpModel | None = None
    geoOhmCables: dict[int, GeoOhmCableModel] = Field(default_factory=dict)


class WellStaticModel(BaseModel):
    deliveryAccountableParty: str
    deliveryResponsibleParty: str
    qualityRegime: str
    deliveryContext: str
    constructionStandard: str
    initialFunction: str
    nitgCode: str
    olgaCoda: str
    wellCode: str
    monitoringPdokId: str
    coordinates: str
    referenceSystem: str
    horizontalPositioningMethod: str
    localVerticalReferencePoint: str
    offset: str | None
    verticalDatum: str
    broId: str | None = None


class WellDynamicModel(BaseModel):
    groundLevelStable: str
    owner: str
    wellHeadProtector: str
    deliverGldToBro: str
    groundLevelPosition: str
    groundLevelPositioningMethod: str
    wellStability: str | None = None
    maintenanceResponsibleParty: str | None = None


class TubeDynamicConstructionModel(BaseModel):
    tubeTopDiameter: float | None
    variableDiameter: str | None
    tubeStatus: str
    tubeTopPosition: float | None
    tubeTopPositioningMethod: str | None
    tubePackingMaterial: str | None
    glue: str | None
    plainTubePartLength: float | None
    insertedPartDiameter: float | None
    insertedPartLength: float | None
    insertedPartMaterial: str | None


class TubeDynamicPositionsModel(BaseModel):
    tubeTopPosition: float | None
    tubeTopPositioningMethod: str | None


class TubeDynamicLengthChangeModel(BaseModel):
    tubeTopPosition: float | None
    tubeTopPositioningMethod: str | None
    plainTubePartLength: float | None


class TubeDynamicStatusModel(BaseModel):
    tubeStatus: str
