"""
Spread risk model: rule-based (transparent, explainable) rather than a black
box — appropriate for a prototype where farmers/authorities need to trust
and audit the reasoning. Extension path: replace with a trained model once
you have enough historical (weather, soil, disease-progression) data pairs
— e.g. a gradient-boosted model predicting days-to-regional-spread.

Growth stage matters because most crops have susceptibility windows —
e.g. wheat is most vulnerable to rust during tillering/heading, not at
grain-fill. This is a simplified illustrative mapping, not agronomic fact,
and should be reviewed by a domain expert before production use.
"""
from services.disease_model import DISEASE_KNOWLEDGE_BASE

GROWTH_STAGE_SUSCEPTIBILITY = {
    "seedling": 0.9,
    "vegetative": 0.7,
    "flowering": 1.0,
    "fruiting": 0.8,
    "maturity": 0.4,
}


def _disease_favorability(disease_name: str, crop_type: str, temp_c, humidity_pct) -> float:
    """0-1 score for how favorable current weather is for this disease."""
    candidates = DISEASE_KNOWLEDGE_BASE.get(crop_type.lower(), [])
    entry = next((c for c in candidates if c["name"] == disease_name), None)
    if entry is None or temp_c is None or humidity_pct is None:
        return 0.5  # unknown -> assume moderate favorability

    low, high = entry["temp_range"]
    temp_score = 1.0 if low <= temp_c <= high else max(0.0, 1 - abs(temp_c - (low + high) / 2) / 15)
    humidity_score = 1.0 if humidity_pct >= entry["humidity_min"] else humidity_pct / entry["humidity_min"]
    return round((temp_score * 0.5 + humidity_score * 0.5), 2)


def assess_spread_risk(
    disease_name: str,
    crop_type: str,
    growth_stage: str,
    severity_score: float,
    weather: dict,
) -> dict:
    reasons = []

    favorability = _disease_favorability(
        disease_name, crop_type, weather.get("temperature_c"), weather.get("humidity_pct")
    )
    if favorability > 0.7:
        reasons.append("Current temperature and humidity are favorable for this pathogen.")
    elif favorability < 0.3:
        reasons.append("Current weather is relatively unfavorable for this pathogen — spread should be slower.")

    stage_factor = GROWTH_STAGE_SUSCEPTIBILITY.get(growth_stage.lower(), 0.6)
    if stage_factor >= 0.8:
        reasons.append(f"Crop is in a highly susceptible growth stage ({growth_stage}).")

    trend = weather.get("forecast_humidity_trend")
    trend_factor = {"rising": 1.15, "stable": 1.0, "falling": 0.85}.get(trend, 1.0)
    if trend == "rising":
        reasons.append("Humidity is forecast to rise over the next 7 days, raising spread potential.")
    elif trend == "falling":
        reasons.append("Humidity is forecast to fall over the next 7 days, which should slow spread.")

    rainfall = weather.get("rainfall_mm_7d")
    rainfall_factor = 1.0
    if rainfall is not None and rainfall > 40:
        rainfall_factor = 1.15
        reasons.append("Significant rainfall expected in the next 7 days — increases fungal/bacterial spread risk.")

    severity_factor = 0.5 + (severity_score / 100) * 0.5

    raw_score = (
        favorability * 40
        + stage_factor * 20
        + severity_factor * 20
    ) * trend_factor * rainfall_factor
    score = round(min(raw_score, 100), 1)

    if disease_name.startswith("Healthy"):
        return {"spread_risk": "low", "spread_risk_score": 0.0, "reasons": ["No active disease detected."]}

    level = "low" if score < 35 else "medium" if score < 65 else "high"
    return {"spread_risk": level, "spread_risk_score": score, "reasons": reasons}
