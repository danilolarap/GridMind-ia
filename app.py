import os

import pandas as pd
from flask import Flask, jsonify, request
from werkzeug.exceptions import BadRequest, UnsupportedMediaType

from forecaster import predict_future_consumption, validate_history

app = Flask(__name__)


@app.get("/health")
def health():
    return jsonify({"status": "IA Service is Operational", "engine": "GridMind-Predictor-v1"})


@app.post("/predict")
def predict():
    try:
        data = request.get_json()
    except (BadRequest, UnsupportedMediaType):
        return jsonify({"error": "Request body must contain valid JSON"}), 400

    if not isinstance(data, dict) or "history" not in data:
        return jsonify({"error": "No historical data provided"}), 400

    history = data["history"]
    if not isinstance(history, list) or any(not isinstance(row, dict) for row in history):
        return jsonify({"error": "history must be an array of objects"}), 400

    try:
        history_df = validate_history(
            pd.DataFrame(history) if history else pd.DataFrame(columns=["timestamp", "consumption"])
        )
        prediction = predict_future_consumption(history_df)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify({
        "current_total": float(history_df["consumption"].sum()),
        "predicted_next_30_days": prediction,
        "confidence_score": 0.85,
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
