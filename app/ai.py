"""AI layer for SupportPilot: ML intent triage, sentiment, draft replies,
and knowledge-base retrieval. No API key needed — scikit-learn runs locally.

If model.pkl is missing (not trained yet), triage falls back to a small
keyword rule set so the app still works.
"""
import os
import pickle
import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, "model.pkl")

_model = None

INTENTS = ["order_status", "shipping", "refund", "complaint", "account", "product_question", "other"]

PRIORITY_BY_INTENT = {
    "complaint": "high",
    "refund": "high",
    "order_status": "normal",
    "shipping": "normal",
    "account": "normal",
    "product_question": "low",
    "other": "low",
}

_KEYWORD_INTENT = [
    (["refund", "return", "money back", "charged twice", "duplicate charge"], "refund"),
    (["where is my order", "order status", "tracking", "dispatched", "delivered", "parcel", "package"], "order_status"),
    (["ship to", "shipping cost", "delivery time", "deliver to", "express shipping", "international shipping"], "shipping"),
    (["unhappy", "unacceptable", "terrible", "disappointed", "complaint", "furious", "rude", "broken", "damaged"], "complaint"),
    (["log in", "login", "password", "account", "delete my account", "reset"], "account"),
    (["waterproof", "warranty", "material", "size", "fit", "battery", "does it", "is this", "what is"], "product_question"),
]

POSITIVE_WORDS = {"thank", "thanks", "great", "excellent", "love", "perfect", "amazing", "happy", "wonderful", "awesome", "good", "helpful"}
NEGATIVE_WORDS = {"unhappy", "terrible", "awful", "furious", "disappointed", "unacceptable", "broken", "damaged", "rude", "worst", "hate", "angry", "frustrated", "poor", "late", "missing", "wrong"}


def load_model():
    global _model
    if _model is None and os.path.exists(MODEL_PATH):
        with open(MODEL_PATH, "rb") as f:
            _model = pickle.load(f)
    return _model


def _keyword_intent(text: str) -> str:
    low = text.lower()
    for keywords, intent in _KEYWORD_INTENT:
        if any(k in low for k in keywords):
            return intent
    return "other"


def sentiment(text: str) -> str:
    low = text.lower()
    words = set(re.findall(r"[a-z]+", low))
    pos = len(words & POSITIVE_WORDS)
    neg = len(words & NEGATIVE_WORDS)
    if neg > pos:
        return "negative"
    if pos > neg:
        return "positive"
    return "neutral"


def triage(text: str) -> dict:
    """Returns intent, sentiment, suggested priority and confidence."""
    model = load_model()
    if model is not None:
        try:
            proba = model.predict_proba([text])[0]
            idx = int(proba.argmax())
            intent = str(model.classes_[idx])
            confidence = round(float(proba[idx]), 3)
        except Exception:
            intent = _keyword_intent(text)
            confidence = 0.5
    else:
        intent = _keyword_intent(text)
        confidence = 0.5
    sent = sentiment(text)
    priority = PRIORITY_BY_INTENT.get(intent, "normal")
    if sent == "negative" and priority in ("low", "normal"):
        priority = "high"
    return {
        "intent": intent,
        "sentiment": sent,
        "priority": priority,
        "confidence": confidence,
    }


def extract_entities(text: str) -> dict:
    order = re.search(r"#?ORD[- ]?(\d{4,})", text, re.IGNORECASE)
    tracking = re.search(r"\b([A-Z]{2}\d{6,}[A-Z]{0,2})\b", text)
    return {
        "order_number": f"ORD-{order.group(1)}" if order else None,
        "tracking_number": tracking.group(1) if tracking else None,
    }


DRAFT_TEMPLATES = {
    "order_status": "Hi {name}, thanks for reaching out. I've checked {order_ref} — it is currently in transit and the latest tracking update shows it moving toward you. I'll keep an eye on it and update you as soon as there is movement. Thanks for your patience!",
    "shipping": "Hi {name}, thanks for asking. We ship worldwide — standard delivery usually takes 3–7 business days internationally, and express is available at checkout for 1–3 business days. Shipping costs are calculated at checkout based on destination and weight.",
    "refund": "Hi {name}, I'm sorry about the trouble with {order_ref}. I've started a refund review for you — once the return is received, refunds are processed within 5–7 business days to your original payment method. I'll confirm here as soon as it is processed.",
    "complaint": "Hi {name}, I'm really sorry about this experience — that's not the standard we aim for. I've escalated your case to our senior team and flagged it as high priority. We'll follow up with a resolution within one business day.",
    "account": "Hi {name}, I can help with your account. Please try the password reset link on the login page first — if the email doesn't arrive within 10 minutes, check your spam folder and let me know, and I'll reset it manually from our side.",
    "product_question": "Hi {name}, great question! Let me check the exact specifications for you. In the meantime, you can find the full details, sizing guide and warranty information on the product page. I'll confirm the specifics here shortly.",
    "other": "Hi {name}, thanks for getting in touch! I've noted your message and passed it to the right team. Is there anything else I can help you with in the meantime?",
}


def generate_draft(intent: str, customer_name: str, text: str) -> str:
    entities = extract_entities(text)
    order_ref = f"order {entities['order_number']}" if entities["order_number"] else "your order"
    template = DRAFT_TEMPLATES.get(intent, DRAFT_TEMPLATES["other"])
    return template.format(name=customer_name or "there", order_ref=order_ref)


def suggest_kb_articles(ticket_text: str, articles, top_n: int = 3):
    """TF-IDF cosine retrieval over KB article title+body. Returns list of
    (article, score) sorted by score, only scores > 0.05."""
    if not articles:
        return []
    docs = [f"{a.title} {a.body}" for a in articles]
    vectorizer = TfidfVectorizer(stop_words="english")
    try:
        matrix = vectorizer.fit_transform(docs + [ticket_text])
    except ValueError:
        return []
    sims = cosine_similarity(matrix[-1], matrix[:-1])[0]
    ranked = sorted(zip(articles, sims), key=lambda x: x[1], reverse=True)
    return [(a, round(float(s), 3)) for a, s in ranked[:top_n] if s > 0.05]
