import decimal
import math
from statistics import mean, pstdev

from app.config import settings


def detect_anomalies(
    columns: list[str],
    rows: list[dict],
    z_threshold: float | None = None,
    pct_threshold: float | None = None,
) -> list[dict]:
    """
    Statistical anomaly detection for analytical query results.

    Identifies outliers using leave-one-out Z-score profiling and percentage change
    relative to the series baseline.

    Rules & Safeguards:
    1. Requires at least 6 data rows to avoid false alarms on small datasets.
    2. Filters out primary/foreign key columns (e.g. 'id', '*_id', 'id_*').
    3. Handles int, float, and decimal.Decimal types.
    4. Handles constant values and zero standard deviation safely without division by zero.
    5. Gracefully handles nulls and non-numeric fields.
    """
    z_threshold = z_threshold if z_threshold is not None else settings.anomaly_z_score_threshold
    pct_threshold = pct_threshold if pct_threshold is not None else settings.anomaly_percent_change_threshold

    anomalies = []

    # 1. Skip small datasets (<6 rows)
    if not rows or len(rows) < 6:
        return anomalies

    # 2. Filter out ID-like columns
    def is_pk_like(col: str) -> bool:
        c = col.lower()
        return c == "id" or c.endswith("_id") or c.startswith("id_")

    candidate_cols = [col for col in columns if not is_pk_like(col)]

    numeric_cols = []
    label_col = None

    for col in candidate_cols:
        is_numeric = True
        numeric_count = 0
        for row in rows:
            val = row.get(col)
            if val is None:
                continue
            if isinstance(val, (int, float, decimal.Decimal)):
                numeric_count += 1
            else:
                is_numeric = False
                break

        if is_numeric and numeric_count > 0:
            numeric_cols.append(col)
        elif not is_numeric and label_col is None:
            label_col = col

    if label_col is None:
        non_numeric = [col for col in candidate_cols if col not in numeric_cols]
        if non_numeric:
            label_col = non_numeric[0]

    # 3. Analyze each numeric column
    for num_col in numeric_cols:
        raw_values = []
        for r in rows:
            v = r.get(num_col)
            if v is None:
                raw_values.append(0.0)
            elif isinstance(v, decimal.Decimal):
                raw_values.append(float(v))
            else:
                try:
                    raw_values.append(float(v))
                except (ValueError, TypeError):
                    raw_values.append(0.0)

        labels = [str(row.get(label_col) if label_col else idx) for idx, row in enumerate(rows)]

        for i in range(len(raw_values)):
            current = raw_values[i]
            baseline_values = raw_values[:i] + raw_values[i + 1 :]

            if len(baseline_values) < 2:
                continue

            b_mean = mean(baseline_values)
            b_stdev = pstdev(baseline_values)

            # If all values are identical or zero deviation, no anomaly
            if b_stdev == 0 or math.isclose(b_stdev, 0, abs_tol=1e-9):
                continue

            z_score = (current - b_mean) / b_stdev

            # Compare against previous row if i > 0, else baseline mean
            if i > 0 and raw_values[i - 1] != 0:
                percent_change = (current - raw_values[i - 1]) / abs(raw_values[i - 1])
                comparison_ref = f"from {round(raw_values[i - 1], 2)} to {round(current, 2)}"
            elif b_mean != 0:
                percent_change = (current - b_mean) / abs(b_mean)
                comparison_ref = f"from baseline avg {round(b_mean, 2)} to {round(current, 2)}"
            else:
                continue

            if abs(z_score) >= z_threshold and abs(percent_change) >= pct_threshold:
                severity = "drop" if (z_score < 0 or percent_change < 0) else "spike"
                direction = "dropped" if severity == "drop" else "spiked"

                anomalies.append({
                    "column": num_col,
                    "row_index": i,
                    "label": labels[i],
                    "value": round(current, 2),
                    "baseline_mean": round(b_mean, 2),
                    "percent_change": round(percent_change * 100, 1),
                    "z_score": round(z_score, 2),
                    "severity": severity,
                    "description": (
                        f"Metric '{num_col}' {direction} by {abs(round(percent_change * 100, 1))}% "
                        f"({comparison_ref}) at '{labels[i]}', "
                        f"deviating significantly from the baseline (Z-score: {round(z_score, 2)})."
                    ),
                })

    return anomalies
