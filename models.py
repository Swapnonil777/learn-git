"""
ORM models. Note: DiagnosisReport intentionally stores NO farmer identity —
only what's needed for the district heatmap and model improvement later.
If you add user accounts, keep them in a separate table and never join
identity into this table by default (aggregate reporting should stay
anonymous-by-design, not anonymous-by-policy).
"""
from datetime import datetime
from sqlalchemy import Column, DateTime, Float, Integer, String
from database import Base


class DiagnosisReport(Base):
    __tablename__ = "diagnosis_reports"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Location (rounded in the API layer before storage — see geo_service.py)
    latitude = Column(Float)
    longitude = Column(Float)
    district = Column(String, index=True)
    state = Column(String, index=True)

    # Inputs
    crop_type = Column(String, index=True)
    growth_stage = Column(String)

    # Environmental snapshot at time of report (cached, not re-fetched later)
    temperature_c = Column(Float, nullable=True)
    humidity_pct = Column(Float, nullable=True)
    rainfall_mm_7d = Column(Float, nullable=True)
    soil_ph = Column(Float, nullable=True)
    soil_organic_carbon = Column(Float, nullable=True)

    # Model outputs
    disease_name = Column(String, index=True)
    confidence = Column(Float)
    severity = Column(String)  # low / moderate / high
    severity_score = Column(Float)  # 0-100
    spread_risk = Column(String)  # low / medium / high
    spread_risk_score = Column(Float)  # 0-100
