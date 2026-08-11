import math
from statistics import mean, pstdev

def detect_anomalies(columns: list[str], rows: list[dict]) -> list[dict]:
    """
    Finds anomalies in numeric columns of a query result.
    
    Refinements applied:
    1. Skips result sets under 6 rows to prevent noise from small datasets.
    2. Filters out primary-key-shaped columns (e.g., 'id', '*_id', 'id_*') to avoid false positives.
    """
    anomalies = []
    
    # 1. Skip if low row count
    if len(rows) < 6:
        return anomalies

    # 2. Identify candidate numeric columns and label column
    # Filter out columns ending in _id or is literally id
    def is_pk_like(col: str) -> bool:
        c = col.lower()
        return c == "id" or c.endswith("_id") or c.startswith("id_")

    candidate_cols = [col for col in columns if not is_pk_like(col)]
    
    # Find numeric columns
    numeric_cols = []
    label_col = None
    
    for col in candidate_cols:
        # Check if column is numeric
        values = []
        is_numeric = True
        for row in rows:
            val = row.get(col)
            if val is None:
                continue
            if isinstance(val, (int, float)):
                values.append(float(val))
            else:
                is_numeric = False
                break
        
        if is_numeric and values:
            numeric_cols.append(col)
        elif not is_numeric and label_col is None:
            # First non-numeric column is a candidate for label
            label_col = col

    # If no label column was found, use the first column that isn't a pk and isn't numeric,
    # or fallback to using indices
    if label_col is None:
        non_numeric = [col for col in candidate_cols if col not in numeric_cols]
        if non_numeric:
            label_col = non_numeric[0]

    # Z-score threshold and percent-change threshold
    Z_SCORE_THRESHOLD = 1.5
    PERCENT_CHANGE_THRESHOLD = 0.15  # 15%

    # 3. Analyze each numeric column
    for num_col in numeric_cols:
        values = [float(row.get(num_col) or 0) for row in rows]
        labels = [str(row.get(label_col) if label_col else idx) for idx, row in enumerate(rows)]
        
        # Check anomalies using leave-current-out baseline
        for i in range(1, len(values)):
            current = values[i]
            previous = values[i - 1]
            if previous == 0:
                continue
                
            baseline_values = values[:i] + values[i + 1 :]
            if len(baseline_values) < 2:
                continue
                
            b_mean = mean(baseline_values)
            b_stdev = pstdev(baseline_values)
            if b_stdev == 0:
                b_stdev = 1e-9
                
            z_score = (current - b_mean) / b_stdev
            percent_change = (current - previous) / abs(previous)
            
            if abs(z_score) >= Z_SCORE_THRESHOLD and abs(percent_change) >= PERCENT_CHANGE_THRESHOLD:
                severity = "drop" if percent_change < 0 else "spike"
                direction = "dropped" if severity == "drop" else "spiked"
                
                anomalies.append({
                    "column": num_col,
                    "row_index": i,
                    "label": labels[i],
                    "value": current,
                    "previous_value": previous,
                    "percent_change": round(percent_change * 100, 1),
                    "z_score": round(z_score, 2),
                    "severity": severity,
                    "description": (
                        f"Metric '{num_col}' {direction} by {abs(round(percent_change * 100, 1))}% "
                        f"(from {previous} to {current}) at '{labels[i]}', "
                        f"deviating significantly from the baseline pattern."
                    )
                })
                
    return anomalies
