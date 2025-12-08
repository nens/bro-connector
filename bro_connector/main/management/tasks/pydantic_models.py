from typing import Optional, Dict, List
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
    electrodes: Dict[int, ElectrodeModel] = Field(default_factory=dict)


class ScreenModel(BaseModel):
    screenLength: Optional[float]
    sockMaterial: Optional[str]


class SedimentSumpModel(BaseModel):
    sedimentSumpLength: Optional[float]


class TubeStaticModel(BaseModel):
    tubeNumber: int
    tubeType: str
    artesianWellCapPresent: str
    sedimentSumpPresent: str
    numberOfGeoOhmCables: int
    tubeMaterial: str
    screen: ScreenModel
    sedimentSump: Optional[SedimentSumpModel] = None
    geoOhmCables: Dict[int, GeoOhmCableModel] = Field(default_factory=dict)


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
    offset: Optional[str]
    verticalDatum: str
    broId: Optional[str] = None


class WellDynamicModel(BaseModel):
    groundLevelStable: str
    owner: str
    wellHeadProtector: str
    deliverGldToBro: str
    groundLevelPosition: str
    groundLevelPositioningMethod: str
    wellStability: Optional[str] = None
    maintenanceResponsibleParty: Optional[str] = None


class TubeDynamicConstructionModel(BaseModel):
    tubeTopDiameter: Optional[float]
    variableDiameter: Optional[str]
    tubeStatus: str
    tubeTopPosition: Optional[float]
    tubeTopPositioningMethod: Optional[str]
    tubePackingMaterial: Optional[str]
    glue: Optional[str]
    plainTubePartLength: Optional[float]
    insertedPartDiameter: Optional[float]
    insertedPartLength: Optional[float]
    insertedPartMaterial: Optional[str]


class TubeDynamicPositionsModel(BaseModel):
    tubeTopPosition: Optional[float]
    tubeTopPositioningMethod: Optional[str]


class TubeDynamicLengthChangeModel(BaseModel):
    tubeTopPosition: Optional[float]
    tubeTopPositioningMethod: Optional[str]
    plainTubePartLength: Optional[float]


class TubeDynamicStatusModel(BaseModel):
    tubeStatus: str
