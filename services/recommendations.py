"""
Rule-based intervention recommendations. Deliberately conservative and
generic (cultural/biological practices first, chemical control framed as
"consult local guidance") since a prototype should not be prescribing
specific pesticide products/dosages without regulatory and regional
review. Extension path: pull region-specific, regulator-approved
treatment guidance from an agricultural extension database.
"""

GENERIC_LOW_SEVERITY = [
    "Monitor the field every 2-3 days for spread to neighboring plants.",
    "Remove and destroy visibly infected leaves to reduce inoculum.",
    "Avoid overhead irrigation in the evening — wet foliage overnight favors most fungal pathogens.",
]

GENERIC_MODERATE_SEVERITY = GENERIC_LOW_SEVERITY + [
    "Improve field drainage and plant spacing to reduce humidity around the canopy.",
    "Consult your local agricultural extension office about approved fungicide/bactericide options for this disease.",
]

GENERIC_HIGH_SEVERITY = GENERIC_MODERATE_SEVERITY + [
    "Consider a preventive fungicide/bactericide application per local extension guidance — act within 48-72 hours.",
    "Flag this field to neighboring farmers — high spread risk means nearby fields should start monitoring now.",
]

HIGH_SPREAD_RISK_ADDENDUM = [
    "Report this outbreak to your local agricultural office so it appears on the regional disease heatmap.",
    "Avoid moving plant material, tools, or equipment to other fields without cleaning them first.",
]


def get_recommendations(severity: str, spread_risk: str) -> list:
    if severity == "none":
        return ["No signs of disease — continue routine monitoring."]

    if severity == "low":
        recs = list(GENERIC_LOW_SEVERITY)
    elif severity == "moderate":
        recs = list(GENERIC_MODERATE_SEVERITY)
    else:
        recs = list(GENERIC_HIGH_SEVERITY)

    if spread_risk == "high":
        recs += HIGH_SPREAD_RISK_ADDENDUM

    return recs
