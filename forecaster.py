import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

# Contract: consumption is the energy consumed during a 10-second interval.
READINGS_IN_30_DAYS = (30 * 24 * 60 * 60) / 10


def validate_history(df):
    """Return a normalized copy or raise ValueError for invalid sensor readings."""
    required = {"timestamp", "consumption"}
    if not required.issubset(df.columns):
        raise ValueError("Each reading requires timestamp and consumption")

    result = df.copy()
    if result.empty:
        return result

    if result["consumption"].map(lambda value: isinstance(value, (bool, np.bool_))).any():
        raise ValueError("consumption must be a finite, non-negative number")
    values = pd.to_numeric(result["consumption"], errors="coerce")
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError("consumption must be a finite, non-negative number")
    result["consumption"] = values.astype(float)
    if not np.isfinite(result["consumption"].sum()):
        raise ValueError("Total consumption exceeds the supported numeric range")

    # Require explicit date strings; integers are otherwise interpreted as nanoseconds.
    if not pd.api.types.is_datetime64_any_dtype(result["timestamp"]) and not result["timestamp"].map(lambda value: isinstance(value, str)).all():
        raise ValueError("timestamp must be a valid date string")
    timestamps = pd.to_datetime(result["timestamp"], utc=True, format="mixed", errors="coerce")
    if timestamps.isna().any():
        raise ValueError("timestamp must be a valid date string")
    result["timestamp"] = timestamps
    return result.sort_values("timestamp").reset_index(drop=True)


def predict_future_consumption(df):
    """Estimate the next 30 days, preserving periods of device inactivity."""
    # Also support direct callers with the same validation as the HTTP endpoint.
    if df.empty:
        return 0.0
    df = validate_history(df)

    positive = df.loc[df["consumption"] > 0, "consumption"]
    if positive.empty:
        return 0.0
    median = positive.median()
    # Divide instead of multiplying the median to avoid numeric overflow.
    df = df.loc[df["consumption"] / median < 20].copy()

    seconds = (df["timestamp"] - df["timestamp"].min()).dt.total_seconds()
    duration = seconds.max()
    average = float(df["consumption"].mean())

    if len(df) >= 20 and duration >= 300:
        model = LinearRegression().fit(seconds.to_numpy().reshape(-1, 1), df["consumption"])
        # The midpoint gives the integral average of a linear monthly projection.
        average = max(0.0, float(model.predict([[duration + 15 * 24 * 60 * 60]])[0]))

    prediction = average * READINGS_IN_30_DAYS
    if not np.isfinite(prediction):
        raise ValueError("Prediction exceeds the supported numeric range")
    return float(prediction)
