import streamlit as st
import hashlib
from snowflake.snowpark.functions import col
import numpy as np
import pandas as pd
import pydeck as pdk
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from snowflake.snowpark.context import get_active_session
import base64

st.set_page_config(page_title="NSES UI", layout="wide")
session = get_active_session()

def get_houston_baseline(session):
    query = """
    SELECT
        "DATE" AS DATE,
        TOTAL_GENERATION_MWH
    FROM PWC_DB.PUBLIC.HOUSTON_BASELINE
    WHERE TOTAL_GENERATION_MWH IS NOT NULL
    ORDER BY TO_DATE("DATE", 'DY MON DD YYYY')
    """
    return session.sql(query).to_pandas()

def apply_dark_theme():
    st.markdown("""
    <style>
        [data-testid="stAppViewContainer"] {
            background: #1a1a1a;
            color: #e0e0e0;
        }
        [data-testid="stSidebar"] {
            background: #111111;
            border-right: 1px solid #333333;
        }
        [data-testid="stSidebar"] * {
            color: #e0e0e0 !important;
        }
        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 2rem;
        }
        .nses-header {
            background: #222222;
            border: 1px solid #333333;
            border-radius: 14px;
            padding: 1rem 1.2rem;
            box-shadow: 0 6px 18px rgba(0,0,0,0.4);
            margin-bottom: 1.2rem;
        }
        .nses-title {
            font-weight: 800;
            font-size: 1.25rem;
            letter-spacing: 0.08em;
            color: #ffffff;
        }
        .nses-subtitle {
            font-size: 0.85rem;
            color: #999999;
        }
        .nses-card {
            background: #222222;
            border: 1px solid #333333;
            border-radius: 16px;
            padding: 1.2rem;
            box-shadow: 0 8px 20px rgba(0,0,0,0.4);
        }
        .section-label {
            font-weight: 700;
            font-size: 1.1rem;
            color: #ffffff;
            margin-bottom: 0.5rem;
        }
        h1, h2, h3, h4, h5, h6, p, span, label, .stMarkdown {
            color: #e0e0e0 !important;
        }
        .stButton > button {
            border-radius: 10px;
            border: 1px solid #444444;
            background: #2a2a2a;
            color: #e0e0e0;
            padding: 0.6rem 0.9rem;
        }
        .stButton > button:hover {
            background: #3a3a3a;
            border-color: #555555;
        }
        input, textarea {
            border-radius: 10px !important;
            border: 1px solid #444444 !important;
            background: #2a2a2a !important;
            color: #e0e0e0 !important;
        }
        div[data-baseweb="select"] > div {
            border-radius: 10px;
            border: 1px solid #444444;
            background: #2a2a2a;
        }
        div[data-baseweb="select"] * {
            color: #e0e0e0 !important;
        }
        hr {
            border-color: #333333 !important;
        }
        .stRadio label, .stSelectbox label {
            color: #e0e0e0 !important;
        }
        [data-testid="stCaption"] {
            color: #888888 !important;
        }
        [data-testid="stMetric"] {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
        }
        [data-testid="stMetricValue"] {
            background: transparent !important;
        }
    </style>
    """, unsafe_allow_html=True)

apply_dark_theme()

REGIONS = {
    "Houston (Harris County)": {"lat": 29.7604, "lng": -95.3698, "zoom": 10},
    "Downtown Loop": {"lat": 29.7589, "lng": -95.3621, "zoom": 13},
    "North Suburbs": {"lat": 30.0200, "lng": -95.4100, "zoom": 11},
    "East Industrial": {"lat": 29.7400, "lng": -95.2500, "zoom": 11},
    "Coastal": {"lat": 29.3000, "lng": -94.7900, "zoom": 10},
}

POWER_PLANTS = pd.DataFrame([
    {"name": "Deer Park", "lat": 29.71341, "lng": -95.1345},
    {"name": "Channelview", "lat": 29.83695, "lng": -95.1217},
    {"name": "Pasadena", "lat": 29.72475, "lng": -95.1765},
    {"name": "Channel Energy", "lat": 29.7189, "lng": -95.2319},
    {"name": "Odyssey Energy", "lat": 29.8161, "lng": -95.1077},
    {"name": "ExxonMobil", "lat": 29.75912, "lng": -95.0097},
])

SUBSTATIONS = pd.DataFrame([
    {"name": "West Houston Sub", "lat": 29.7550, "lng": -95.2200, "voltage": "345kV", "load": 82},
    {"name": "Baytown Sub", "lat": 29.7700, "lng": -95.0400, "voltage": "345kV", "load": 71},
    {"name": "Ship Channel Sub", "lat": 29.7400, "lng": -95.1500, "voltage": "138kV", "load": 93},
    {"name": "La Porte Sub", "lat": 29.6700, "lng": -95.0600, "voltage": "138kV", "load": 67},
    {"name": "North Channel Sub", "lat": 29.8300, "lng": -95.0800, "voltage": "345kV", "load": 55},
])

TRANSMISSION_LINES = pd.DataFrame([
    {"src_lat": 29.7550, "src_lng": -95.2200, "dst_lat": 29.7400, "dst_lng": -95.1500, "voltage": "345kV"},
    {"src_lat": 29.7400, "src_lng": -95.1500, "dst_lat": 29.7700, "dst_lng": -95.0400, "voltage": "345kV"},
    {"src_lat": 29.7700, "src_lng": -95.0400, "dst_lat": 29.8300, "dst_lng": -95.0800, "voltage": "345kV"},
    {"src_lat": 29.7400, "src_lng": -95.1500, "dst_lat": 29.6700, "dst_lng": -95.0600, "voltage": "138kV"},
    {"src_lat": 29.8300, "src_lng": -95.0800, "dst_lat": 29.7550, "dst_lng": -95.2200, "voltage": "345kV"},
    {"src_lat": 29.6700, "src_lng": -95.0600, "dst_lat": 29.7700, "dst_lng": -95.0400, "voltage": "138kV"},
    {"src_lat": 29.7550, "src_lng": -95.2200, "dst_lat": 29.7189, "dst_lng": -95.2319, "voltage": "138kV"},
    {"src_lat": 29.7400, "src_lng": -95.1500, "dst_lat": 29.72475, "dst_lng": -95.1765, "voltage": "138kV"},
    {"src_lat": 29.7400, "src_lng": -95.1500, "dst_lat": 29.71341, "dst_lng": -95.1345, "voltage": "138kV"},
    {"src_lat": 29.8300, "src_lng": -95.0800, "dst_lat": 29.8161, "dst_lng": -95.1077, "voltage": "138kV"},
    {"src_lat": 29.8300, "src_lng": -95.0800, "dst_lat": 29.83695, "dst_lng": -95.1217, "voltage": "138kV"},
    {"src_lat": 29.7700, "src_lng": -95.0400, "dst_lat": 29.75912, "dst_lng": -95.0097, "voltage": "138kV"},
])

FEEDERS = pd.DataFrame([
    {"src_lat": 29.71341, "src_lng": -95.1345, "dst_lat": 29.70, "dst_lng": -95.15},
    {"src_lat": 29.71341, "src_lng": -95.1345, "dst_lat": 29.72, "dst_lng": -95.12},
    {"src_lat": 29.83695, "src_lng": -95.1217, "dst_lat": 29.85, "dst_lng": -95.10},
    {"src_lat": 29.83695, "src_lng": -95.1217, "dst_lat": 29.82, "dst_lng": -95.14},
    {"src_lat": 29.72475, "src_lng": -95.1765, "dst_lat": 29.71, "dst_lng": -95.19},
    {"src_lat": 29.75912, "src_lng": -95.0097, "dst_lat": 29.77, "dst_lng": -94.99},
    {"src_lat": 29.7189, "src_lng": -95.2319, "dst_lat": 29.73, "dst_lng": -95.25},
    {"src_lat": 29.8161, "src_lng": -95.1077, "dst_lat": 29.80, "dst_lng": -95.09},
])

PLANT_CAPACITY = {
    "Deer Park": 1000, "Channelview": 800, "Pasadena": 600,
    "Channel Energy": 750, "Odyssey Energy": 500, "ExxonMobil": 900,
}

PLANT_COORDS = {row["name"]: (row["lat"], row["lng"]) for _, row in POWER_PLANTS.iterrows()}

SCENARIO_MULTIPLIERS = {
    "Normal": 1.0,
    "Fire ": 1.0,
    "Flood ": 1.1,
    "Severe Storm": 1.15,
    "Hurricane": 1.35,
    "Severe Ice Storm ": 1.4,
}

st.session_state.setdefault("logged_in", False)
st.session_state.setdefault("user", None)
st.session_state.setdefault("region", "Houston (Harris County)")
st.session_state.setdefault("last_action", None)
st.session_state.setdefault("page", "Home")
st.session_state.setdefault("fault_plant_names", [])
st.session_state.setdefault("sim_load_multiplier", 1.0)

def check_login(username: str, password: str) -> bool:
    username = username.strip()
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    result = (
        session.table("PWC_DB.PUBLIC.APP_USERS")
        .filter(
            (col("USERNAME") == username) &
            (col("PASSWORD_HASH") == hashed_password)
        )
        .select("USERNAME", "ROLE")
        .to_pandas()
    )
    if not result.empty:
        st.session_state.user_role = result.iloc[0]["ROLE"]
        return True
    return False

def render_login():
    left, mid, right = st.columns([2, 1.2, 2])
    with mid:
        st.markdown('<div class="nses-card">', unsafe_allow_html=True)
        st.markdown("### Sign in")
        st.caption("Access the NSES analytics dashboard.")
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="")
            password = st.text_input("Password", type="password", placeholder="")
            submitted = st.form_submit_button("Log in")
        if submitted:
            if check_login(username, password):
                st.session_state.logged_in = True
                st.session_state.user = username.strip()
                st.rerun()
            else:
                st.error("Invalid username or password.")
        st.markdown("</div>", unsafe_allow_html=True)

def render_reports_page():
    st.markdown("""
    <div style="background:linear-gradient(135deg,#1e3a5f,#2a1a4e);border-radius:16px;
    padding:1.5rem 2rem;margin-bottom:1.5rem;border:1px solid #334;">
        <div style="font-size:1.6rem;font-weight:800;color:#fff;letter-spacing:0.05em;">
            Generation Report</div>
        <div style="font-size:0.85rem;color:#aaa;margin-top:0.3rem;">
            Houston Energy Grid — Historical Analysis & Forecasting</div>
    </div>
    """, unsafe_allow_html=True)

    hist = session.sql("""
        SELECT "DATE", TOTAL_GENERATION_MWH
        FROM PWC_DB.PUBLIC.HOUSTON_BASELINE
        WHERE TOTAL_GENERATION_MWH IS NOT NULL
    """).to_pandas()
    hist["DATE"] = pd.to_datetime(hist["DATE"])

    forecast = session.sql("""
        SELECT "DATE", PRED_MEAN AS PREDICTED_MWH
        FROM PWC_DB.PUBLIC.HOUSTON_FUTURE_FORECAST
        ORDER BY "DATE"
    """).to_pandas()

    pred = session.sql("""
        SELECT "DATE",
               "TOTAL_GENERATION_MWH",
               "PREDICTION":"output_feature_0"::FLOAT AS PREDICTED_MWH
        FROM PWC_DB.PUBLIC.HOUSTON_PREDICTIONS
    """).to_pandas()

    st.markdown("""
    <div style="background:#1a2a3a;border-radius:12px;padding:0.6rem 1.2rem;
    margin-bottom:0.8rem;border-left:4px solid #4a9eff;">
        <span style="font-weight:700;font-size:1rem;color:#4a9eff;">Summary Statistics</span>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("Avg Generation (MWh)", f"{hist['TOTAL_GENERATION_MWH'].mean():,.0f}")
    c2.metric("Peak Generation (MWh)", f"{hist['TOTAL_GENERATION_MWH'].max():,.0f}")
    c3.metric("Min Generation (MWh)", f"{hist['TOTAL_GENERATION_MWH'].min():,.0f}")

    c4, c5, c6 = st.columns(3)
    yearly = hist.set_index("DATE").resample("YE")["TOTAL_GENERATION_MWH"].sum()
    if len(yearly) >= 2:
        yoy = ((yearly.iloc[-1] - yearly.iloc[-2]) / yearly.iloc[-2]) * 100
        c4.metric("YoY Growth", f"{yoy:+.1f}%")
    peak_month = hist.groupby(hist["DATE"].dt.month)["TOTAL_GENERATION_MWH"].mean().idxmax()
    month_names = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    c5.metric("Peak Month (Avg)", month_names[peak_month - 1])
    c6.metric("Data Points", f"{len(hist):,}")

    st.write("")

    st.markdown("""
    <div style="background:#1a2a3a;border-radius:12px;padding:0.6rem 1.2rem;
    margin-bottom:0.8rem;border-left:4px solid #4a9eff;">
        <span style="font-weight:700;font-size:1rem;color:#4a9eff;">Historical vs Predicted</span>
    </div>
    """, unsafe_allow_html=True)

    chart_df = pred[["DATE", "TOTAL_GENERATION_MWH", "PREDICTED_MWH"]].copy()
    chart_df["DATE"] = pd.to_datetime(chart_df["DATE"])
    chart_df = chart_df.sort_values("DATE").set_index("DATE")
    chart_df.columns = ["Actual (MWh)", "Predicted (MWh)"]
    st.line_chart(chart_df)

    df_future_chart = forecast.copy()
    df_future_chart["DATE"] = pd.to_datetime(df_future_chart["DATE"])
    df_future_chart = df_future_chart.sort_values("DATE").set_index("DATE")
    df_future_chart.columns = ["Forecast (MWh)"]
    st.caption("24-Month Future Forecast")
    st.line_chart(df_future_chart)

    st.write("")

    st.markdown("""
    <div style="background:#1a2a3a;border-radius:12px;padding:0.6rem 1.2rem;
    margin-bottom:0.8rem;border-left:4px solid #4a9eff;">
        <span style="font-weight:700;font-size:1rem;color:#4a9eff;">Generation by Power Plant</span>
    </div>
    """, unsafe_allow_html=True)

    plant_df = session.sql("""
        SELECT TO_DATE("DATE", 'DY MON DD YYYY') AS DT, 'Deer Park' AS PLANT, "Net Generation (MWh)" AS MWH FROM PWC_DB.PUBLIC.A_POWER_PLANTS WHERE "Net Generation (MWh)" IS NOT NULL
        UNION ALL SELECT TO_DATE("DATE", 'DY MON DD YYYY'), 'Channelview', "Net Generation (MWh)" FROM PWC_DB.PUBLIC.B_POWER_PLANTS WHERE "Net Generation (MWh)" IS NOT NULL
        UNION ALL SELECT TO_DATE("DATE", 'DY MON DD YYYY'), 'Pasadena', "Net Generation (MWh)" FROM PWC_DB.PUBLIC.C_POWER_PLANTS WHERE "Net Generation (MWh)" IS NOT NULL
        UNION ALL SELECT TO_DATE("DATE", 'DY MON DD YYYY'), 'Channel Energy', "Net Generation (MWh)" FROM PWC_DB.PUBLIC.D_POWER_PLANT WHERE "Net Generation (MWh)" IS NOT NULL
        UNION ALL SELECT TO_DATE("DATE", 'DY MON DD YYYY'), 'Odyssey Energy', "Net Generation (MWh)" FROM PWC_DB.PUBLIC.E_POWER_PLANT WHERE "Net Generation (MWh)" IS NOT NULL
        UNION ALL SELECT TO_DATE("DATE", 'DY MON DD YYYY'), 'ExxonMobil', "Net Generation (MWh)" FROM PWC_DB.PUBLIC.F_POWER_PLANT WHERE "Net Generation (MWh)" IS NOT NULL
        ORDER BY DT
    """).to_pandas()
    plant_pivot = plant_df.pivot_table(index="DT", columns="PLANT", values="MWH")
    st.line_chart(plant_pivot)

    st.write("")

    st.markdown("""
    <div style="background:#1a2a3a;border-radius:12px;padding:0.6rem 1.2rem;
    margin-bottom:0.8rem;border-left:4px solid #4a9eff;">
        <span style="font-weight:700;font-size:1rem;color:#4a9eff;">Model Performance</span>
    </div>
    """, unsafe_allow_html=True)

    mae = (pred["TOTAL_GENERATION_MWH"] - pred["PREDICTED_MWH"]).abs().mean()
    ss_res = ((pred["TOTAL_GENERATION_MWH"] - pred["PREDICTED_MWH"]) ** 2).sum()
    ss_tot = ((pred["TOTAL_GENERATION_MWH"] - pred["TOTAL_GENERATION_MWH"].mean()) ** 2).sum()
    r2 = 1 - (ss_res / ss_tot)
    m1, m2, m3 = st.columns(3)
    m1.metric("MAE", f"{mae:,.0f} MWh")
    m2.metric("R² Score", f"{r2:.4f}")
    m3.metric("Forecast Horizon", f"{len(forecast)} months")

    e1, e2, e3 = st.columns(3)
    with e1:
        hist_csv = hist.to_csv(index=False)
        st.download_button("Download Historical Data", hist_csv, "houston_historical.csv", "text/csv")
    with e2:
        forecast_csv = forecast.to_csv(index=False)
        st.download_button("Download Forecast Data", forecast_csv, "houston_forecast.csv", "text/csv")
    with e3:
        combined = pd.concat([
            hist.rename(columns={"TOTAL_GENERATION_MWH": "ACTUAL_MWH"}).assign(PREDICTED_MWH=np.nan),
            forecast.assign(ACTUAL_MWH=np.nan)
        ]).sort_values("DATE")
        full_csv = combined.to_csv(index=False)
        st.download_button("Download Full Report", full_csv, "houston_full_report.csv", "text/csv")

def render_main_page():
    center, right = st.columns([3, 1], gap="large")

    with center:
        st.markdown(
            '<div class="nses-card"><div class="section-label">Grid View</div></div>',
            unsafe_allow_html=True
        )

        r = REGIONS.get(st.session_state.region, REGIONS["Houston (Harris County)"])

        gen_df = session.sql("""
            SELECT * FROM (
                SELECT 'Deer Park' AS PLANT, "Net Generation (MWh)" AS MWH
                FROM PWC_DB.PUBLIC.A_POWER_PLANTS
                WHERE "Net Generation (MWh)" IS NOT NULL
                ORDER BY TO_DATE("DATE", 'DY MON DD YYYY') DESC LIMIT 1
            )
            UNION ALL SELECT * FROM (
                SELECT 'Channelview' AS PLANT, "Net Generation (MWh)" AS MWH
                FROM PWC_DB.PUBLIC.B_POWER_PLANTS
                WHERE "Net Generation (MWh)" IS NOT NULL
                ORDER BY TO_DATE("DATE", 'DY MON DD YYYY') DESC LIMIT 1
            )
            UNION ALL SELECT * FROM (
                SELECT 'Pasadena' AS PLANT, "Net Generation (MWh)" AS MWH
                FROM PWC_DB.PUBLIC.C_POWER_PLANTS
                WHERE "Net Generation (MWh)" IS NOT NULL
                ORDER BY TO_DATE("DATE", 'DY MON DD YYYY') DESC LIMIT 1
            )
            UNION ALL SELECT * FROM (
                SELECT 'Channel Energy' AS PLANT, "Net Generation (MWh)" AS MWH
                FROM PWC_DB.PUBLIC.D_POWER_PLANT
                WHERE "Net Generation (MWh)" IS NOT NULL
                ORDER BY TO_DATE("DATE", 'DY MON DD YYYY') DESC LIMIT 1
            )
            UNION ALL SELECT * FROM (
                SELECT 'Odyssey Energy' AS PLANT, "Net Generation (MWh)" AS MWH
                FROM PWC_DB.PUBLIC.E_POWER_PLANT
                WHERE "Net Generation (MWh)" IS NOT NULL
                ORDER BY TO_DATE("DATE", 'DY MON DD YYYY') DESC LIMIT 1
            )
            UNION ALL SELECT * FROM (
                SELECT 'ExxonMobil' AS PLANT, "Net Generation (MWh)" AS MWH
                FROM PWC_DB.PUBLIC.F_POWER_PLANT
                WHERE "Net Generation (MWh)" IS NOT NULL
                ORDER BY TO_DATE("DATE", 'DY MON DD YYYY') DESC LIMIT 1
            )
        """).to_pandas()

        map_data = POWER_PLANTS.merge(gen_df, left_on="name", right_on="PLANT", how="left")
        map_data["MWH"] = map_data["MWH"].fillna(0).astype(float)

        fault_names = st.session_state.fault_plant_names or []
        if fault_names:
            map_data["color"] = map_data["name"].apply(
                lambda n: [128, 128, 128, 180] if n in fault_names else [220, 70, 40, 210]
            )
            map_data["glow_color"] = map_data["name"].apply(
                lambda n: [128, 128, 128, 30] if n in fault_names else [255, 120, 60, 55]
            )
            map_data["status"] = map_data["name"].apply(
                lambda n: "OFFLINE" if n in fault_names else "Online"
            )
        else:
            map_data["color"] = [[220, 70, 40, 210]] * len(map_data)
            map_data["glow_color"] = [[255, 120, 60, 55]] * len(map_data)
            map_data["status"] = "Online"

        plant_glow_layer = pdk.Layer(
            "ScatterplotLayer",
            data=map_data,
            get_position=["lng", "lat"],
            get_radius=3200,
            get_fill_color="glow_color",
            pickable=False,
        )

        plant_layer = pdk.Layer(
            "ScatterplotLayer",
            data=map_data,
            get_position=["lng", "lat"],
            get_radius=1600,
            get_fill_color="color",
            get_line_color=[255, 255, 255],
            line_width_min_pixels=1,
            stroked=True,
            pickable=True,
        )

        substation_layer = pdk.Layer(
            "ScatterplotLayer",
            data=SUBSTATIONS,
            get_position=["lng", "lat"],
            get_radius=1200,
            get_fill_color=[255, 215, 0, 210],
            get_line_color=[255, 255, 255],
            line_width_min_pixels=1,
            stroked=True,
            pickable=True,
        )

        base_line_layer = pdk.Layer(
            "LineLayer",
            data=TRANSMISSION_LINES,
            id="base-lines",
            get_source_position=["src_lng", "src_lat"],
            get_target_position=["dst_lng", "dst_lat"],
            get_color=[20, 20, 20, 200],
            get_width=6,
            pickable=False,
        )

        if fault_names:
            fault_coords = [PLANT_COORDS[n] for n in fault_names if n in PLANT_COORDS]
            fault_lats = [c[0] for c in fault_coords]
            fault_lngs = [c[1] for c in fault_coords]

            def is_connected_to_fault(row):
                return (
                    (row["dst_lat"] in fault_lats and row["dst_lng"] in fault_lngs) or
                    (row["src_lat"] in fault_lats and row["src_lng"] in fault_lngs)
                )

            mask = TRANSMISSION_LINES.apply(is_connected_to_fault, axis=1)
            disabled_lines = TRANSMISSION_LINES[mask]
            active_345 = TRANSMISSION_LINES[(TRANSMISSION_LINES["voltage"] == "345kV") & ~mask]
            active_138 = TRANSMISSION_LINES[(TRANSMISSION_LINES["voltage"] == "138kV") & ~mask]

            feeder_mask = FEEDERS.apply(
                lambda row: (row["src_lat"] in fault_lats and row["src_lng"] in fault_lngs), axis=1
            )
            active_feeders = FEEDERS[~feeder_mask]
            disabled_feeders = FEEDERS[feeder_mask]
        else:
            active_345 = TRANSMISSION_LINES[TRANSMISSION_LINES["voltage"] == "345kV"]
            active_138 = TRANSMISSION_LINES[TRANSMISSION_LINES["voltage"] == "138kV"]
            active_feeders = FEEDERS
            disabled_lines = pd.DataFrame()
            disabled_feeders = pd.DataFrame()

        trans_345_layer = pdk.Layer(
            "LineLayer",
            data=active_345,
            id="345kv-lines",
            get_source_position=["src_lng", "src_lat"],
            get_target_position=["dst_lng", "dst_lat"],
            get_color=[0, 200, 255, 230],
            get_width=3,
            pickable=True,
        )

        trans_138_layer = pdk.Layer(
            "LineLayer",
            data=active_138,
            id="138kv-lines",
            get_source_position=["src_lng", "src_lat"],
            get_target_position=["dst_lng", "dst_lat"],
            get_color=[255, 140, 60, 220],
            get_width=2,
            pickable=True,
        )

        feeder_layer = pdk.Layer(
            "LineLayer",
            data=active_feeders,
            id="feeder-lines",
            get_source_position=["src_lng", "src_lat"],
            get_target_position=["dst_lng", "dst_lat"],
            get_color=[140, 140, 140, 100],
            get_width=1,
            pickable=False,
        )

        layers = [
            feeder_layer, base_line_layer, trans_138_layer, trans_345_layer,
            plant_glow_layer, plant_layer, substation_layer,
        ]

        if len(disabled_lines) > 0:
            disabled_line_layer = pdk.Layer(
                "LineLayer", data=disabled_lines, id="disabled-lines",
                get_source_position=["src_lng", "src_lat"],
                get_target_position=["dst_lng", "dst_lat"],
                get_color=[255, 60, 60, 120], get_width=2, pickable=False,
            )
            layers.insert(2, disabled_line_layer)

        if len(disabled_feeders) > 0:
            disabled_feeder_layer = pdk.Layer(
                "LineLayer", data=disabled_feeders, id="disabled-feeders",
                get_source_position=["src_lng", "src_lat"],
                get_target_position=["dst_lng", "dst_lat"],
                get_color=[255, 60, 60, 60], get_width=1, pickable=False,
            )
            layers.insert(1, disabled_feeder_layer)

        sub_text_layer = pdk.Layer(
            "TextLayer", data=SUBSTATIONS,
            get_position=["lng", "lat"], get_text="name", get_size=12,
            get_color=[255, 235, 140, 220], get_pixel_offset=[0, -16],
            get_alignment_baseline="bottom",
        )

        plant_text_layer = pdk.Layer(
            "TextLayer", data=map_data,
            get_position=["lng", "lat"], get_text="name", get_size=11,
            get_color=[255, 180, 160, 200], get_pixel_offset=[0, 14],
            get_alignment_baseline="top",
        )

        layers.extend([sub_text_layer, plant_text_layer])

        view_state = pdk.ViewState(
            latitude=r["lat"], longitude=r["lng"], zoom=r["zoom"], pitch=0, bearing=0,
        )

        deck = pdk.Deck(
            layers=layers,
            initial_view_state=view_state,
            map_style="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
            tooltip={
                "html": "<b>{name}</b><br/>Status: {status}<br/>Voltage: {voltage}<br/>Load: {load}<br/>Generation: {MWH} MWh",
                "style": {"backgroundColor": "#1a1a2e", "color": "#e0e0e0", "fontSize": "13px", "borderRadius": "8px", "padding": "8px"},
            },
        )

        st.pydeck_chart(deck, height=550)
        st.write("")
        st.markdown(
            '<div class="nses-card"><div class="section-label">Simulation Controls</div></div>',
            unsafe_allow_html=True
        )

        region = st.selectbox("Select Region", list(REGIONS.keys()), key="main_region_select")
        st.session_state.region = region

        colA, colB, colC = st.columns(3)

        with colA:
            if st.button("Start Simulation", use_container_width=True, key="start_sim_btn"):
                st.session_state.last_action = f"Started simulation for {region}"

        with colB:
            if st.button("Stop", use_container_width=True, key="stop_sim_btn"):
                st.session_state.last_action = "Simulation stopped"
                st.session_state.fault_plant_names = []

        with colC:
            if st.button("Reset Scenario", use_container_width=True, key="reset_scenario_btn"):
                st.session_state.last_action = "Scenario reset"
                st.session_state.fault_plant_names = []
                st.rerun()

        st.caption(f"Selected region: {region}")

        if st.session_state.last_action and st.session_state.last_action.startswith("Started simulation"):
            fault_plants = st.multiselect(
                "Take Plant(s) Offline",
                list(PLANT_CAPACITY.keys()),
                default=[],
                key="fault_plant_select"
            )

            scenario = st.selectbox(
                "Disaster Scenario",
                list(SCENARIO_MULTIPLIERS.keys()),
                key="scenario_select"
            )
            load_multiplier = SCENARIO_MULTIPLIERS[scenario]

            if fault_plants and st.button("Run Fault Simulation", key="run_fault_btn"):
                st.session_state.fault_plant_names = fault_plants
                st.session_state.sim_load_multiplier = load_multiplier
                st.session_state.sim_scenario_label = scenario
                st.rerun()

        if st.session_state.fault_plant_names:
            fault_list = st.session_state.fault_plant_names
            load_multiplier = st.session_state.sim_load_multiplier
            scenario_label = st.session_state.get("sim_scenario_label", "")
            total_fault_cap = sum(PLANT_CAPACITY[p] for p in fault_list)
            remaining = {k: v for k, v in PLANT_CAPACITY.items() if k not in fault_list}
            total_remaining = sum(remaining.values())

            redistributed = {}
            load_pct = {}
            for name, cap in remaining.items():
                share = cap / total_remaining
                new_load = (cap + total_fault_cap * share) * load_multiplier
                redistributed[name] = new_load
                load_pct[name] = new_load / cap * 100

            r_names = list(remaining.keys())
            r_pcts = [load_pct[n] for n in r_names]
            overloaded = sum(1 for p in r_pcts if p > 100)
            warning_count = sum(1 for p in r_pcts if 85 < p <= 100)

            st.markdown(f"""
            <div style="background:linear-gradient(135deg,#1e3a5f,#2a1a4e);border-radius:12px;
            padding:1rem 1.2rem;margin:1rem 0 0.8rem 0;border:1px solid #334;">
                <div style="font-weight:800;font-size:1.1rem;color:#ffffff;letter-spacing:0.03em;">
                    Fault Simulation Results</div>
                <div style="font-size:0.8rem;color:#888;margin-top:0.3rem;">
                    {', '.join(fault_list)} offline — {scenario_label}</div>
            </div>
            """, unsafe_allow_html=True)

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Plants Offline", f"{len(fault_list)}")
            m2.metric("Capacity Lost", f"{total_fault_cap:,} MW")
            m3.metric("Overloaded", f"{overloaded}")
            m4.metric("At Warning", f"{warning_count}")

            st.markdown("""
            <div style="background:#1a2a3a;border-radius:10px;padding:0.4rem 1rem;
            margin:0.8rem 0 0.5rem 0;border-left:4px solid #F39C12;">
                <span style="font-weight:700;font-size:0.9rem;color:#F39C12;">Load Redistribution</span>
            </div>
            """, unsafe_allow_html=True)

            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 4))
            fig.patch.set_facecolor("#1a1a1a")
            for ax in (ax1, ax2):
                ax.set_facecolor("#1a1a1a")
                ax.tick_params(colors="#e0e0e0")
                ax.xaxis.label.set_color("#e0e0e0")
                ax.yaxis.label.set_color("#e0e0e0")
                ax.title.set_color("#e0e0e0")
                for spine in ax.spines.values():
                    spine.set_color("#333")

            names_all = list(PLANT_CAPACITY.keys())
            vals_all = [PLANT_CAPACITY[n] for n in names_all]
            bar_colors_before = ["#888888" if n in fault_list else "#4A90D9" for n in names_all]
            ax1.barh(names_all, vals_all, color=bar_colors_before, edgecolor="#1a1a1a")
            ax1.set_xlabel("Load (MW)")
            ax1.set_title("Before Fault")

            r_vals = [redistributed[n] for n in r_names]
            colors = ["#E74C3C" if p > 100 else "#F39C12" if p > 85 else "#2ECC71" for p in r_pcts]
            bars = ax2.barh(r_names, r_vals, color=colors, edgecolor="#1a1a1a")
            for bar, pct in zip(bars, r_pcts):
                ax2.text(bar.get_width() + 10, bar.get_y() + bar.get_height()/2,
                         f"{pct:.0f}%", va="center", fontsize=9, color="#e0e0e0", fontweight="bold")
            ax2.set_xlabel("Load (MW)")
            ax2.set_title(f"After Fault — {len(fault_list)} Plant(s) Offline")

            legend_patches = [
                mpatches.Patch(color="#2ECC71", label="Normal (<85%)"),
                mpatches.Patch(color="#F39C12", label="Warning (85-100%)"),
                mpatches.Patch(color="#E74C3C", label="Overloaded (>100%)"),
                mpatches.Patch(color="#888888", label="Offline"),
            ]
            ax2.legend(handles=legend_patches, loc="lower right", fontsize=7,
                       facecolor="#1a1a1a", edgecolor="#333", labelcolor="#e0e0e0")
            plt.tight_layout()
            st.pyplot(fig)

            st.markdown("""
            <div style="background:#1a2a3a;border-radius:10px;padding:0.4rem 1rem;
            margin:0.8rem 0 0.5rem 0;border-left:4px solid #4A90D9;">
                <span style="font-weight:700;font-size:0.9rem;color:#4A90D9;">Historical Disruption Timeline</span>
            </div>
            """, unsafe_allow_html=True)

            sim_df = session.sql("""
                SELECT DATE, BASELINE_MWH, SIMULATED_MWH, DISRUPTION_PCT, INCIDENT_TYPE
                FROM PWC_DB.PUBLIC.HOUSTON_ANOMALY_SIMULATION_RESULTS
                ORDER BY DATE
            """).to_pandas()
            sim_df["DATE"] = pd.to_datetime(sim_df["DATE"])

            fig2, ax3 = plt.subplots(figsize=(14, 3.5))
            fig2.patch.set_facecolor("#1a1a1a")
            ax3.set_facecolor("#1a1a1a")
            ax3.tick_params(colors="#e0e0e0")
            ax3.xaxis.label.set_color("#e0e0e0")
            ax3.yaxis.label.set_color("#e0e0e0")
            ax3.title.set_color("#e0e0e0")
            for spine in ax3.spines.values():
                spine.set_color("#333")

            ax3.plot(sim_df["DATE"], sim_df["BASELINE_MWH"], color="#4A90D9", linewidth=1, label="Baseline", alpha=0.8)
            ax3.plot(sim_df["DATE"], sim_df["SIMULATED_MWH"], color="#E74C3C", linewidth=1.5, label="Simulated", alpha=0.9)

            anomaly_rows = sim_df[sim_df["DISRUPTION_PCT"] > 0].drop_duplicates(subset=["DATE"])
            for _, row in anomaly_rows.iterrows():
                ax3.axvspan(row["DATE"] - pd.Timedelta(days=15), row["DATE"] + pd.Timedelta(days=15),
                            alpha=0.15, color="red")

            ax3.set_title("Baseline vs Simulated Generation", color="#e0e0e0")
            ax3.set_ylabel("MWh", color="#e0e0e0")
            ax3.legend(facecolor="#1a1a1a", edgecolor="#333", labelcolor="#e0e0e0")
            ax3.grid(True, alpha=0.15, color="#333")
            plt.tight_layout()
            st.pyplot(fig2)

            st.markdown("""
            <div style="background:#1a2a3a;border-radius:10px;padding:0.4rem 1rem;
            margin:0.8rem 0 0.5rem 0;border-left:4px solid #9B59B6;">
                <span style="font-weight:700;font-size:0.9rem;color:#9B59B6;">Impact by Disaster Type</span>
            </div>
            """, unsafe_allow_html=True)

            impact = sim_df[sim_df["DISRUPTION_PCT"] > 0].groupby("INCIDENT_TYPE").agg(
                AVG_DISRUPTION=("DISRUPTION_PCT", "mean"),
                TOTAL_DEVIATION=("BASELINE_MWH", lambda x: (sim_df.loc[x.index, "BASELINE_MWH"] - sim_df.loc[x.index, "SIMULATED_MWH"]).sum()),
                EVENT_COUNT=("DATE", "nunique")
            ).sort_values("TOTAL_DEVIATION")

            fig3, (ax4, ax5) = plt.subplots(1, 2, figsize=(14, 3.5))
            fig3.patch.set_facecolor("#1a1a1a")
            for ax in (ax4, ax5):
                ax.set_facecolor("#1a1a1a")
                ax.tick_params(colors="#e0e0e0")
                ax.xaxis.label.set_color("#e0e0e0")
                ax.title.set_color("#e0e0e0")
                for spine in ax.spines.values():
                    spine.set_color("#333")

            colors_map = {"Hurricane": "#E74C3C", "Severe Storm": "#F39C12", "Severe Ice Storm": "#3498DB",
                          "Flood": "#1ABC9C", "Fire": "#E67E22", "Biological": "#9B59B6", "Other": "#95A5A6"}
            bar_colors = [colors_map.get(t, "#95A5A6") for t in impact.index]

            ax4.barh(impact.index, abs(impact["TOTAL_DEVIATION"]), color=bar_colors, edgecolor="#1a1a1a")
            ax4.set_xlabel("Total MWh Lost", color="#e0e0e0")
            ax4.set_title("Cumulative Generation Loss")

            ax5.barh(impact.index, impact["AVG_DISRUPTION"] * 100, color=bar_colors, edgecolor="#1a1a1a")
            for i, (idx, row) in enumerate(impact.iterrows()):
                ax5.text(row["AVG_DISRUPTION"] * 100 + 0.3, i,
                         f"({int(row['EVENT_COUNT'])} events)", va="center", fontsize=8, color="#e0e0e0")
            ax5.set_xlabel("Avg Disruption %", color="#e0e0e0")
            ax5.set_title("Disruption Severity by Type")
            plt.tight_layout()
            st.pyplot(fig3)

    with right:
        st.markdown(
            '<div class="nses-card"><div class="section-label">Analytics Output</div></div>',
            unsafe_allow_html=True
        )

        st.write("")

        if st.button("Baseline Analysis", use_container_width=True, key="baseline_btn"):
            baseline_df = get_houston_baseline(session)
            baseline_df["DATE"] = pd.to_datetime(baseline_df["DATE"])
            st.session_state.last_action = "Baseline Analysis triggered"
            st.subheader("Houston Baseline Information")
            st.line_chart(baseline_df.set_index("DATE")["TOTAL_GENERATION_MWH"])

        if st.button("Predictions", use_container_width=True, key="predictions_btn"):
            st.session_state.last_action = "predictions"
            df_hist = session.sql("""
                SELECT "DATE", TOTAL_GENERATION_MWH
                FROM PWC_DB.PUBLIC.HOUSTON_BASELINE
                WHERE TOTAL_GENERATION_MWH IS NOT NULL
                ORDER BY TO_DATE("DATE", 'DY MON DD YYYY')
            """).to_pandas()
            df_hist["DATE"] = pd.to_datetime(df_hist["DATE"])

            df_future = session.sql("""
                SELECT "DATE", PRED_MEAN AS PREDICTED_MWH
                FROM PWC_DB.PUBLIC.HOUSTON_FUTURE_FORECAST
                ORDER BY "DATE"
            """).to_pandas()

            df_hist["PREDICTED_MWH"] = np.nan
            df_future["TOTAL_GENERATION_MWH"] = np.nan

            combined = pd.concat([
                df_hist[["DATE", "TOTAL_GENERATION_MWH", "PREDICTED_MWH"]],
                df_future[["DATE", "TOTAL_GENERATION_MWH", "PREDICTED_MWH"]]
            ]).sort_values("DATE").set_index("DATE")

            st.caption("Historical Generation + Future Forecast (MWh)")
            st.line_chart(combined[["TOTAL_GENERATION_MWH", "PREDICTED_MWH"]])
            st.caption(f"{len(df_future)} future months forecasted")

        if st.button("Import Data", use_container_width=True, key="import_data_btn"):
            st.session_state.last_action = "Import Data"

        if st.session_state.last_action == "Import Data":
            plant_map = {
                "Deer Park (A)": "A_POWER_PLANTS",
                "Channelview (B)": "B_POWER_PLANTS",
                "Pasadena (C)": "C_POWER_PLANTS",
                "Channel Energy (D)": "D_POWER_PLANT",
                "Odyssey Energy (E)": "E_POWER_PLANT",
                "ExxonMobil (F)": "F_POWER_PLANT",
            }

            plant = st.selectbox("Select Power Plant", list(plant_map.keys()), key="import_plant_select")
            table_name = plant_map[plant]

            st.caption('CSV: **DATE** + **Net Generation (MWh)**')
            uploaded = st.file_uploader("Upload CSV", type=["csv"], key="plant_csv_upload")

            if uploaded:
                df = pd.read_csv(uploaded)
                st.dataframe(df.head(5))

                expected_cols = {"DATE", "Net Generation (MWh)"}
                if not expected_cols.issubset(set(df.columns)):
                    st.error(f"Need columns: {expected_cols}")
                else:
                    st.success(f"{len(df)} rows ready")

                    if st.button("Run Import & Re-Predict", key="run_import_repredict_btn"):
                        with st.spinner("1/4 Importing..."):
                            snow_df = session.create_dataframe(df)
                            snow_df.write.mode("append").save_as_table(f"PWC_DB.PUBLIC.{table_name}")
                        st.success(f"Inserted into {table_name}")

                        with st.spinner("2/4 Rebuilding features..."):
                            session.sql("""
                                CREATE OR REPLACE TABLE PWC_DB.PUBLIC.HOUSTON_BASELINE_FEATURES AS
                                SELECT
                                    TO_DATE("DATE", 'DY MON DD YYYY') AS DT,
                                    TOTAL_GENERATION_MWH AS TARGET_MWH,
                                    YEAR(TO_DATE("DATE", 'DY MON DD YYYY')) AS YEAR,
                                    MONTH(TO_DATE("DATE", 'DY MON DD YYYY')) AS MONTH,
                                    LAG(TOTAL_GENERATION_MWH, 1) OVER (ORDER BY TO_DATE("DATE", 'DY MON DD YYYY')) AS LAG_1,
                                    LAG(TOTAL_GENERATION_MWH, 2) OVER (ORDER BY TO_DATE("DATE", 'DY MON DD YYYY')) AS LAG_2,
                                    LAG(TOTAL_GENERATION_MWH, 12) OVER (ORDER BY TO_DATE("DATE", 'DY MON DD YYYY')) AS LAG_12
                                FROM PWC_DB.PUBLIC.HOUSTON_BASELINE
                            """).collect()
                        st.success("Features rebuilt")

                        with st.spinner("3/4 Re-predicting..."):
                            session.sql("""
                                CREATE OR REPLACE TABLE PWC_DB.PUBLIC.HOUSTON_PREDICTIONS AS
                                SELECT
                                    DT AS "DATE",
                                    TARGET_MWH AS TOTAL_GENERATION_MWH,
                                    PWC_DB.PUBLIC.HOUSTON_RF_MWH!PREDICT(YEAR, MONTH, 1):"output_feature_0"::FLOAT AS PRED_TOTAL_GENERATION_MWH,
                                    YEAR, MONTH, 1 AS DAY,
                                    PWC_DB.PUBLIC.HOUSTON_RF_MWH!PREDICT(YEAR, MONTH, 1) AS PREDICTION
                                FROM PWC_DB.PUBLIC.HOUSTON_BASELINE_FEATURES
                                WHERE LAG_12 IS NOT NULL
                            """).collect()
                        st.success("Predictions updated")

                        with st.spinner("4/4 Forecasting..."):
                            session.sql("""
                                CREATE OR REPLACE TABLE PWC_DB.PUBLIC.HOUSTON_FUTURE_FORECAST AS
                                SELECT
                                    d."DATE",
                                    PWC_DB.PUBLIC.HOUSTON_RF_MWH!PREDICT(d.YEAR, d.MONTH, d.DAY):"output_feature_0"::FLOAT AS PREDICTED_MWH
                                FROM PWC_DB.PUBLIC.HOUSTON_FUTURE_DATES d
                                ORDER BY d."DATE"
                            """).collect()
                        st.success("Forecast updated")

                        st.balloons()
                        st.success("Done! Check **Reports**.")

        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown("**Legend**")
        st.markdown("🔴 Power Plant")
        st.markdown("🟡 Substation")
        st.markdown("🟦 345kV Line")
        st.markdown("🟠 138kV Line")
        st.markdown("⚪ Feeder")

    st.markdown("<hr>", unsafe_allow_html=True)
    st.caption("Last Action")
    st.write(st.session_state.last_action)

def render_home():
    with open("SdPp.jpg", "rb") as f:
        b64 = base64.b64encode(f.read()).decode()

    baseline = session.sql("""
        SELECT COUNT(*) AS CNT,
               MAX(TOTAL_GENERATION_MWH) AS PEAK,
               AVG(TOTAL_GENERATION_MWH) AS AVG_GEN
        FROM PWC_DB.PUBLIC.HOUSTON_BASELINE
        WHERE TOTAL_GENERATION_MWH IS NOT NULL
    """).to_pandas().iloc[0]

    st.markdown(f"""
    <style>
        @keyframes gridPulse {{
            0%, 100% {{ opacity: 0.15; }}
            50% {{ opacity: 0.3; }}
        }}
        @keyframes fadeInUp {{
            from {{ opacity: 0; transform: translateY(20px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        @keyframes glowBorder {{
            0%, 100% {{ border-color: rgba(74,144,217,0.3); box-shadow: 0 0 15px rgba(74,144,217,0.1); }}
            50% {{ border-color: rgba(74,144,217,0.6); box-shadow: 0 0 25px rgba(74,144,217,0.2); }}
        }}
        @keyframes scanline {{
            0% {{ transform: translateY(-100%); }}
            100% {{ transform: translateY(100%); }}
        }}
        .hero-section {{
            background: linear-gradient(180deg,
                rgba(10,10,20,0.5) 0%,
                rgba(30,58,95,0.6) 40%,
                rgba(10,10,20,0.85) 100%),
                url('data:image/jpeg;base64,{b64}');
            background-size: cover;
            background-position: center 40%;
            border-radius: 16px;
            padding: 4rem 2.5rem 3rem;
            margin-bottom: 1.5rem;
            border: 1px solid rgba(74,144,217,0.3);
            position: relative;
            overflow: hidden;
            animation: glowBorder 4s ease-in-out infinite;
        }}
        .hero-section::before {{
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background: repeating-linear-gradient(
                0deg, transparent, transparent 40px,
                rgba(74,144,217,0.04) 40px, rgba(74,144,217,0.04) 41px
            ),
            repeating-linear-gradient(
                90deg, transparent, transparent 40px,
                rgba(74,144,217,0.04) 40px, rgba(74,144,217,0.04) 41px
            );
            animation: gridPulse 4s ease-in-out infinite;
        }}
        .hero-section::after {{
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0;
            height: 200%;
            background: linear-gradient(180deg,
                transparent 0%,
                rgba(74,144,217,0.03) 50%,
                transparent 100%);
            animation: scanline 8s linear infinite;
            pointer-events: none;
        }}
        .hero-badge {{
            display: inline-block;
            background: rgba(74,144,217,0.2);
            border: 1px solid rgba(74,144,217,0.4);
            border-radius: 20px;
            padding: 0.3rem 1rem;
            font-size: 0.75rem;
            color: #4A90D9;
            letter-spacing: 0.1em;
            font-weight: 600;
            margin-bottom: 1rem;
            position: relative;
        }}
        .hero-title {{
            font-size: 2.4rem;
            font-weight: 800;
            color: #fff;
            letter-spacing: 0.06em;
            position: relative;
            animation: fadeInUp 0.8s ease-out;
            text-shadow: 0 2px 12px rgba(0,0,0,0.6);
        }}
        .hero-subtitle {{
            font-size: 1.05rem;
            color: #ccc;
            margin-top: 0.5rem;
            position: relative;
            animation: fadeInUp 0.8s ease-out 0.2s both;
            text-shadow: 0 1px 6px rgba(0,0,0,0.5);
        }}
        .hero-stats {{
            display: flex;
            gap: 2rem;
            margin-top: 1.5rem;
            position: relative;
        }}
        .hero-stat {{
            animation: fadeInUp 0.8s ease-out 0.4s both;
        }}
        .hero-stat-value {{
            font-size: 1.4rem;
            font-weight: 800;
            color: #4A90D9;
            text-shadow: 0 0 10px rgba(74,144,217,0.3);
        }}
        .hero-stat-label {{
            font-size: 0.7rem;
            color: #999;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }}
        .feature-card {{
            background: #222;
            border: 1px solid #333;
            border-radius: 12px;
            padding: 1.2rem;
            min-height: 160px;
            transition: transform 0.2s ease, border-color 0.2s ease;
        }}
        .feature-card:hover {{
            transform: translateY(-4px);
            border-color: #555;
        }}
    </style>

    <div class="hero-section">
        <div class="hero-badge">HOUSTON ENERGY GRID</div>
        <div class="hero-title">Welcome to NSES</div>
        <div class="hero-subtitle">Power Grid Monitoring, Simulation & Predictive Analytics Platform</div>
        <div class="hero-stats">
            <div class="hero-stat">
                <div class="hero-stat-value">6</div>
                <div class="hero-stat-label">Power Plants</div>
            </div>
            <div class="hero-stat">
                <div class="hero-stat-value">5</div>
                <div class="hero-stat-label">Substations</div>
            </div>
            <div class="hero-stat">
                <div class="hero-stat-value">{baseline['AVG_GEN']:,.0f}</div>
                <div class="hero-stat-label">Avg MWh</div>
            </div>
            <div class="hero-stat">
                <div class="hero-stat-value">{baseline['PEAK']:,.0f}</div>
                <div class="hero-stat-label">Peak MWh</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
        <div class="feature-card" style="border-top:3px solid #4A90D9;">
            <div style="font-size:1.5rem;margin-bottom:0.5rem;">🗺️</div>
            <div style="font-weight:700;color:#4A90D9;">Dashboard</div>
            <div style="font-size:0.85rem;color:#aaa;margin-top:0.4rem;">
            Real-time grid visualization, plant status, and fault simulation.</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div class="feature-card" style="border-top:3px solid #2ECC71;">
            <div style="font-size:1.5rem;margin-bottom:0.5rem;">📈</div>
            <div style="font-weight:700;color:#2ECC71;">Predictions</div>
            <div style="font-size:0.85rem;color:#aaa;margin-top:0.4rem;">
            ML-powered generation forecasting using historical baseline data.</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown("""
        <div class="feature-card" style="border-top:3px solid #E74C3C;">
            <div style="font-size:1.5rem;margin-bottom:0.5rem;">📊</div>
            <div style="font-weight:700;color:#E74C3C;">Reports</div>
            <div style="font-size:0.85rem;color:#aaa;margin-top:0.4rem;">
            Disruption timeline, anomaly simulation, and impact analysis.</div>
        </div>
        """, unsafe_allow_html=True)

    st.write("")

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Explore Grid", use_container_width=True, key="home_explore_btn"):
            st.session_state.page = "Dashboard"
            st.rerun()
    with col2:
        if st.button("View Reports", use_container_width=True, key="home_reports_btn"):
            st.session_state.page = "Reports"
            st.rerun()
    with col3:
        if st.button("Import Data", use_container_width=True, key="home_import_btn"):
            st.session_state.page = "Dashboard"
            st.session_state.last_action = "Import Data"
            st.rerun()

    st.divider()

  

    st.markdown("""
    <div style="background:#1a2a3a;border-radius:12px;padding:0.6rem 1.2rem;
    margin-bottom:0.8rem;border-left:4px solid #4a9eff;">
        <span style="font-weight:700;font-size:1rem;color:#4a9eff;">About NSES</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    NSES (National Smart Energy System) is a monitoring and analytics platform built for Houston's power grid infrastructure.
    The system tracks real-time generation across 6 power plants and 5 substations in Harris County,
    simulates fault scenarios and disaster impacts, and uses machine learning to forecast energy generation 24 months ahead.
    Designed to support grid operators and energy analysts in making data-driven decisions for grid resilience and reliability.
    """)

    st.markdown("""
    <div style="text-align:center;padding:1rem 0 0.5rem;margin-top:0.5rem;">
        <div style="font-size:0.75rem;color:#555;">
            Created by <span style="color:#4A90D9;font-weight:600;">PanthersWhoCode</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    

   

def render_dashboard():
    with st.sidebar:
        st.markdown("## Dashboard")
        st.caption("Navigation")
        pages = ["Home", "Dashboard", "Reports"]
        current = st.session_state.page if st.session_state.page in pages else "Home"
        st.session_state.page = st.radio(
          "Navigation",
          pages,
          index=pages.index(current),
          label_visibility="collapsed"
)

    col1, col2 = st.columns([8, 1])
    with col1:
        st.markdown(f"""
        <div class="nses-header">
            <div class="nses-title">USER INTERFACE</div>
            <div class="nses-subtitle">
                Signed in as <b>{st.session_state.user}</b> • {st.session_state.page}
            </div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        if st.button("Logout", key="logout_btn"):
           st.session_state.logged_in = False
           st.session_state.user = None
           st.rerun()

    if st.session_state.page == "Home":
        render_home()
    elif st.session_state.page == "Reports":
        render_reports_page()
    else:
        render_main_page()

if not st.session_state.logged_in:
    render_login()
else:
    render_dashboard() 