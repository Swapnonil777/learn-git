from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db
from services import geo_service, recommendations, soil_service, spread_risk, weather_service
from services.disease_model import analyze_leaf_image

router = APIRouter()

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/jpg", "image/webp"}


@router.post("/diagnose", response_model=schemas.DiagnosisResponse)
async def diagnose(
    image: UploadFile = File(...),
    crop_type: str = Form(...),
    growth_stage: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    db: Session = Depends(get_db),
):
    if image.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(400, f"Unsupported image type: {image.content_type}")
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise HTTPException(400, "Invalid GPS coordinates.")

    image_bytes = await image.read()
    if len(image_bytes) == 0:
        raise HTTPException(400, "Empty image file.")

    # Run the pieces that don't depend on each other concurrently in a real
    # deployment (asyncio.gather); kept sequential here for readability.
    cv_result = analyze_leaf_image(image_bytes, crop_type)
    weather = await weather_service.get_weather_snapshot(latitude, longitude)
    soil = await soil_service.get_soil_snapshot(latitude, longitude)
    geo = await geo_service.reverse_geocode(latitude, longitude)

    risk = spread_risk.assess_spread_risk(
        disease_name=cv_result["disease_name"],
        crop_type=crop_type,
        growth_stage=growth_stage,
        severity_score=cv_result["severity_score"],
        weather=weather,
    )
    recs = recommendations.get_recommendations(cv_result["severity"], risk["spread_risk"])

    rounded_lat, rounded_lon = geo_service.round_coords(latitude, longitude)
    report = models.DiagnosisReport(
        latitude=rounded_lat,
        longitude=rounded_lon,
        district=geo["district"],
        state=geo["state"],
        crop_type=crop_type,
        growth_stage=growth_stage,
        temperature_c=weather.get("temperature_c"),
        humidity_pct=weather.get("humidity_pct"),
        rainfall_mm_7d=weather.get("rainfall_mm_7d"),
        soil_ph=soil.get("ph"),
        soil_organic_carbon=soil.get("organic_carbon_g_kg"),
        disease_name=cv_result["disease_name"],
        confidence=cv_result["confidence"],
        severity=cv_result["severity"],
        severity_score=cv_result["severity_score"],
        spread_risk=risk["spread_risk"],
        spread_risk_score=risk["spread_risk_score"],
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    return schemas.DiagnosisResponse(
        report_id=report.id,
        crop_type=crop_type,
        growth_stage=growth_stage,
        district=geo["district"],
        state=geo["state"],
        disease_name=cv_result["disease_name"],
        confidence=cv_result["confidence"],
        severity=cv_result["severity"],
        severity_score=cv_result["severity_score"],
        spread_risk=risk["spread_risk"],
        spread_risk_score=risk["spread_risk_score"],
        spread_risk_reasons=risk["reasons"],
        recommendations=recs,
        weather=schemas.WeatherSnapshot(**weather),
        soil=schemas.SoilSnapshot(**soil),
    )
