import decimal
import pytest
from app.analysis.anomaly import detect_anomalies


def test_detect_spike_anomaly():
    data = [
        {"month": "2026-01", "revenue": 10000.0},
        {"month": "2026-02", "revenue": 10500.0},
        {"month": "2026-03", "revenue": 10200.0},
        {"month": "2026-04", "revenue": 9800.0},
        {"month": "2026-05", "revenue": 38000.0},  # Massive promo spike (~3.8x)
        {"month": "2026-06", "revenue": 10100.0},
        {"month": "2026-07", "revenue": 10400.0},
    ]
    cols = ["month", "revenue"]
    anomalies = detect_anomalies(cols, data)
    assert len(anomalies) == 1
    assert anomalies[0]["column"] == "revenue"
    assert anomalies[0]["severity"] == "spike"
    assert anomalies[0]["label"] == "2026-05"
    assert anomalies[0]["value"] == 38000.0
    assert anomalies[0]["z_score"] > 2.0


def test_detect_drop_anomaly():
    data = [
        {"day": "Mon", "visitors": 500},
        {"day": "Tue", "visitors": 520},
        {"day": "Wed", "visitors": 510},
        {"day": "Thu", "visitors": 530},
        {"day": "Fri", "visitors": 50},   # Outage drop (10x drop)
        {"day": "Sat", "visitors": 515},
        {"day": "Sun", "visitors": 505},
    ]
    cols = ["day", "visitors"]
    anomalies = detect_anomalies(cols, data)
    assert len(anomalies) == 1
    assert anomalies[0]["column"] == "visitors"
    assert anomalies[0]["severity"] == "drop"
    assert anomalies[0]["label"] == "Fri"
    assert anomalies[0]["value"] == 50
    assert anomalies[0]["z_score"] < -2.0


def test_no_anomaly_on_normal_data():
    data = [
        {"month": "Jan", "sales": 100},
        {"month": "Feb", "sales": 105},
        {"month": "Mar", "sales": 98},
        {"month": "Apr", "sales": 102},
        {"month": "May", "sales": 107},
        {"month": "Jun", "sales": 99},
    ]
    cols = ["month", "sales"]
    anomalies = detect_anomalies(cols, data)
    assert anomalies == []


def test_insufficient_rows_returns_empty():
    # Fewer than 6 rows should return no anomalies to prevent noise
    data = [
        {"month": "Jan", "sales": 100},
        {"month": "Feb", "sales": 500},  # Even with large jump, < 6 rows is skipped
        {"month": "Mar", "sales": 100},
    ]
    cols = ["month", "sales"]
    anomalies = detect_anomalies(cols, data)
    assert anomalies == []


def test_constant_values_does_not_crash_or_false_alarm():
    data = [{"month": f"M{i}", "count": 42} for i in range(10)]
    cols = ["month", "count"]
    anomalies = detect_anomalies(cols, data)
    assert anomalies == []


def test_handles_null_values_gracefully():
    data = [
        {"month": "M1", "sales": 100},
        {"month": "M2", "sales": None},
        {"month": "M3", "sales": 105},
        {"month": "M4", "sales": 102},
        {"month": "M5", "sales": 98},
        {"month": "M6", "sales": 103},
        {"month": "M7", "sales": 450},  # Spike
    ]
    cols = ["month", "sales"]
    anomalies = detect_anomalies(cols, data)
    assert len(anomalies) == 1
    assert anomalies[0]["label"] == "M7"


def test_ignores_id_like_columns():
    # Sequence IDs 1 to 7 should not be analyzed even though they are numeric
    data = [
        {"id": 1, "customer_id": 101, "order_id": 1001, "score": 50},
        {"id": 2, "customer_id": 102, "order_id": 1002, "score": 52},
        {"id": 3, "customer_id": 103, "order_id": 1003, "score": 49},
        {"id": 4, "customer_id": 104, "order_id": 1004, "score": 51},
        {"id": 5, "customer_id": 105, "order_id": 1005, "score": 53},
        {"id": 6, "customer_id": 99999, "order_id": 88888, "score": 50},  # Big jump in IDs
    ]
    cols = ["id", "customer_id", "order_id", "score"]
    anomalies = detect_anomalies(cols, data)
    assert anomalies == []


def test_handles_decimal_values():
    data = [
        {"month": "M1", "revenue": decimal.Decimal("100.50")},
        {"month": "M2", "revenue": decimal.Decimal("102.30")},
        {"month": "M3", "revenue": decimal.Decimal("99.80")},
        {"month": "M4", "revenue": decimal.Decimal("101.10")},
        {"month": "M5", "revenue": decimal.Decimal("103.00")},
        {"month": "M6", "revenue": decimal.Decimal("420.75")},  # Spike
    ]
    cols = ["month", "revenue"]
    anomalies = detect_anomalies(cols, data)
    assert len(anomalies) == 1
    assert anomalies[0]["column"] == "revenue"
    assert anomalies[0]["severity"] == "spike"


def test_detect_seeded_database_anomaly():
    """Verifies that the exact seeded database monthly order counts produce
    the verified anomaly metrics: +235.7% change and Z-score 25.02."""
    data = [
        {"month": "2025-09", "order_count": 65},
        {"month": "2025-10", "order_count": 68},
        {"month": "2025-11", "order_count": 72},
        {"month": "2025-12", "order_count": 85},
        {"month": "2026-01", "order_count": 62},
        {"month": "2026-02", "order_count": 60},
        {"month": "2026-03", "order_count": 66},
        {"month": "2026-04", "order_count": 70},
        {"month": "2026-05", "order_count": 235},  # May spike
        {"month": "2026-06", "order_count": 74},
        {"month": "2026-07", "order_count": 71},
        {"month": "2026-08", "order_count": 75},
    ]
    cols = ["month", "order_count"]
    anomalies = detect_anomalies(cols, data)
    assert len(anomalies) == 1
    assert anomalies[0]["column"] == "order_count"
    assert anomalies[0]["label"] == "2026-05"
    assert anomalies[0]["value"] == 235.0
    assert anomalies[0]["percent_change"] == 235.7
    assert anomalies[0]["z_score"] == 25.02

