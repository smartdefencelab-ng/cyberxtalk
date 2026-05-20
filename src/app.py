from enum import Enum
from typing import List, Optional

from fastapi import FastAPI
from langdetect import detect, LangDetectException
from pydantic import BaseModel, Field


class IncidentCategory(str, Enum):
    phishing = "Phishing"
    malware = "Malware"
    account_compromise = "Account Compromise"
    ransomware = "Ransomware / Extortion"
    online_banking_fraud = "Online Banking Fraud"
    social_media_impersonation = "Social Media Impersonation"
    unknown = "Unknown / Needs Analyst Review"


class IncidentReport(BaseModel):
    reporter_name: Optional[str] = None
    incident_description: str = Field(..., min_length=3)
    affected_asset: Optional[str] = None
    date_observed: Optional[str] = None


class IncidentResponse(BaseModel):
    language_detected: str
    category: IncidentCategory
    priority: str
    indicators: List[str]
    recommended_actions: List[str]


app = FastAPI(
    title="CyberXTalk API",
    description="Multilingual cyber incident intake, classification, and triage prototype.",
    version="0.1.0",
)


def detect_language(text: str) -> str:
    try:
        return detect(text)
    except LangDetectException:
        return "unknown"


def classify_incident(text: str) -> IncidentCategory:
    lowered = text.lower()

    if any(token in lowered for token in ["phish", "link", "login page", "otp", "credential"]):
        return IncidentCategory.phishing
    if any(token in lowered for token in ["malware", "virus", "trojan", "infected"]):
        return IncidentCategory.malware
    if any(token in lowered for token in ["hacked", "account", "password", "locked out"]):
        return IncidentCategory.account_compromise
    if any(token in lowered for token in ["ransom", "encrypted", "pay bitcoin", "extortion"]):
        return IncidentCategory.ransomware
    if any(token in lowered for token in ["debit", "bank", "transfer", "unauthorized transaction", "alert"]):
        return IncidentCategory.online_banking_fraud
    if any(token in lowered for token in ["impersonate", "fake profile", "pretending", "facebook", "instagram", "whatsapp"]):
        return IncidentCategory.social_media_impersonation

    return IncidentCategory.unknown


def score_priority(text: str, category: IncidentCategory) -> str:
    lowered = text.lower()
    high_risk_terms = ["money", "bank", "ransom", "encrypted", "company", "urgent", "debit", "transfer"]

    if category in {IncidentCategory.ransomware, IncidentCategory.online_banking_fraud}:
        return "High"
    if any(token in lowered for token in high_risk_terms):
        return "High"
    if category == IncidentCategory.unknown:
        return "Low"
    return "Medium"


def extract_indicators(text: str) -> List[str]:
    indicators = []
    lowered = text.lower()

    for token in ["http", "https", "otp", "bank", "whatsapp", "email", "password", "bitcoin"]:
        if token in lowered:
            indicators.append(token)

    return indicators


def recommend_actions(category: IncidentCategory) -> List[str]:
    default = [
        "Preserve screenshots, messages, links, emails, and transaction evidence.",
        "Avoid deleting suspicious messages until an analyst reviews them.",
        "Escalate to the appropriate technical, banking, or law-enforcement response channel where necessary.",
    ]

    category_actions = {
        IncidentCategory.phishing: [
            "Do not click the suspicious link again.",
            "Change passwords for affected accounts.",
            "Enable multi-factor authentication.",
        ],
        IncidentCategory.account_compromise: [
            "Change password immediately from a trusted device.",
            "Revoke unknown sessions and connected devices.",
            "Enable multi-factor authentication.",
        ],
        IncidentCategory.online_banking_fraud: [
            "Contact the bank immediately and request account protection.",
            "Preserve debit alerts, transaction references, and chat evidence.",
            "Report the incident through the bank's official fraud channel.",
        ],
        IncidentCategory.ransomware: [
            "Disconnect affected systems from the network.",
            "Do not pay without expert guidance.",
            "Preserve ransom notes and affected file samples for analysis.",
        ],
    }

    return category_actions.get(category, []) + default


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "cyberxtalk"}


@app.post("/report", response_model=IncidentResponse)
def report_incident(report: IncidentReport):
    text = report.incident_description
    language = detect_language(text)
    category = classify_incident(text)
    priority = score_priority(text, category)
    indicators = extract_indicators(text)
    actions = recommend_actions(category)

    return IncidentResponse(
        language_detected=language,
        category=category,
        priority=priority,
        indicators=indicators,
        recommended_actions=actions,
    )
