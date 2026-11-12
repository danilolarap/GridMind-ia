import unittest

import pandas as pd

from app import app
from forecaster import READINGS_IN_30_DAYS, predict_future_consumption


class PredictionTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def reading(self, consumption, timestamp="2026-11-12T12:00:00Z"):
        return {"timestamp": timestamp, "consumption": consumption}

    def test_health(self):
        self.assertEqual(self.client.get("/health").status_code, 200)

    def test_empty_history(self):
        response = self.client.post("/predict", json={"history": []})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["predicted_next_30_days"], 0)
        self.assertEqual(response.json["current_total"], 0)

    def test_invalid_bodies(self):
        for body in (None, [], 12, "text", {}, {"history": None},
                     {"history": {}}, {"history": [1]}, {"history": [{}]}):
            with self.subTest(body=body):
                response = self.client.post("/predict", json=body)
                self.assertEqual(response.status_code, 400)
                self.assertIn("error", response.json)

    def test_invalid_json(self):
        for content_type in ("application/json", "text/plain"):
            with self.subTest(content_type=content_type):
                response = self.client.post("/predict", data="{broken", content_type=content_type)
                self.assertEqual(response.status_code, 400)

    def test_invalid_consumption(self):
        for value in (-1, None, "invalid", True, float("inf"), float("nan")):
            with self.subTest(value=value):
                response = self.client.post("/predict", json={"history": [self.reading(value)]})
                self.assertEqual(response.status_code, 400)

    def test_invalid_timestamp(self):
        for timestamp in ("invalid", None, 123, "2026-02-30"):
            with self.subTest(timestamp=timestamp):
                response = self.client.post("/predict", json={
                    "history": [self.reading(1, timestamp)]
                })
                self.assertEqual(response.status_code, 400)

    def test_constant_consumption(self):
        response = self.client.post("/predict", json={"history": [self.reading(2)]})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["current_total"], 2)
        self.assertEqual(response.json["predicted_next_30_days"], 2 * READINGS_IN_30_DAYS)

    def test_inactivity_is_preserved(self):
        response = self.client.post("/predict", json={
            "history": [self.reading(0), self.reading(2)]
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["predicted_next_30_days"], READINGS_IN_30_DAYS)

    def test_all_zeros(self):
        response = self.client.post("/predict", json={"history": [self.reading(0)]})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["predicted_next_30_days"], 0)

    def test_outlier_filtered_only_from_forecast(self):
        response = self.client.post("/predict", json={
            "history": [self.reading(1), self.reading(1), self.reading(100)]
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["current_total"], 102)
        self.assertEqual(response.json["predicted_next_30_days"], READINGS_IN_30_DAYS)

    def test_trend_with_unsorted_mixed_timezones(self):
        timestamps = pd.date_range("2026-11-12", periods=21, freq="20s", tz="UTC")
        history = [self.reading(1 + i * 0.00001, timestamp.isoformat())
                   for i, timestamp in enumerate(timestamps)]
        history[0]["timestamp"] = "2026-11-11T19:00:00-05:00"
        response = self.client.post("/predict", json={"history": history[::-1]})
        self.assertEqual(response.status_code, 200)
        expected_average = 1 + 0.00001 / 20 * (400 + 15 * 24 * 60 * 60)
        self.assertAlmostEqual(response.json["predicted_next_30_days"],
                               expected_average * READINGS_IN_30_DAYS, places=5)

    def test_direct_caller_does_not_mutate_input(self):
        df = pd.DataFrame([self.reading(2)])
        original = df.copy(deep=True)
        self.assertEqual(predict_future_consumption(df), 2 * READINGS_IN_30_DAYS)
        pd.testing.assert_frame_equal(df, original)

    def test_direct_caller_rejects_missing_columns(self):
        with self.assertRaises(ValueError):
            predict_future_consumption(pd.DataFrame({"timestamp": ["2026-11-12"]}))


if __name__ == "__main__":
    unittest.main()
