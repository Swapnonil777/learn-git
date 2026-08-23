"""
Leaf image analysis.

IMPORTANT — read this before demoing this as "AI disease detection":
This module does NOT contain a trained neural network. Training a real
crop-disease CNN needs a labeled dataset (e.g. PlantVillage, PlantDoc) and
a training pipeline this prototype doesn't include. What's here instead is
a deliberately simple, transparent color/texture heuristic — it looks at
what fraction of the leaf is discolored (yellow/brown/black lesions vs.
healthy green) and picks the most plausible disease for that crop from a
small knowledge base.

It is structured so a real model is a one-function swap: implement
`_classify_with_trained_model()` to load a fine-tuned ResNet/EfficientNet
(PlantVillage has ~87% top-1 accuracy on a ResNet50 baseline) and return
early from `analyze_leaf_image()` when a model file is present.
"""
import io
from typing import Optional

import numpy as np
from PIL import Image

# crop -> list of (disease name, favorable_temp_range_c, favorable_humidity_pct,
#                   lesion_color_signature)
# Signatures and thresholds are illustrative placeholders for the prototype,
# not calibrated against real plant pathology data.
DISEASE_KNOWLEDGE_BASE = {
    "tomato": [
        {"name": "Early Blight", "temp_range": (24, 29), "humidity_min": 80, "signature": "brown_rings"},
        {"name": "Late Blight", "temp_range": (10, 24), "humidity_min": 90, "signature": "dark_wet"},
        {"name": "Septoria Leaf Spot", "temp_range": (20, 27), "humidity_min": 85, "signature": "small_spots"},
    ],
    "potato": [
        {"name": "Late Blight", "temp_range": (10, 24), "humidity_min": 90, "signature": "dark_wet"},
        {"name": "Early Blight", "temp_range": (24, 29), "humidity_min": 80, "signature": "brown_rings"},
    ],
    "wheat": [
        {"name": "Leaf Rust", "temp_range": (15, 22), "humidity_min": 70, "signature": "orange_pustules"},
        {"name": "Powdery Mildew", "temp_range": (15, 22), "humidity_min": 60, "signature": "white_powder"},
    ],
    "rice": [
        {"name": "Rice Blast", "temp_range": (24, 28), "humidity_min": 85, "signature": "grey_lesions"},
        {"name": "Bacterial Leaf Blight", "temp_range": (25, 34), "humidity_min": 70, "signature": "yellow_wilt"},
    ],
    "maize": [
        {"name": "Northern Corn Leaf Blight", "temp_range": (18, 27), "humidity_min": 75, "signature": "grey_lesions"},
        {"name": "Common Rust", "temp_range": (16, 25), "humidity_min": 70, "signature": "orange_pustules"},
    ],
}

DEFAULT_DISEASES = DISEASE_KNOWLEDGE_BASE["tomato"]


def _load_trained_model():
    """Stub. Return a loaded model object if a weights file exists on disk,
    else None. Left unimplemented in the prototype — see module docstring."""
    return None


def _classify_with_trained_model(model, image: Image.Image, crop_type: str) -> Optional[dict]:
    """Would run real inference. Not implemented in the prototype."""
    return None


def _color_heuristic(image: Image.Image) -> dict:
    """Very rough lesion-coverage estimate from HSV color analysis.

    Returns fraction of leaf pixels that look discolored (yellow/brown/black)
    vs. healthy green, plus a coarse guess at lesion color for matching
    against the knowledge base signatures.
    """
    img = image.convert("RGB").resize((256, 256))
    arr = np.array(img).astype(np.float32) / 255.0

    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    maxc = np.max(arr, axis=2)
    minc = np.min(arr, axis=2)
    v = maxc
    s = np.where(maxc == 0, 0, (maxc - minc) / np.where(maxc == 0, 1, maxc))

    # crude hue calc, good enough to bucket green vs yellow/brown vs dark
    hue = np.zeros_like(maxc)
    delta = maxc - minc + 1e-6
    r_max = (maxc == r)
    g_max = (maxc == g) & ~r_max
    b_max = (maxc == b) & ~r_max & ~g_max
    hue[r_max] = (60 * ((g[r_max] - b[r_max]) / delta[r_max]) + 360) % 360
    hue[g_max] = (60 * ((b[g_max] - r[g_max]) / delta[g_max]) + 120) % 360
    hue[b_max] = (60 * ((r[b_max] - g[b_max]) / delta[b_max]) + 240) % 360

    leaf_mask = s > 0.15  # ignore near-white background / glare
    total_leaf_px = max(int(np.sum(leaf_mask)), 1)

    green_mask = leaf_mask & (hue >= 70) & (hue <= 170)
    yellow_brown_mask = leaf_mask & (hue >= 20) & (hue < 70)
    dark_mask = leaf_mask & (v < 0.25)

    lesion_px = int(np.sum(yellow_brown_mask) + np.sum(dark_mask))
    lesion_fraction = min(lesion_px / total_leaf_px, 1.0)

    if np.sum(dark_mask) > np.sum(yellow_brown_mask):
        color_signature = "dark_wet"
    else:
        color_signature = "brown_rings"
    if np.sum(green_mask) / total_leaf_px > 0.9:
        color_signature = "healthy"

    return {"lesion_fraction": lesion_fraction, "color_signature": color_signature}


def analyze_leaf_image(image_bytes: bytes, crop_type: str) -> dict:
    """Main entry point. Returns disease_name, confidence (0-1), severity,
    severity_score (0-100)."""
    model = _load_trained_model()
    image = Image.open(io.BytesIO(image_bytes))

    if model is not None:
        result = _classify_with_trained_model(model, image, crop_type)
        if result is not None:
            return result

    analysis = _color_heuristic(image)
    lesion_fraction = analysis["lesion_fraction"]
    candidates = DISEASE_KNOWLEDGE_BASE.get(crop_type.lower(), DEFAULT_DISEASES)

    if lesion_fraction < 0.05:
        return {
            "disease_name": "Healthy / No visible disease",
            "confidence": round(1.0 - lesion_fraction, 2),
            "severity": "none",
            "severity_score": round(lesion_fraction * 100, 1),
        }

    # Pick a plausible candidate — with a real signature match if we have one,
    # otherwise the crop's most common disease as a fallback guess.
    matched = next(
        (c for c in candidates if c["signature"] == analysis["color_signature"]),
        candidates[0],
    )

    confidence = round(min(0.55 + lesion_fraction * 0.4, 0.9), 2)
    severity_score = round(lesion_fraction * 100, 1)
    severity = "low" if severity_score < 15 else "moderate" if severity_score < 40 else "high"

    return {
        "disease_name": matched["name"],
        "confidence": confidence,
        "severity": severity,
        "severity_score": severity_score,
    }
