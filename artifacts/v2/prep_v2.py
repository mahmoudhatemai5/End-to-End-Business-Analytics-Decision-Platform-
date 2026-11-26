"""Feature preparation for the v2 Olist models (plain-data bundle, no custom classes)."""
import numpy as np, pandas as pd
OHE = {"order_status": None, "payment_type": None, "customer_state": None, "seller_state": None}
CNT = ["customer_city", "seller_city", "product_category_name"]

def base_frame(raw):
    d = raw.copy()
    ts = pd.to_datetime(d["order_purchase_timestamp"]); est = pd.to_datetime(d["order_estimated_delivery_date"])
    d["purchase_dayofweek"] = ts.dt.dayofweek; d["purchase_hour"] = ts.dt.hour; d["purchase_month"] = ts.dt.month
    d["promised_delivery_days"] = (est - ts).dt.total_seconds() / 86400.0
    return d

def fit_bundle(train_raw):
    d = base_frame(train_raw)
    num = [c for c in d.columns if pd.api.types.is_numeric_dtype(d[c])]
    return {
        "medians": d[num].median().to_dict(),
        "ohe_levels": {c: sorted(d[c].dropna().astype(str).unique().tolist()) for c in OHE},
        "count_maps": {c: d[c].astype(str).value_counts().to_dict() for c in CNT},
    }

def transform(raw, bundle):
    d = base_frame(raw)
    for c, m in bundle["medians"].items():
        if c in d.columns: d[c] = d[c].fillna(m)
    out = d.copy()
    for c, levels in bundle["ohe_levels"].items():
        s = d[c].astype(str)
        for l in levels: out[f"{c}_{l}"] = (s == l).astype(float)
    for c in CNT:
        out[c] = d[c].astype(str).map(bundle["count_maps"][c]).fillna(0).astype(float)
    return out
