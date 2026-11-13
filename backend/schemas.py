from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

class RegionBase(BaseModel):
    city: str
    active_cases: int = Field(default=0, validation_alias="activeCases")
    patients: int = Field(default=0)
    disease: Optional[str] = None
    population_density: Optional[float] = Field(
        default=None, validation_alias="populationDensity"
    )
    hospital_capacity: Optional[float] = Field(default=None, validation_alias="hospitalCapacity")
    vaccination_rate: Optional[float] = Field(default=None, validation_alias="vaccinationRate")

    model_config = ConfigDict(populate_by_name=True)

class RegionCreate(RegionBase):
    pass

class RegionOut(BaseModel):
    id: int
    city: str
    risk: str
    activeCases: int = Field(validation_alias="active_cases")
    activeTrend: str = Field(validation_alias="active_trend", default="+0%")
    patients: int
    patientsTrend: str = Field(validation_alias="patients_trend", default="+0%")
    history: List[int]
    disease: Optional[str] = None
    populationDensity: Optional[float] = Field(validation_alias="population_density", default=0.0)
    hospitalCapacity: Optional[float] = Field(validation_alias="hospital_capacity", default=0.0)
    vaccinationRate: Optional[float] = Field(validation_alias="vaccination_rate", default=0.0)
    recommendations: List[str]
    lastWeekCases: Optional[int] = Field(validation_alias="last_week_cases", default=0)

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_validator("history", "recommendations", mode="before")
    @classmethod
    def parse_json_strings(cls, v):
        if isinstance(v, str):
            try:
                import json
                return json.loads(v)
            except:
                return []
        if v is None:
            return []
        return v

class DashboardStats(BaseModel):
    totalCases: int
    totalPatients: int
    activeRegions: int
    highRisk: int

class ChartPoint(BaseModel):
    day: str
    value: int

class CityChart(BaseModel):
    city: str
    data: List[ChartPoint]

class DashboardResponse(BaseModel):
    regions: List[RegionOut]
    totals: DashboardStats
    topChart: List[CityChart]
