from typing import List, Optional

from pydantic import BaseModel


class WeatherSnapshot(BaseModel):
    temperature_c: Optional[float]
    humidity_pct: Optional[float]
    rainfall_mm_7d: Optional[float]
    forecast_humidity_trend: Optional[str]  # "rising" / "falling" / "stable"


class SoilSnapshot(BaseModel):
    ph: Optional[float]
    organic_carbon_g_kg: Optional[float]
    nitrogen_g_kg: Optional[float]


class DiagnosisResponse(BaseModel):
    report_id: int
    crop_type: str
    growth_stage: str
    district: Optional[str]
    state: Optional[str]

    disease_name: str
    confidence: float
    severity: str
    severity_score: float

    spread_risk: str
    spread_risk_score: float
    spread_risk_reasons: List[str]

    recommendations: List[str]

    weather: WeatherSnapshot
    soil: SoilSnapshot

    disclaimer: str = (
        "Prototype system. Disease detection uses a lightweight heuristic, "
        "not a trained CNN — validate with an agronomist before acting on "
        "high-stakes recommendations."
    )


class HeatmapCell(BaseModel):
    district: str
    state: Optional[str]
    report_count: int
    dominant_disease: str
    avg_severity_score: float
    avg_spread_risk_score: float
    risk_level: str
    center_lat: float
    center_lon: float
