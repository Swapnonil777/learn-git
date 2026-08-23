from collections import Counter
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db

router = APIRouter()


@router.get("/heatmap", response_model=List[schemas.HeatmapCell])
def get_heatmap(
    state: Optional[str] = Query(None, description="Filter to a specific state/province"),
    crop_type: Optional[str] = Query(None, description="Filter to a specific crop"),
    db: Session = Depends(get_db),
):
    """District-level aggregation for agricultural authorities. Never
    returns individual farm coordinates or any farmer-identifying data —
    only district-level counts and rounded center coordinates."""
    query = db.query(models.DiagnosisReport).filter(
        models.DiagnosisReport.disease_name.notlike("Healthy%")
    )
    if state:
        query = query.filter(models.DiagnosisReport.state == state)
    if crop_type:
        query = query.filter(models.DiagnosisReport.crop_type == crop_type)

    reports = query.all()

    by_district = {}
    for r in reports:
        key = (r.district, r.state)
        by_district.setdefault(key, []).append(r)

    cells = []
    for (district, state_name), group in by_district.items():
        disease_counts = Counter(r.disease_name for r in group)
        dominant_disease = disease_counts.most_common(1)[0][0]
        avg_severity = sum(r.severity_score for r in group) / len(group)
        avg_spread = sum(r.spread_risk_score for r in group) / len(group)
        avg_lat = sum(r.latitude for r in group) / len(group)
        avg_lon = sum(r.longitude for r in group) / len(group)

        risk_level = "low" if avg_spread < 35 else "medium" if avg_spread < 65 else "high"

        cells.append(
            schemas.HeatmapCell(
                district=district,
                state=state_name,
                report_count=len(group),
                dominant_disease=dominant_disease,
                avg_severity_score=round(avg_severity, 1),
                avg_spread_risk_score=round(avg_spread, 1),
                risk_level=risk_level,
                center_lat=round(avg_lat, 3),
                center_lon=round(avg_lon, 3),
            )
        )

    # Hotspots first — highest spread risk, then report volume.
    cells.sort(key=lambda c: (c.avg_spread_risk_score, c.report_count), reverse=True)
    return cells


@router.get("/heatmap/summary")
def get_summary(db: Session = Depends(get_db)):
    """Quick top-line stats for a dashboard header."""
    total = db.query(func.count(models.DiagnosisReport.id)).scalar()
    diseased = (
        db.query(func.count(models.DiagnosisReport.id))
        .filter(models.DiagnosisReport.disease_name.notlike("Healthy%"))
        .scalar()
    )
    high_risk_districts = (
        db.query(models.DiagnosisReport.district)
        .filter(models.DiagnosisReport.spread_risk == "high")
        .distinct()
        .count()
    )
    return {
        "total_reports": total,
        "reports_with_disease": diseased,
        "districts_with_high_spread_risk": high_risk_districts,
    }
