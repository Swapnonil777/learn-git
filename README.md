# AI Crop Disease Early Warning System — Backend Prototype

A FastAPI backend implementing the multimodal pipeline described in the
brief: leaf image + crop type + growth stage + GPS → auto-fetched weather
and soil data → disease detection, spread-risk prediction, interventions,
and a district-level outbreak heatmap for authorities.

## What's real vs. what's a stand-in (read this first)

This is a **working prototype**, and it's honest about where it's simplified
so you know exactly what to harden before this touches real farmers:

| Component | What's implemented | What to swap in for production |
|---|---|---|
| Leaf disease detection | A transparent color/lesion-coverage heuristic (`services/disease_model.py`) — no trained neural net | A CNN fine-tuned on PlantVillage/PlantDoc (ResNet50/EfficientNet baseline gets ~85-95% on PlantVillage) |
| Weather | Live calls to [Open-Meteo](https://open-meteo.com) (free, no key) | Same, or a paid provider for higher resolution |
| Soil | Live calls to [ISRIC SoilGrids](https://rest.isric.org/soilgrids/v2.0/docs) (free, no key, ~250m global model) | National soil survey data or real sensors, if/when available |
| Geolocation → district | Live reverse geocoding via OpenStreetMap Nominatim (free, rate-limited) | Google Geocoding API or self-hosted Nominatim at scale |
| Spread risk | Rule-based scoring (temp/humidity favorability × growth-stage susceptibility × forecast trend) | A model trained on real historical outbreak progression data |
| Recommendations | Rule-based, deliberately generic/conservative (no specific pesticide dosing) | Region-specific extension-service guidance database |
| Storage | SQLite, anonymized reports (no farmer identity fields) | Postgres + PostGIS for real geospatial queries at scale |

Everything is structured so each stand-in is a **single-function swap** —
see the docstring at the top of each `services/*.py` file.

## Project structure

```
crop_disease_backend/
├── main.py                    # FastAPI app, CORS, router wiring
├── database.py                # SQLAlchemy engine/session (SQLite)
├── models.py                  # DiagnosisReport ORM model
├── schemas.py                 # Pydantic request/response models
├── requirements.txt
├── routers/
│   ├── diagnose.py            # POST /diagnose
│   └── heatmap.py             # GET /heatmap, GET /heatmap/summary
└── services/
    ├── disease_model.py       # CV heuristic + disease knowledge base
    ├── weather_service.py     # Open-Meteo integration
    ├── soil_service.py        # SoilGrids integration
    ├── geo_service.py         # Reverse geocoding + coord rounding
    ├── spread_risk.py         # Spread-risk scoring
    └── recommendations.py     # Intervention rules
```

## Running it

Requires Python 3.10+ and internet access (for the weather/soil/geo APIs).

```bash
cd crop_disease_backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Open http://localhost:8000/docs for interactive Swagger UI — the easiest
way to try it, since it handles the multipart image upload for you.

### Try it with curl

```bash
curl -X POST http://localhost:8000/diagnose \
  -F "image=@/path/to/leaf.jpg" \
  -F "crop_type=tomato" \
  -F "growth_stage=flowering" \
  -F "latitude=28.6139" \
  -F "longitude=77.2090"
```

Example response shape:

```json
{
  "report_id": 1,
  "crop_type": "tomato",
  "growth_stage": "flowering",
  "district": "New Delhi",
  "state": "Delhi",
  "disease_name": "Early Blight",
  "confidence": 0.6,
  "severity": "low",
  "severity_score": 12.1,
  "spread_risk": "high",
  "spread_risk_score": 94.2,
  "spread_risk_reasons": [
    "Current temperature and humidity are favorable for this pathogen.",
    "Crop is in a highly susceptible growth stage (flowering).",
    "Humidity is forecast to rise over the next 7 days, raising spread potential.",
    "Significant rainfall expected in the next 7 days — increases fungal/bacterial spread risk."
  ],
  "recommendations": ["...", "..."],
  "weather": { "temperature_c": 26.4, "humidity_pct": 88, "rainfall_mm_7d": 55.2, "forecast_humidity_trend": "rising" },
  "soil": { "ph": 7.2, "organic_carbon_g_kg": 14.3, "nitrogen_g_kg": 1.1 },
  "disclaimer": "Prototype system..."
}
```

### Check the heatmap

After a few `/diagnose` calls from different coordinates:

```bash
curl http://localhost:8000/heatmap
curl http://localhost:8000/heatmap/summary
curl "http://localhost:8000/heatmap?state=Delhi&crop_type=tomato"
```

Supported crops in the demo knowledge base: `tomato`, `potato`, `wheat`,
`rice`, `maize` (case-insensitive). Any other crop falls back to the
tomato disease set with a lower implied confidence — that's a prototype
shortcut, not a real fallback strategy.

## What I'd extend first

Roughly in priority order:

1. **Swap the CV heuristic for a real model.** This is the single biggest
   credibility gap. Fine-tune a ResNet/EfficientNet on PlantVillage (or a
   regionally-relevant dataset — PlantVillage is mostly US/EU cultivars)
   and drop it into `_classify_with_trained_model()`. Until this happens,
   don't present disease names/confidence as authoritative anywhere in a
   farmer-facing UI — frame it as "possible diagnosis, verify with extension
   officer."
2. **Async-parallelize the external calls.** `diagnose.py` currently calls
   weather → soil → geo sequentially; `asyncio.gather()` them since they're
   independent — cuts response time roughly 3x.
2b. **Add basic rate limiting / caching** on weather and soil lookups keyed
   by rounded coordinates — many farmers in the same district will trigger
   near-identical API calls within the same day.
3. **Move to Postgres + PostGIS** once you need real "reports within N km"
   or proper spatial clustering for the heatmap instead of exact-string
   district matching.
4. **Add auth for the heatmap endpoints** — right now anyone can query
   `/heatmap`. Authorities' dashboard should sit behind API keys or OAuth;
   the `/diagnose` endpoint can stay open for farmer-facing apps.
5. **Validate the spread-risk rules and knowledge base with an actual plant
   pathologist.** The temp/humidity ranges and growth-stage susceptibility
   multipliers here are illustrative placeholders to make the pipeline
   demonstrable, not sourced from agronomic literature.
6. **Feedback loop:** let extension officers mark a report's diagnosis as
   confirmed/incorrect. That labeled data is exactly what you'd need to
   train the real CV model in improvement #1.
