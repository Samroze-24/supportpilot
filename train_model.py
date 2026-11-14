"""Train the SupportPilot intent classifier (TF-IDF + LogisticRegression).

Reads data/messages.csv (140 sample English messages, 7 intents), holds out
20% for honest evaluation, saves model.pkl + metrics.json.
Run:  python train_model.py
"""
import json
import os
import pickle

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def main():
    df = pd.read_csv(os.path.join(BASE_DIR, "data", "messages.csv"))
    X_train, X_test, y_train, y_test = train_test_split(
        df["text"], df["intent"], test_size=0.2, random_state=42, stratify=df["intent"]
    )
    model = Pipeline(
        [
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), stop_words="english")),
            ("clf", LogisticRegression(max_iter=1000, C=10)),
        ]
    )
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    accuracy = round(float(accuracy_score(y_test, y_pred)), 4)
    macro_f1 = round(float(f1_score(y_test, y_pred, average="macro")), 4)
    report = classification_report(y_test, y_pred, output_dict=True, zero_division=0)
    per_intent = {
        intent: {
            "precision": round(float(v["precision"]), 3),
            "recall": round(float(v["recall"]), 3),
            "f1": round(float(v["f1-score"]), 3),
            "support": int(v["support"]),
        }
        for intent, v in report.items()
        if intent in df["intent"].unique()
    }
    with open(os.path.join(BASE_DIR, "model.pkl"), "wb") as f:
        pickle.dump(model, f)
    metrics = {
        "model": "TF-IDF (1-2 grams) + LogisticRegression",
        "total_samples": int(len(df)),
        "train_samples": int(len(X_train)),
        "test_samples": int(len(X_test)),
        "accuracy": accuracy,
        "macro_f1": macro_f1,
        "per_intent": per_intent,
        "note": "Metrics are on a held-out 20% split of the sample dataset (data/messages.csv). Sample/synthetic data only — not real customer messages.",
    }
    with open(os.path.join(BASE_DIR, "metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"Trained on {len(X_train)} messages, tested on {len(X_test)}")
    print(f"Accuracy: {accuracy}, macro F1: {macro_f1}")
    return metrics


if __name__ == "__main__":
    main()
