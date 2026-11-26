"""
Olist predictor (Streamlit) - v3
  1) Delivery delay (LEAKAGE-FREE)   2) Freight cost   3) Delivery days
  4) Customer segments               5) After delivery: satisfaction + review-text model

What's new in v3:
  - Delay model no longer uses review_score / has_review_comment / seller_handling_days
    (they are only known after the order). Delivery days no longer uses seller_handling_days.
  - New freight, delivery-days and delay models (artifacts/v2/).
  - Review message -> stars uses a REAL trained model (TF-IDF + logistic regression on the
    Olist comments) instead of the keyword analyzer.
  - Every problem has 2-3 models (delay: HistGradientBoosting / XGBoost / RandomForest; freight, days, satisfaction:
    HistGradientBoosting / RandomForest), each tab has a Predict button.
  - Only tab 4 (segments) still uses the original notebook artifacts in artifacts/.

Run:
    pip install streamlit joblib scikit-learn xgboost category_encoders matplotlib pandas pydeck
    streamlit run streamlit_app_all_problems.py

Needs artifacts/v2/ (created by the v2 section at the end of the notebook) next to this file.
Tab 4 (segments) also needs the original artifacts/ files from the notebook.
"""
import math
import os
import sys
import joblib
import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

st.set_page_config(page_title="Olist Order Predictor", page_icon="📦", layout="wide")

ART_DIR = os.environ.get("ART_DIR", "artifacts")
V2_DIR = os.path.join(ART_DIR, "v2")
sys.path.insert(0, V2_DIR)
try:
    import prep_v2 as P
except Exception as e:  # noqa
    st.error(f"Could not find `{V2_DIR}/prep_v2.py`. Run the v2 section of the notebook first.\n\n{e}")
    st.stop()
COLORS = {"HistGradientBoosting": "#378ADD", "RandomForest": "#2E9E6B", "XGBoost": "#D85A30"}


# ---------------------------------------------------------------- loading
@st.cache_resource(show_spinner="Loading models...")
def load_v2(v2_dir):
    out = {n: joblib.load(os.path.join(v2_dir, f)) for n, f in
           [("bundle", "preprocess_v2.joblib"), ("delay", "delay_v2.joblib"), ("freight", "freight_v2.joblib"),
            ("days", "days_v2.joblib"), ("sat", "satisfaction_v2.joblib"), ("text", "review_text_model.joblib")]}
    return out


try:
    V2 = load_v2(V2_DIR)
except Exception as e:
    st.error(f"Could not load the v2 artifacts from `{V2_DIR}`. Run the v2 section at the end of the notebook.\n\n{e}")
    st.stop()
B = V2["bundle"]
MED = B["medians"]
LV = B["ohe_levels"]


# ---- original notebook artifacts (only for tab 4 segments and tab 5 satisfaction)
OLD = {"segments": "segments.joblib", "satisfaction": "satisfaction.joblib"}


@st.cache_resource(show_spinner="Loading original artifacts...")
def load_old(art_dir):
    out = {"bundle": None, "extra": None}
    p = os.path.join(art_dir, "preprocess.joblib")
    out["bundle"] = joblib.load(p) if os.path.exists(p) else None
    p = os.path.join(art_dir, "app_extra.joblib")
    out["extra"] = joblib.load(p) if os.path.exists(p) else None
    for k, f in OLD.items():
        p = os.path.join(art_dir, f)
        out[k] = joblib.load(p) if os.path.exists(p) else None
    return out


OLDA = load_old(ART_DIR)
bundle = OLDA["bundle"]
extra = OLDA["extra"]


def need_old_pack(key):
    if OLDA.get(key) is None or bundle is None or extra is None:
        st.info("This tab uses the original notebook artifacts (`artifacts/preprocess.joblib`, "
                f"`{OLD[key]}`, `app_extra.joblib`). They were not found next to the app.")
        return None
    return OLDA[key]


def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance between two lat/lng points."""
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def show_route_map(cust_lat, cust_lng, geo_lat, geo_lng):
    """Seller + customer on a map, with a line between them. Falls back to st.map."""
    pts = pd.DataFrame([
        {"lat": cust_lat, "lon": cust_lng, "place": "Customer"},
        {"lat": geo_lat, "lon": geo_lng, "place": "Seller"},
    ])
    try:
        import pydeck as pdk
        scatter = pdk.Layer(
            "ScatterplotLayer", data=pts, get_position=["lon", "lat"],
            get_fill_color=[55, 138, 221], get_radius=45000, pickable=True)
        arc = pdk.Layer(
            "ArcLayer",
            data=pd.DataFrame([{"slon": geo_lng, "slat": geo_lat, "dlon": cust_lng, "dlat": cust_lat}]),
            get_source_position=["slon", "slat"], get_target_position=["dlon", "dlat"],
            get_source_color=[216, 90, 48], get_target_color=[55, 138, 221], get_width=3)
        view = pdk.ViewState(latitude=(cust_lat + geo_lat) / 2, longitude=(cust_lng + geo_lng) / 2,
                             zoom=3.1, pitch=0)
        st.pydeck_chart(pdk.Deck(layers=[arc, scatter], initial_view_state=view,
                                 tooltip={"text": "{place}"}))
    except Exception:
        st.map(pts)


def simple_line(x, y, xlabel, ylabel, title, vline=None, hline=None, color="#378ADD"):
    """One clean curve, current value marked. Nothing else."""
    fig, ax = plt.subplots(figsize=(6, 3.2))
    ax.plot(x, y, color=color, lw=2.5)
    if vline is not None:
        ax.axvline(vline, color="gray", ls="--", lw=1)
    if hline is not None:
        ax.axhline(hline, color="#D85A30", ls="--", lw=1)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.tick_params(labelsize=10)
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)



# ---------------------------------------------------------------- original-notebook preprocessing (tabs 4 and 5 only)
def _build_full_old(inputs):
    r = bundle["raw_template"].copy()
    for k, v in inputs.items():
        r[k] = v
    num_in = list(bundle["num_imputer"].feature_names_in_)
    r[num_in] = bundle["num_imputer"].transform(r[num_in].astype(float))
    ohe_cols = bundle["ohe_cols"]
    enc = bundle["oh"].transform(r[ohe_cols])
    enc_df = pd.DataFrame(enc, columns=bundle["oh"].get_feature_names_out(ohe_cols), index=r.index)
    r = r.drop(columns=ohe_cols).join(enc_df)
    r = r.drop(columns=bundle["id_cols"], errors="ignore")
    fc = bundle["freq_cols"]
    r[fc] = bundle["count_encoder"].transform(r[fc])
    sc = bundle["scaler"]
    cols = list(sc.feature_names_in_)
    r[cols] = sc.transform(r[cols].astype(float))
    return r


def _build_cols_old(inputs, cols):
    return _build_full_old(inputs)[list(cols)]



# ---------------------------------------------------------------- feature building (v2)
def build_v2(rows, cols):
    """rows: list of dicts of raw inputs -> DataFrame with the model's columns (same steps as the notebook v2 section)."""
    recs = []
    for r in rows:
        base = dict(MED)
        base.update({"order_status": "delivered"})
        base.update(r)
        recs.append(base)
    return P.transform(pd.DataFrame(recs), B)[list(cols)]


def predict_delay(rows):
    pk = V2["delay"]
    X = build_v2(rows, pk["cols"])
    return {n: m.predict_proba(X)[:, 1] for n, m in pk["models"].items()}


def predict_reg(key, rows):
    """Regression pack with several models -> {model name: predictions in original units}."""
    pk = V2[key]
    X = build_v2(rows, pk["cols"])
    out = {}
    for n, mm in pk["models"].items():
        p = mm["model"].predict(X)
        out[n] = np.expm1(p) if mm["log_target"] else p
    return out


def predict_sat(rows):
    pk = V2["sat"]
    X = build_v2(rows, pk["cols"])
    return {n: m.predict_proba(X)[:, 1] for n, m in pk["models"].items()}


def predict_button(key):
    """Predict button: results stay on screen after the first click (like the original app)."""
    if st.button("Predict", type="primary", key=f"btn_{key}"):
        st.session_state[f"done_{key}"] = True
    return st.session_state.get(f"done_{key}", False)


def multi_line(x, series, xlabel, ylabel, title, vline=None, hline=None):
    fig, ax = plt.subplots(figsize=(6, 3.2))
    for n, y in series.items():
        ax.plot(x, y, label=n, color=COLORS.get(n, "#378ADD"), lw=2.5)
    if vline is not None:
        ax.axvline(vline, color="gray", ls="--", lw=1)
    if hline is not None:
        ax.axhline(hline, color="#D85A30", ls="--", lw=1)
    ax.set_xlabel(xlabel); ax.set_ylabel(ylabel); ax.set_title(title); ax.legend(frameon=False, fontsize=9)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    fig.tight_layout(); st.pyplot(fig); plt.close(fig)


# ---------------------------------------------------------------- sidebar
st.sidebar.title("Settings")
all_models = list(V2["delay"]["models"].keys())
chosen = st.sidebar.multiselect("Delay models to compare", all_models, default=all_models)
thr_mode = st.sidebar.radio("Delay threshold", ["Balanced (best F1)", "Catch more delays (recall-focused)"])
thr_key = "thresholds" if thr_mode.startswith("Balanced") else "thresholds_recall"
thresholds = {}
st.sidebar.subheader("Delay decision thresholds")
for n in chosen:
    thresholds[n] = st.sidebar.slider(n, 0.01, 0.99, float(min(max(V2["delay"][thr_key][n], 0.01), 0.99)), 0.01,
                                      key=f"thr_{n}_{thr_key}")
st.sidebar.caption("The delay models use only information known when the order is placed (no review, no seller handling time).")

# ---------------------------------------------------------------- helpers
def dv(k, fallback=0.0):
    v = MED.get(k, fallback)
    return float(v) if v == v else float(fallback)


_ni = st.number_input


def number_input(label, lo, hi, val, step=None, **kw):
    """number_input that never crashes when the default is outside the range."""
    val = float(min(max(val, lo), hi))
    return _ni(label, lo, hi, val, step, **kw)



# ---------------------------------------------------------------- inputs (grouped, each field asked once)
st.title("📦 Olist order predictor")
st.caption("Fill the order details once below. Each tab answers one question about the order. "
           "Review-related inputs live only in the last tab (they only exist after delivery).")

st.header("Order")
o1, o2, o3 = st.columns(3)
with o1:
    purchase_date = st.date_input("Purchase date", pd.Timestamp("2018-03-15"))
    purchase_hour = st.slider("Purchase hour", 0, 23, 12)
with o2:
    promised_days = st.slider("Promised delivery days", 1.0, 90.0,
                              float(np.clip(dv("promised_delivery_days", 22), 1, 90)), 0.5)
    total_items = number_input("Total items", 1.0, 30.0, max(1.0, dv("total_items", 1)), 1.0)
with o3:
    num_sellers = number_input("Unique sellers", 1.0, 10.0, max(1.0, dv("num_unique_sellers", 1)), 1.0)
    payment_type = st.selectbox("Payment type", LV["payment_type"])

st.header("Places & distance")
m1, m2 = st.columns([1, 1])
with m1:
    l1, l2 = st.columns(2)
    with l1:
        st.markdown("**Customer**")
        customer_state = st.selectbox("Customer state", LV["customer_state"],
                                      index=LV["customer_state"].index("SP") if "SP" in LV["customer_state"] else 0)
        cust_lat = number_input("Customer latitude", -35.0, 6.0, dv("customer_lat", -22.9), format="%.4f")
        cust_lng = number_input("Customer longitude", -75.0, -30.0, dv("customer_lng", -48.0), format="%.4f")
    with l2:
        st.markdown("**Seller**")
        seller_state = st.selectbox("Seller state", LV["seller_state"],
                                    index=LV["seller_state"].index("SP") if "SP" in LV["seller_state"] else 0)
        geo_lat = number_input("Seller latitude", -35.0, 6.0, dv("geolocation_lat", -22.9), format="%.4f")
        geo_lng = number_input("Seller longitude", -75.0, -30.0, dv("geolocation_lng", -46.6), format="%.4f")
    auto_distance = haversine_km(cust_lat, cust_lng, geo_lat, geo_lng)
    manual_distance = st.checkbox("Enter the distance manually instead", value=False)
    if manual_distance:
        distance = number_input("Distance seller → customer (km)", 0.0, 9000.0,
                                min(9000.0, max(0.0, auto_distance)), 10.0)
    else:
        distance = auto_distance
        st.success(f"Distance seller → customer: **{auto_distance:,.0f} km** (computed from the coordinates)")
with m2:
    show_route_map(cust_lat, cust_lng, geo_lat, geo_lng)

st.header("Product & price")
p1, p2, p3 = st.columns(3)
with p1:
    price = number_input("Price", 0.0, 10000.0, dv("price", 75), 5.0)
    freight = number_input("Freight value", 0.0, 1000.0, dv("freight_value", 16), 1.0)
with p2:
    weight = number_input("Product weight (kg)", 0.0, 50.0, dv("product_weight_kg", 0.8), 0.1)
    volume = number_input("Product volume (m3)", 0.0, 2.0, dv("product_volume_m3", 0.01), 0.001, format="%.4f")
with p3:
    photos = number_input("Product photos", 1.0, 20.0, max(1.0, dv("product_photos_qty", 1)), 1.0)
    cat_counts = B["count_maps"]["product_category_name"]
    cats = sorted(cat_counts, key=lambda k: -cat_counts[k])
    category = st.selectbox("Product category", cats)

st.header("Payment")
q1, q2, q3 = st.columns(3)
with q1:
    total_payment = number_input("Total payment value", 0.0, 20000.0, dv("total_payment_value", 110), 5.0)
with q2:
    num_payments = number_input("Number of payments", 1.0, 30.0, max(1.0, dv("num_payments", 1)), 1.0)
    installments = number_input("Max installments", 1.0, 30.0, max(1.0, dv("payment_installments_max", 2)), 1.0)
with q3:
    approval_days = number_input("Payment approval (days)", 0.0, 30.0, dv("payment_approval_days", 0.35), 0.1)

with st.expander("Advanced (zip codes and cities)"):
    b1, b2 = st.columns(2)
    seller_zip = number_input("Seller zip prefix", 0.0, 99999.0, dv("seller_zip_code_prefix", 10000), 1.0)
    cust_zip = number_input("Customer zip prefix", 0.0, 99999.0, dv("customer_zip_code_prefix", 10000), 1.0)
    cc, sc = B["count_maps"]["customer_city"], B["count_maps"]["seller_city"]
    ccities = sorted(cc, key=lambda k: -cc[k]); scities = sorted(sc, key=lambda k: -sc[k])
    cust_city = b1.selectbox("Customer city", ccities)
    seller_city = b2.selectbox("Seller city", scities)


def make_inputs(promised=None, **over):
    promised = promised_days if promised is None else promised
    ts = pd.Timestamp(purchase_date) + pd.Timedelta(hours=int(purchase_hour))
    d_ = {
        "order_status": "delivered",
        "order_purchase_timestamp": ts,
        "order_estimated_delivery_date": ts + pd.Timedelta(days=float(promised)),
        "total_items": total_items, "num_unique_sellers": num_sellers,
        "customer_state": customer_state, "seller_state": seller_state,
        "price": price, "freight_value": freight,
        "product_weight_kg": weight, "product_volume_m3": volume, "product_photos_qty": photos,
        "distance_km": distance, "payment_type": payment_type,
        "total_payment_value": total_payment, "num_payments": num_payments,
        "payment_installments_max": installments, "payment_approval_days": approval_days,
        "customer_lat": cust_lat, "customer_lng": cust_lng, "geolocation_lat": geo_lat, "geolocation_lng": geo_lng,
        "seller_zip_code_prefix": seller_zip, "customer_zip_code_prefix": cust_zip,
        "product_category_name": category, "customer_city": cust_city, "seller_city": seller_city,
    }
    d_.update(over)
    return d_


def old_inputs(**over):
    """Inputs for the ORIGINAL notebook artifacts (segments / satisfaction tabs)."""
    ts = pd.Timestamp(purchase_date) + pd.Timedelta(hours=int(purchase_hour))
    d_ = make_inputs(**over)
    d_.update({"purchase_dayofweek": ts.dayofweek, "purchase_hour": ts.hour, "purchase_month": ts.month,
               "promised_delivery_days": float(promised_days),
               "seller_handling_days": float(bundle["defaults"].get("seller_handling_days", 2.0)) if bundle else 2.0,
               "review_score": np.nan, "has_review_comment": 0})
    d_.update(over)
    return d_


# ---------------------------------------------------------------- tabs
tab_delay, tab_freight, tab_days, tab_seg, tab_after = st.tabs(
    ["1) Delay", "2) Freight cost", "3) Delivery days", "4) Customer segment",
     "5) After delivery · satisfaction & review"])

with tab_delay:
    models = [n for n in chosen]
    if not models:
        st.warning("Pick at least one model from the sidebar.")
    else:
        st.caption("Leakage-free: uses only what is known when the order is placed.")
        if predict_button("delay"):
            probs = predict_delay([make_inputs()])
            p = {n: float(probs[n][0]) for n in models}
            st.divider()
            cols = st.columns(len(p))
            for col, (n, v) in zip(cols, p.items()):
                late = v >= thresholds[n]
                col.metric(n, f"{v * 100:.1f}% delay", delta=("Likely DELAYED" if late else "Likely on time"),
                           delta_color="inverse" if late else "normal")
            avg = float(np.mean(list(p.values())))
            votes = sum(v >= thresholds[n] for n, v in p.items())
            st.info(f"Average delay probability: **{avg * 100:.1f}%** - {votes} of {len(p)} models flag this order as delayed.")
            g1, g2 = st.columns(2)
            with g1:
                fig, ax = plt.subplots(figsize=(6, 3.2))
                names = list(p.keys()); vals = [p[n] * 100 for n in names]
                bars = ax.bar(names, vals, color=[COLORS.get(n, "#378ADD") for n in names], width=0.55)
                for b_, v in zip(bars, vals):
                    ax.text(b_.get_x() + b_.get_width() / 2, v + 2, f"{v:.0f}%", ha="center", fontsize=12, fontweight="bold")
                ax.set_ylim(0, 100); ax.set_ylabel("Delay probability (%)"); ax.set_title("How likely is this order to be late?")
                ax.tick_params(axis="x", labelsize=8)
                for side in ("top", "right"):
                    ax.spines[side].set_visible(False)
                fig.tight_layout(); st.pyplot(fig); plt.close(fig)
            with g2:
                sweep = np.arange(3, 61, 2.0)
                sp = predict_delay([make_inputs(s_) for s_ in sweep])
                multi_line(sweep, {n: sp[n] * 100 for n in models}, "Promised delivery days", "Delay probability (%)",
                           "What if the promised time changes?", vline=promised_days)
            st.caption("The dashed line is the promised delivery days you entered above.")

with tab_freight:
    st.subheader("Expected freight (shipping) cost")
    if predict_button("freight"):
        est = {n: float(v[0]) for n, v in predict_reg("freight", [make_inputs()]).items()}
        cols = st.columns(len(est))
        for col, (n, v) in zip(cols, est.items()):
            col.metric(n, f"{v:,.2f}")
        g1, g2 = st.columns(2)
        with g1:
            sw = np.linspace(10, 3000, 25)
            multi_line(sw, predict_reg("freight", [make_inputs(distance_km=s_) for s_ in sw]),
                       "Distance (km)", "Freight", "Freight vs distance", vline=distance)
        with g2:
            sw = np.linspace(0.1, 30, 25)
            multi_line(sw, predict_reg("freight", [make_inputs(product_weight_kg=s_) for s_ in sw]),
                       "Product weight (kg)", "Freight", "Freight vs weight", vline=weight)
        st.caption("The dashed line is your current value. The freight value typed above is not used by these models.")

with tab_days:
    st.subheader("Expected actual delivery time")
    st.caption("Leakage-free: no seller handling time (it is only known after the order ships).")
    if predict_button("days"):
        est = {n: float(v[0]) for n, v in predict_reg("days", [make_inputs()]).items()}
        cols = st.columns(len(est) + 1)
        for col, (n, v) in zip(cols, est.items()):
            col.metric(f"{n}: predicted days", f"{v:.1f}", delta=f"{v - promised_days:+.1f} vs promised",
                       delta_color="inverse" if v > promised_days else "normal")
        cols[-1].metric("Promised days", f"{promised_days:.1f}")
        g1, g2 = st.columns(2)
        with g1:
            sw = np.linspace(10, 3000, 25)
            multi_line(sw, predict_reg("days", [make_inputs(distance_km=s_) for s_ in sw]),
                       "Distance (km)", "Predicted days", "Delivery days vs distance", vline=distance, hline=promised_days)
        with g2:
            sw = np.linspace(0.1, 30, 25)
            multi_line(sw, predict_reg("days", [make_inputs(product_weight_kg=s_) for s_ in sw]),
                       "Product weight (kg)", "Predicted days", "Delivery days vs weight", vline=weight, hline=promised_days)
        st.caption("Orange dashed line = promised delivery days. Above it means the model expects a late delivery.")

# ---- 4) customer segment
with tab_seg:
    pack = need_old_pack("segments")
    if pack and predict_button("seg"):
        st.subheader("Which customer segment is this order?")
        Xs = _build_cols_old(old_inputs(), pack["cols"]).clip(-5, 5)
        k = int(pack["model"].predict(Xs)[0])
        name = pack["names"][k]
        size = pack["sizes"].get(k, float("nan"))
        c1_, c2_ = st.columns(2)
        c1_.metric("Segment", f"{name} (cluster {k})")
        c2_.metric("Share of all customers", f"{size * 100:.0f}%")

        palette = ["#378ADD", "#D85A30", "#2E9E6B", "#9B59B6"]
        fig, ax = plt.subplots(figsize=(7, 3.6))
        for c in sorted(pack["names"]):
            m = pack["bg_cluster"] == c
            ax.scatter(pack["bg_pcs"][m, 0], pack["bg_pcs"][m, 1], s=6, alpha=0.4,
                       color=palette[c % 4], label=pack["names"][c])
        pt = pack["pca"].transform(Xs)
        ax.scatter(pt[:, 0], pt[:, 1], marker="*", s=320, color="black", edgecolor="white",
                   label="This order", zorder=5)
        ax.set_xlabel("PC1")
        ax.set_ylabel("PC2")
        ax.set_title("Where this order sits among customers")
        ax.legend(frameon=False, fontsize=9)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        fig.tight_layout()
        st.pyplot(fig)
        plt.close(fig)

        with st.expander("Compare this order to the segment averages"):
            prof = pd.DataFrame(pack["profile"])  # rows = cluster, cols = metrics
            prof.index = [pack["names"][i] for i in prof.index]
            mine = {"total_payment_value": total_payment, "total_items": total_items, "price": price,
                    "freight_value": freight, "payment_installments_max": installments}
            prof.loc["This order"] = pd.Series(mine)
            fig, ax = plt.subplots(figsize=(7, 3.4))
            prof.T.plot(kind="bar", ax=ax, color=palette[:len(pack["names"])] + ["black"])
            ax.set_title("Average per segment vs this order")
            ax.tick_params(axis="x", rotation=25)
            ax.legend(frameon=False, fontsize=9)
            for side in ("top", "right"):
                ax.spines[side].set_visible(False)
            fig.tight_layout()
            st.pyplot(fig)
            plt.close(fig)



# ---------------------------------------------------------------- review text model
SAT_LABELS = {1: ("Very dissatisfied", "😡"), 2: ("Dissatisfied", "🙁"), 3: ("Neutral", "😐"),
              4: ("Satisfied", "🙂"), 5: ("Very satisfied", "🤩")}


def review_to_stars(text):
    """Real trained model (TF-IDF + logistic regression). Returns (stars, {star: probability}, expected stars)."""
    t = V2["text"]
    pr = t["model"].predict_proba(t["vectorizer"].transform([text]))[0]
    probs = {int(c): float(p) for c, p in zip(t["classes"], pr)}
    stars = max(probs, key=probs.get)
    return stars, probs, sum(k * v for k, v in probs.items())


with tab_after:
    st.subheader("After the order is delivered")
    st.caption("This whole tab is for AFTER the customer actually receives the order.")
    actual_days = st.slider("Actual delivery days (what really happened)", 1.0, 90.0,
                            float(np.clip(promised_days, 1, 90)), 0.5)
    sat_mode = st.radio("Satisfaction threshold", ["Balanced (best F1)", "Catch more unsatisfied (recall-focused)"], horizontal=True)
    sk = "thresholds" if sat_mode.startswith("Balanced") else "thresholds_recall"

    def sat_rows(a_list):
        return [make_inputs(actual_delivery_days=a_, delivery_vs_estimated=a_ - promised_days) for a_ in a_list]

    if predict_button("sat"):
        pr = {n: float(v[0]) for n, v in predict_sat(sat_rows([actual_days])).items()}
        cols = st.columns(len(pr) + 1)
        for col, (n, v) in zip(cols, pr.items()):
            thr_n = V2["sat"][sk][n]
            bad = v >= thr_n
            col.metric(f"{n}: P(unsatisfied)", f"{v * 100:.1f}%", delta="Likely UNSATISFIED" if bad else "Likely satisfied",
                       delta_color="inverse" if bad else "normal")
        cols[-1].metric("Delivery vs promise", f"{actual_days - promised_days:+.1f} days")
        sw = np.linspace(1, 60, 30)
        sp = predict_sat(sat_rows(sw))
        multi_line(sw, {n: v * 100 for n, v in sp.items()}, "Actual delivery days", "P(unsatisfied) %",
                   "Satisfaction vs delivery time", vline=actual_days)
        st.caption("Unsatisfied = review score of 3 or less. Dashed line = the delivery time you entered.")

    st.divider()
    st.subheader("Review message → stars")
    st.caption("Paste the customer's review message (Portuguese works best). A real model trained on the Olist reviews estimates the stars.")
    review_text = st.text_area("Review message", height=120,
                               placeholder="Ex.: Produto excelente, chegou antes do prazo, recomendo!")
    if st.button("Analyze review", type="primary"):
        if not review_text.strip():
            st.warning("Paste a review message first.")
        else:
            stars, probs, exp = review_to_stars(review_text)
            label, emoji = SAT_LABELS[stars]
            r1, r2, r3 = st.columns(3)
            r1.metric("Estimated satisfaction", f"{label} {emoji}")
            r2.metric("Estimated score", "★" * stars + "☆" * (5 - stars))
            r3.metric("Average expected stars", f"{exp:.2f}")
            fig, ax = plt.subplots(figsize=(6, 2.6))
            ax.bar([str(k) for k in probs], [v * 100 for v in probs.values()], color="#378ADD", width=0.55)
            ax.set_xlabel("Stars"); ax.set_ylabel("Probability (%)"); ax.set_title("Model confidence per star")
            for side in ("top", "right"):
                ax.spines[side].set_visible(False)
            fig.tight_layout(); st.pyplot(fig); plt.close(fig)
            st.caption("Trained on real Olist comments: about 60% exact-star accuracy, 82% on negative/neutral/positive. "
                       "Very bad (1) and very good (5) reviews are reliable; 2-4 stars are often confused. It is not an LLM.")
