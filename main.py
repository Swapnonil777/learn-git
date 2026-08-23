from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import models
from database import engine
from routers import diagnose, heatmap

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI Crop Disease Early Warning System (Prototype)",
    description=(
        "Multimodal diagnosis (leaf image + weather + soil + geolocation + "
        "crop/growth stage) with spread-risk prediction and district-level "
        "outbreak heatmaps."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this before any real deployment
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(diagnose.router, tags=["diagnosis"])
app.include_router(heatmap.router, tags=["heatmap"])


@app.get("/")
def health_check():
    return {"status": "ok", "service": "crop-disease-early-warning"}
