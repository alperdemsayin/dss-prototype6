"""User-friendly Streamlit dashboard for maritime routing optimization."""

import json
import math
from typing import Dict, List, Tuple

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from structures import Plant, Ship
from solver import quick_diagnostics, run_solver


st.set_page_config(
    page_title="Maritime Optimizer",
    page_icon="⚓",
    layout="wide",
    initial_sidebar_state="expanded",
)

APP_TITLE = "Maritime Inventory Routing Optimizer"
APP_SUBTITLE = (
    "Simple decision support dashboard for route planning, plant monitoring, and cost analysis"
)

FIXED_SCENARIO = {
    "depot": {"name": "Istanbul Depot", "lat": 41.0082, "lon": 28.9784},
    "plants": [
        {"name": "Antalya", "lat": 36.8969, "lon": 30.7133, "cap": 500.0, "init_stock": 400.0, "cons_rate": 5.0, "deadline": 120.0},
        {"name": "Iskenderun", "lat": 36.5872, "lon": 36.1735, "cap": 420.0, "init_stock": 330.0, "cons_rate": 4.0, "deadline": 110.0},
        {"name": "Mersin", "lat": 36.8000, "lon": 34.6333, "cap": 600.0, "init_stock": 520.0, "cons_rate": 6.0, "deadline": 120.0},
        {"name": "Canakkale", "lat": 40.1553, "lon": 26.4142, "cap": 350.0, "init_stock": 300.0, "cons_rate": 3.0, "deadline": 90.0},
        {"name": "Izmir", "lat": 38.4237, "lon": 27.1428, "cap": 480.0, "init_stock": 360.0, "cons_rate": 4.5, "deadline": 100.0},
        {"name": "Samsun", "lat": 41.2867, "lon": 36.3300, "cap": 390.0, "init_stock": 300.0, "cons_rate": 3.8, "deadline": 105.0},
    ],
}

DEFAULT_SHIP = {
    "empty_weight": 2000.0,
    "pump_rate": 50.0,
    "prep_time": 0.5,
    "charter_rate": 500.0,
    "fuel_cost": 0.02,
    "speed": 15.0,
}

MENU_ITEMS = ["Home", "Optimizer", "Plant Map"]
IGNORED_ROUTE_LABELS = {"Depot", "End of service", "Depot (return)"}


# -----------------------------------------------------------------------------
# Styling
# -----------------------------------------------------------------------------

def inject_custom_css() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background: #ffffff;
            color: #1a1a1a;
        }
        [data-testid="stAppViewContainer"] {
            background: #ffffff;
        }
        .block-container {
            padding-top: 1.25rem;
            padding-bottom: 2rem;
        }

        /* Sidebar */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #1e293b 0%, #334155 100%);
            border-right: 1px solid rgba(148, 163, 184, 0.3);
        }
        [data-testid="stSidebar"] * {
            color: #f1f5f9 !important;
        }

        /* Strong readable text in main area */
        [data-testid="stAppViewContainer"] h1,
        [data-testid="stAppViewContainer"] h2,
        [data-testid="stAppViewContainer"] h3,
        [data-testid="stAppViewContainer"] h4,
        [data-testid="stAppViewContainer"] h5,
        [data-testid="stAppViewContainer"] h6 {
            color: #0f172a !important;
        }
        [data-testid="stAppViewContainer"] p,
        [data-testid="stAppViewContainer"] li,
        [data-testid="stAppViewContainer"] label,
        [data-testid="stAppViewContainer"] span,
        [data-testid="stAppViewContainer"] div,
        [data-testid="stAppViewContainer"] small {
            color: #334155 !important;
        }
        .hero, .hero * {
            color: #ffffff !important;
        }
        [data-testid="stSidebar"] .stMetric label,
        [data-testid="stSidebar"] .stMetric div {
            color: #f1f5f9 !important;
        }
        
        /* Fix dataframe text */
        [data-testid="stDataFrame"] * {
            color: #1a1a1a !important;
        }
        
        /* Fix metric values */
        [data-testid="stMetricValue"] {
            color: #0f172a !important;
        }
        
        /* Fix metric labels */
        [data-testid="stMetricLabel"] {
            color: #475569 !important;
        }

        /* Panels */
        .hero {
            background: linear-gradient(135deg, #0f766e 0%, #2563eb 55%, #7c3aed 100%);
            padding: 1.4rem 1.5rem;
            border-radius: 24px;
            box-shadow: 0 18px 40px rgba(15, 23, 42, 0.12);
            margin-bottom: 1rem;
        }
        .hero h1 {
            margin: 0;
            font-size: 2rem;
            line-height: 1.15;
        }
        .hero p {
            margin: 0.45rem 0 0 0;
            opacity: 0.95;
            font-size: 1rem;
        }
        .quick-card {
            border-radius: 22px;
            padding: 1rem 1.1rem;
            color: white;
            min-height: 128px;
            box-shadow: 0 14px 28px rgba(15, 23, 42, 0.08);
            margin-bottom: 0.75rem;
        }
        .quick-card h4 {
            margin: 0;
            font-size: 0.9rem;
            font-weight: 600;
            opacity: 0.92;
            color: white !important;
        }
        .quick-card .value {
            margin-top: 0.45rem;
            font-size: 1.8rem;
            font-weight: 800;
            line-height: 1.1;
            color: white !important;
        }
        .quick-card .note {
            margin-top: 0.35rem;
            font-size: 0.9rem;
            opacity: 0.92;
            color: white !important;
        }
        .teal { background: linear-gradient(135deg, #0f766e, #14b8a6); }
        .blue { background: linear-gradient(135deg, #1d4ed8, #60a5fa); }
        .purple { background: linear-gradient(135deg, #6d28d9, #a78bfa); }
        .orange { background: linear-gradient(135deg, #ea580c, #fb923c); }

        .help-box {
            background: #ffffff;
            border-left: 6px solid #14b8a6;
            border-radius: 18px;
            padding: 1rem 1.1rem;
            box-shadow: 0 10px 25px rgba(15, 23, 42, 0.05);
            margin-bottom: 1rem;
        }
        .mini-title {
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: #64748b !important;
            font-weight: 700;
            margin-bottom: 0.25rem;
        }
        .nav-note {
            font-size: 0.85rem;
            color: #cbd5e1 !important;
            line-height: 1.45;
        }
        .route-band {
            background: #ffffff;
            border: 1px solid #dbe4ef;
            border-radius: 18px;
            padding: 0.8rem 0.95rem;
            margin: 0.5rem 0 1rem 0;
            box-shadow: 0 8px 20px rgba(15, 23, 42, 0.05);
        }
        .route-band-title {
            font-size: 0.78rem;
            font-weight: 800;
            color: #475569 !important;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-bottom: 0.45rem;
        }
        .route-flow {
            display: flex;
            gap: 0.45rem;
            align-items: center;
            flex-wrap: wrap;
        }
        .route-chip {
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            background: #dbeafe;
            border: 1px solid #93c5fd;
            color: #1e3a8a !important;
            padding: 0.4rem 0.65rem;
            border-radius: 12px;
            font-size: 0.9rem;
            font-weight: 600;
        }
        .route-arrow {
            color: #64748b !important;
            font-size: 1.05rem;
            font-weight: 500;
        }
        .route-chip.start {
            background: #ecfeff;
            border-color: #99f6e4;
            color: #115e59 !important;
        }
        .route-chip.end {
            background: #faf5ff;
            border-color: #e9d5ff;
            color: #6b21a8 !important;
        }
        .route-num {
            display: inline-flex;
            width: 1.55rem;
            height: 1.55rem;
            border-radius: 999px;
            align-items: center;
            justify-content: center;
            background: #2563eb;
            color: #ffffff !important;
            font-size: 0.82rem;
            font-weight: 800;
        }
        .route-arrow {
            color: #64748b !important;
            font-weight: 900;
        }

        /* Widgets */
        .stButton > button,
        .stDownloadButton > button {
            border-radius: 14px;
            border: 0;
            min-height: 2.9rem;
            font-weight: 700;
            box-shadow: 0 10px 20px rgba(37, 99, 235, 0.12);
        }
        div[data-baseweb="input"],
        div[data-baseweb="base-input"] {
            background: #ffffff !important;
            border-radius: 12px !important;
        }
        input {
            color: #0f172a !important;
            -webkit-text-fill-color: #0f172a !important;
        }
        [data-testid="stWidgetLabel"] *,
        [data-testid="stMarkdownContainer"] * {
            color: inherit !important;
        }
        .stToggle label,
        .stCheckbox label,
        .stRadio label,
        .stNumberInput label,
        .stSelectbox label,
        .stTextInput label {
            color: #0f172a !important;
            font-weight: 600;
        }
        [data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid #dbe4ef;
            padding: 0.8rem;
            border-radius: 18px;
            box-shadow: 0 8px 22px rgba(15, 23, 42, 0.04);
        }
        [data-testid="stMetricLabel"],
        [data-testid="stMetricValue"],
        [data-testid="stMetricDelta"] {
            color: #0f172a !important;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 0.4rem;
        }
        .stTabs [data-baseweb="tab"] {
            background: #ffffff;
            border-radius: 12px 12px 0 0;
            padding: 0.55rem 1rem;
            border: 1px solid #dbe4ef;
            border-bottom: 0;
        }
        .stTabs [aria-selected="true"] {
            background: #eff6ff !important;
            border-color: #93c5fd !important;
        }
        .stDataFrame, div[data-testid="stDataFrame"] {
            background: #ffffff;
            border-radius: 16px;
        }
        div[data-testid="stExpander"] {
            background: #ffffff;
            border-radius: 16px;
            border: 1px solid #dbe4ef;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


inject_custom_css()


# -----------------------------------------------------------------------------
# Utility functions
# -----------------------------------------------------------------------------

def haversine_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 3440.065
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return r * 2 * math.asin(math.sqrt(a))


@st.cache_data(show_spinner=False)
def compute_distance_matrix(depot_lat: float, depot_lon: float, plant_rows: List[Dict]):
    n = len(plant_rows)
    dist = [[0.0] * (n + 2) for _ in range(n + 2)]
    points = [(depot_lat, depot_lon)] + [(p["lat"], p["lon"]) for p in plant_rows]
    for i in range(n + 1):
        for j in range(n + 1):
            if i != j:
                dist[i][j] = round(
                    haversine_nm(points[i][0], points[i][1], points[j][0], points[j][1]),
                    1,
                )
    return dist


def make_active_plant_rows() -> List[Dict]:
    rows = []
    for i, item in enumerate(st.session_state.fixed_plants):
        if item["enabled"]:
            rows.append(
                {
                    "id": i + 1,
                    "name": item["name"],
                    "lat": float(item["lat"]),
                    "lon": float(item["lon"]),
                    "cap": float(item["cap"]),
                    "init_stock": float(item["init_stock"]),
                    "cons_rate": float(item["cons_rate"]),
                    "deadline": float(item["deadline"]),
                }
            )
    return rows


def make_plants(rows: List[Dict]) -> List[Plant]:
    return [
        Plant(
            name=row["name"],
            cap=row["cap"],
            init_stock=row["init_stock"],
            cons_rate=row["cons_rate"],
            deadline=row["deadline"],
        )
        for row in rows
    ]


def build_bundle(result: Dict) -> bytes:
    return json.dumps(
        {
            "status": result.get("status"),
            "voyage_time": result.get("voyage_time"),
            "total_cost": result.get("total_cost"),
            "route_labels": result.get("route_labels"),
            "deliveries": result.get("deliveries"),
            "arcs": result.get("arcs"),
        },
        indent=2,
    ).encode("utf-8")


def navigate(page_name: str) -> None:
    st.session_state.nav_page = page_name
    st.rerun()


def quick_card(title: str, value: str, note: str, tone: str = "blue") -> None:
    st.markdown(
        f"""
        <div class="quick-card {tone}">
            <h4>{title}</h4>
            <div class="value">{value}</div>
            <div class="note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def info_panel(title: str, body: str) -> None:
    st.markdown(
        f"""
        <div class="help-box">
            <div class="mini-title">{title}</div>
            <div>{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def status_badge(value: bool) -> str:
    return "Active" if value else "Off"


def build_map_view(active_rows: List[Dict], depot: Dict) -> Tuple[Dict, float]:
    points = [(depot["lat"], depot["lon"]) ] + [(row["lat"], row["lon"]) for row in active_rows]
    latitudes = [lat for lat, _ in points]
    longitudes = [lon for _, lon in points]
    center = {"lat": sum(latitudes) / len(latitudes), "lon": sum(longitudes) / len(longitudes)}

    lat_span = max(latitudes) - min(latitudes) if len(latitudes) > 1 else 0.0
    lon_span = max(longitudes) - min(longitudes) if len(longitudes) > 1 else 0.0
    span = max(lat_span, lon_span)
    if span <= 1:
        zoom = 7.2
    elif span <= 3:
        zoom = 6.0
    elif span <= 6:
        zoom = 5.2
    elif span <= 12:
        zoom = 4.6
    elif span <= 20:
        zoom = 3.8
    else:
        zoom = 2.6
    return center, zoom


def colorize_figure(fig: go.Figure) -> None:
    fig.update_layout(
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font=dict(color="#0f172a", size=13),
        title_font=dict(size=18, color="#0f172a"),
        legend=dict(bgcolor="rgba(255,255,255,0.88)", bordercolor="#dbe4ef", borderwidth=1),
        margin=dict(l=10, r=10, t=50, b=10),
    )
    fig.update_xaxes(showgrid=True, gridcolor="#e2e8f0", zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor="#e2e8f0", zeroline=False)


def render_route_highlight(result: Dict) -> None:
    route_steps = [label for label in result["route_labels"] if label not in IGNORED_ROUTE_LABELS]
    chips = ['<span class="route-chip start">Depot</span>']
    for idx, name in enumerate(route_steps, start=1):
        chips.append('<span class="route-arrow">→</span>')
        chips.append(
            f'<span class="route-chip"><span class="route-num">{idx}</span>{name}</span>'
        )

    end_label = "Return to Depot" if result["route_labels"] and result["route_labels"][-1] == "Depot (return)" else "End of service"
    chips.append('<span class="route-arrow">→</span>')
    chips.append(f'<span class="route-chip end">{end_label}</span>')

    st.markdown(
        f"""
        <div class="route-band">
            <div class="route-band-title">Route order</div>
            <div class="route-flow">{''.join(chips)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# -----------------------------------------------------------------------------
# Maps
# -----------------------------------------------------------------------------

def render_plant_map(active_rows: List[Dict], depot: Dict, plot_key: str) -> None:
    fig = go.Figure()
    center, zoom = build_map_view(active_rows, depot)

    fig.add_trace(
        go.Scattermapbox(
            lat=[depot["lat"]],
            lon=[depot["lon"]],
            mode="markers+text",
            marker=dict(size=28, color="#2563eb", opacity=0.95),
            text=["D"],
            textfont=dict(size=15, color="#ffffff", family="Arial Black"),
            textposition="middle center",
            name="Depot",
            customdata=[f"<b>{depot['name']}</b><br>Depot"],
            hovertemplate="%{customdata}<extra></extra>",
        )
    )

    if active_rows:
        hover_rows = []
        for row in active_rows:
            hover_rows.append(
                "<br>".join(
                    [
                        f"<b>{row['name']}</b>",
                        f"Plant #{row['id']}",
                        f"Capacity: {row['cap']:.0f} T",
                        f"Initial stock: {row['init_stock']:.0f} T",
                        f"Consumption: {row['cons_rate']:.1f} T/hr",
                        f"Deadline: {row['deadline']:.1f} hr",
                    ]
                )
            )

        fig.add_trace(
            go.Scattermapbox(
                lat=[row["lat"] for row in active_rows],
                lon=[row["lon"] for row in active_rows],
                mode="markers+text",
                marker=dict(size=34, color="#10b981", opacity=0.95),
                text=[str(row["id"]) for row in active_rows],
                textfont=dict(size=17, color="#ffffff", family="Arial Black"),
                textposition="middle center",
                name="Plants",
                customdata=hover_rows,
                hovertemplate="%{customdata}<extra></extra>",
            )
        )

    fig.update_layout(
        mapbox=dict(style="carto-positron", center=center, zoom=zoom),
        margin=dict(l=0, r=0, t=0, b=0),
        height=560,
        legend=dict(orientation="h", yanchor="bottom", y=0.01, xanchor="left", x=0.01),
    )
    st.plotly_chart(fig, use_container_width=True, key=plot_key)


def render_solution_map(result: Dict, active_rows: List[Dict], depot: Dict, rank: int) -> None:
    coord_map = {"Depot": (depot["lat"], depot["lon"]), depot["name"]: (depot["lat"], depot["lon"])}
    for row in active_rows:
        coord_map[row["name"]] = (row["lat"], row["lon"])

    visit_order: Dict[str, int] = {}
    order = 1
    for label in result["route_labels"]:
        if label in IGNORED_ROUTE_LABELS:
            continue
        if label in coord_map and label not in visit_order:
            visit_order[label] = order
            order += 1

    center, zoom = build_map_view(active_rows, depot)
    fig = go.Figure()

    route_coord_labels = [label for label in result["route_labels"] if label in coord_map]
    if len(route_coord_labels) >= 2:
        fig.add_trace(
            go.Scattermapbox(
                lat=[coord_map[label][0] for label in route_coord_labels],
                lon=[coord_map[label][1] for label in route_coord_labels],
                mode="lines",
                line=dict(width=4, color="#2563eb"),
                name="Route path",
                hoverinfo="skip",
            )
        )

    fig.add_trace(
        go.Scattermapbox(
            lat=[depot["lat"]],
            lon=[depot["lon"]],
            mode="markers+text",
            marker=dict(size=28, color="#2563eb", opacity=0.95),
            text=["D"],
            textfont=dict(size=15, color="#ffffff", family="Arial Black"),
            textposition="middle center",
            name="Depot",
            customdata=[f"<b>{depot['name']}</b><br>Starting depot"],
            hovertemplate="%{customdata}<extra></extra>",
        )
    )

    visited_lat, visited_lon, visited_text, visited_hover = [], [], [], []
    idle_lat, idle_lon, idle_text, idle_hover = [], [], [], []

    for row in active_rows:
        delivery = next((d for d in result["deliveries"] if d["Plant"] == row["name"]), None)
        hover_lines = [f"<b>{row['name']}</b>"]
        if row["name"] in visit_order:
            hover_lines.append(f"Visit order: {visit_order[row['name']]}")
        else:
            hover_lines.append("Not visited in this solution")
        if delivery:
            late = delivery.get("Lateness (hr)", 0)
            hover_lines.extend(
                [
                    f"Arrival: {delivery['Arrival (hr)']} hr",
                    f"Deadline: {delivery['Eff. Deadline (hr)']} hr",
                    f"Delivered: {delivery['Delivered (T)']} T",
                    f"Lateness: {late:.3f} hr",
                ]
            )
        hover_text = "<br>".join(hover_lines)

        if row["name"] in visit_order:
            visited_lat.append(row["lat"])
            visited_lon.append(row["lon"])
            visited_text.append(str(visit_order[row["name"]]))
            visited_hover.append(hover_text)
        else:
            idle_lat.append(row["lat"])
            idle_lon.append(row["lon"])
            idle_text.append(str(row["id"]))
            idle_hover.append(hover_text)

    if idle_lat:
        fig.add_trace(
            go.Scattermapbox(
                lat=idle_lat,
                lon=idle_lon,
                mode="markers+text",
                marker=dict(size=26, color="#94a3b8", opacity=0.9),
                text=idle_text,
                textfont=dict(size=14, color="#ffffff", family="Arial Black"),
                textposition="middle center",
                name="Unvisited",
                customdata=idle_hover,
                hovertemplate="%{customdata}<extra></extra>",
            )
        )

    if visited_lat:
        fig.add_trace(
            go.Scattermapbox(
                lat=visited_lat,
                lon=visited_lon,
                mode="markers+text",
                marker=dict(size=36, color="#10b981", opacity=0.95),
                text=visited_text,
                textfont=dict(size=18, color="#ffffff", family="Arial Black"),
                textposition="middle center",
                name="Visit order",
                customdata=visited_hover,
                hovertemplate="%{customdata}<extra></extra>",
            )
        )

    fig.update_layout(
        mapbox=dict(style="carto-positron", center=center, zoom=zoom),
        margin=dict(l=0, r=0, t=0, b=0),
        height=560,
        legend=dict(orientation="h", yanchor="bottom", y=0.01, xanchor="left", x=0.01),
    )
    st.plotly_chart(fig, use_container_width=True, key=f"solution_map_{rank}")


# -----------------------------------------------------------------------------
# Results
# -----------------------------------------------------------------------------

def render_results(multi: Dict, active_rows: List[Dict], depot: Dict) -> None:
    if isinstance(multi, str):
        st.error(multi)
        return

    if multi.get("kind") == "validation_error":
        st.error("Input validation failed.")
        for issue in multi["diagnostics"]["issues"]:
            st.write(f"- {issue}")
        return

    if multi.get("kind") == "infeasible":
        st.error(multi["message"])
        checks = pd.DataFrame(multi["diagnostics"].get("plant_checks", []))
        if not checks.empty:
            st.dataframe(checks, use_container_width=True, hide_index=True)
        return

    solutions = multi.get("solutions", [])
    st.caption(f"Found {multi.get('n_found', len(solutions))} solution(s) | Solve time: {multi['elapsed']} s")

    for warning in multi.get("diagnostics", {}).get("warnings", []):
        st.warning(warning)

    if len(solutions) == 1:
        solution = solutions[0]
        st.markdown(f"### Solution #1 — {solution['status']}")
        render_one_solution(solution, active_rows, depot, rank=1)
    else:
        tabs = st.tabs([f"Solution #{sol['solution_rank']} — {sol['status']}" for sol in solutions])
        for tab, solution in zip(tabs, solutions):
            with tab:
                render_one_solution(solution, active_rows, depot, rank=solution["solution_rank"])


def render_one_solution(result: Dict, active_rows: List[Dict], depot: Dict, rank: int = 1) -> None:
    on_time = sum(1 for delivery in result["deliveries"] if delivery["On Time"])
    total_plants = len(result["deliveries"])
    late_count = total_plants - on_time

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total cost", f"${result['total_cost']:,.0f}")
    c2.metric("Voyage time", f"{result['voyage_time']:.2f} hr")
    c3.metric("On-time deliveries", f"{on_time} / {total_plants}")
    if late_count > 0:
        c4.metric(
            "Lateness penalty",
            f"${result['lateness_penalty']:,.0f}",
            delta=f"{late_count} plant(s) late",
            delta_color="inverse",
        )
    else:
        c4.metric("Lateness penalty", "$0", delta="All on time", delta_color="normal")

    render_route_highlight(result)

    tab1, tab2, tab3, tab4 = st.tabs(["Map", "Deliveries", "Costs", "Technical details"])

    with tab1:
        info_panel(
            "How to read the route map",
            "Blue line = sailing route. Blue D = depot. Green numbered circles = visited plants showing route order (1, 2, 3...). Gray markers = unvisited plants.",
        )
        render_solution_map(result, active_rows, depot, rank=rank)

    with tab2:
        df = pd.DataFrame(result["deliveries"])
        if not df.empty:
            df["Delivered (T)"] = pd.to_numeric(df["Delivered (T)"], errors="coerce").fillna(0)
            df["Arrival (hr)"] = pd.to_numeric(df["Arrival (hr)"], errors="coerce").fillna(0)
            df["Eff. Deadline (hr)"] = pd.to_numeric(df["Eff. Deadline (hr)"], errors="coerce").fillna(0)

            chart_left, chart_right = st.columns(2)

            with chart_left:
                delivery_bar = go.Figure(
                    data=[
                        go.Bar(
                            x=df["Plant"],
                            y=df["Delivered (T)"],
                            text=df["Delivered (T)"].round(1),
                            textposition="outside",
                            name="Delivered",
                        )
                    ]
                )
                delivery_bar.update_layout(
                    title="Delivered quantity by plant",
                    xaxis_title="Plant",
                    yaxis_title="Delivered (T)",
                )
                colorize_figure(delivery_bar)
                st.plotly_chart(delivery_bar, use_container_width=True, key=f"delivery_bar_{rank}")

            with chart_right:
                delivery_share = df[df["Delivered (T)"] > 0][["Plant", "Delivered (T)"]]
                if not delivery_share.empty:
                    delivery_pie = go.Figure(
                        data=[
                            go.Pie(
                                labels=delivery_share["Plant"],
                                values=delivery_share["Delivered (T)"],
                                hole=0.42,
                                textinfo="label+percent",
                            )
                        ]
                    )
                    delivery_pie.update_layout(title="Delivery share")
                    colorize_figure(delivery_pie)
                    st.plotly_chart(delivery_pie, use_container_width=True, key=f"delivery_pie_{rank}")

            timing_fig = go.Figure()
            timing_fig.add_trace(
                go.Bar(
                    x=df["Plant"],
                    y=df["Arrival (hr)"],
                    name="Arrival",
                )
            )
            timing_fig.add_trace(
                go.Bar(
                    x=df["Plant"],
                    y=df["Eff. Deadline (hr)"],
                    name="Deadline",
                )
            )
            timing_fig.update_layout(
                title="Arrival vs deadline",
                xaxis_title="Plant",
                yaxis_title="Hours",
                barmode="group",
            )
            colorize_figure(timing_fig)
            st.plotly_chart(timing_fig, use_container_width=True, key=f"delivery_timing_{rank}")

        def highlight_late(row: pd.Series):
            if not row.get("On Time", True):
                return ["background-color: #fff1f2"] * len(row)
            return [""] * len(row)

        st.dataframe(df.style.apply(highlight_late, axis=1), use_container_width=True, hide_index=True)
        st.download_button(
            "Download deliveries CSV",
            df.to_csv(index=False).encode("utf-8"),
            f"deliveries_sol{rank}.csv",
            "text/csv",
        )

    with tab3:
        cost_df = pd.DataFrame(
            [
                {"Component": "Charter cost", "Value ($)": round(result["charter"], 2)},
                {"Component": "Empty-ship fuel cost", "Value ($)": round(result["empty_fuel"], 2)},
                {"Component": "Cargo fuel cost", "Value ($)": round(result["cargo_fuel"], 2)},
                {"Component": "Lateness penalty", "Value ($)": round(result["lateness_penalty"], 2)},
            ]
        )

        cost_left, cost_right = st.columns(2)
        with cost_left:
            cost_bar = go.Figure(
                data=[
                    go.Bar(
                        x=cost_df["Component"],
                        y=cost_df["Value ($)"],
                        text=cost_df["Value ($)"].round(2),
                        textposition="outside",
                        name="Cost",
                    )
                ]
            )
            cost_bar.update_layout(title="Cost breakdown", xaxis_title="Component", yaxis_title="Cost ($)")
            colorize_figure(cost_bar)
            st.plotly_chart(cost_bar, use_container_width=True, key=f"cost_bar_{rank}")

        with cost_right:
            positive_costs = cost_df[cost_df["Value ($)"] > 0]
            if not positive_costs.empty:
                cost_pie = go.Figure(
                    data=[
                        go.Pie(
                            labels=positive_costs["Component"],
                            values=positive_costs["Value ($)"],
                            hole=0.42,
                            textinfo="label+percent",
                        )
                    ]
                )
                cost_pie.update_layout(title="Cost share")
                colorize_figure(cost_pie)
                st.plotly_chart(cost_pie, use_container_width=True, key=f"cost_pie_{rank}")

        max_row = cost_df.sort_values("Value ($)", ascending=False).iloc[0]
        info_panel(
            "Largest cost driver",
            f"The biggest component in this solution is {max_row['Component']} with ${max_row['Value ($)']:,.2f}.",
        )

        total_row = pd.DataFrame([{"Component": "TOTAL", "Value ($)": round(result["total_cost"], 2)}])
        st.dataframe(pd.concat([cost_df, total_row], ignore_index=True), use_container_width=True, hide_index=True)
        st.download_button(
            "Download result JSON",
            build_bundle(result),
            f"mirp_result_sol{rank}.json",
            "application/json",
        )

    with tab4:
        st.markdown("#### Active arcs")
        st.dataframe(pd.DataFrame(result["arcs"]), use_container_width=True, hide_index=True)
        pre = result.get("pre", {})
        if pre:
            st.markdown("#### Model coefficients")
            st.write(
                {
                    "worst_case_cargo_Q": round(pre.get("Q", 0.0), 3),
                    "penalty_coefficient": pre.get("penalty"),
                    "alpha": {i: round(v, 3) for i, v in pre.get("alpha", {}).items()},
                    "beta": {i: round(v, 4) for i, v in pre.get("beta", {}).items()},
                    "eff_l": {i: round(v, 2) for i, v in pre.get("eff_l", {}).items()},
                    "L_i": pre.get("L", {}),
                    "terminal_label": pre.get("terminal_label"),
                }
            )
        st.caption(
            f"OR-Tools SCIP | Variables: {result['n_vars']} | Constraints: {result['n_cons']} | Solve time: {result['elapsed']} s"
        )


# -----------------------------------------------------------------------------
# Page sections
# -----------------------------------------------------------------------------

def render_sidebar() -> None:
    st.sidebar.markdown("## ⚓ Maritime DSS")
    st.sidebar.markdown('<div class="nav-note">Simple navigation for setup, optimization, and plant monitoring.</div>', unsafe_allow_html=True)
    current_index = MENU_ITEMS.index(st.session_state.nav_page)
    selected = st.sidebar.radio("Main menu", MENU_ITEMS, index=current_index)
    if selected != st.session_state.nav_page:
        st.session_state.nav_page = selected
        st.rerun()

    active_rows = make_active_plant_rows()
    st.sidebar.divider()
    st.sidebar.metric("Active plants", len(active_rows))
    st.sidebar.metric("Saved results", 0 if st.session_state.last_result is None else 1)
    st.sidebar.metric("Default speed", f"{DEFAULT_SHIP['speed']:.0f} NM/hr")
    st.sidebar.divider()
    st.sidebar.caption("Use Home for quick access, Optimizer for setup and results, and Plant Map for the network overview.")


def render_header() -> None:
    st.markdown(
        f"""
        <div class="hero">
            <h1>{APP_TITLE}</h1>
            <p>{APP_SUBTITLE}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_home() -> None:
    render_header()
    active_rows = make_active_plant_rows()

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        quick_card("Plants in network", str(len(FIXED_SCENARIO["plants"])), "Monitor all plant locations", "teal")
    with k2:
        quick_card("Currently active", str(len(active_rows)), "Used in optimization", "blue")
    with k3:
        quick_card("Route modes", "2", "Open route or closed route", "purple")
    with k4:
        quick_card("Main views", "3", "Home, Optimizer, Plant Map", "orange")

    left, right = st.columns([1.1, 0.9])

    with left:
        info_panel(
            "How to use",
            "Start from the optimizer to choose active plants and vessel inputs. Then run the model and check the route map, deliveries, and cost analysis.",
        )

        button_col1, button_col2 = st.columns(2)
        with button_col1:
            if st.button("Open optimizer", type="primary", use_container_width=True):
                navigate("Optimizer")
        with button_col2:
            if st.button("View plant map", use_container_width=True):
                navigate("Plant Map")

        st.markdown("### Quick scenario overview")
        summary_df = pd.DataFrame(
            [
                {
                    "Plant": row["name"],
                    "Status": status_badge(row["enabled"]),
                    "Capacity (T)": row["cap"],
                    "Initial stock (T)": row["init_stock"],
                    "Deadline (hr)": row["deadline"],
                }
                for row in st.session_state.fixed_plants
            ]
        )
        st.dataframe(summary_df, use_container_width=True, hide_index=True)

    with right:
        st.markdown("### Active plant map")
        render_plant_map(active_rows, FIXED_SCENARIO["depot"], plot_key="home_plant_map")


def render_plant_map_page() -> None:
    render_header()
    depot = FIXED_SCENARIO["depot"]
    active_rows = make_active_plant_rows()

    left, right = st.columns([0.95, 1.05])
    with left:
        info_panel(
            "Map overview",
            "Blue marker (D) = Istanbul depot. Green numbered markers = active plants. Each plant displays its ID number directly on the marker for easy identification.",
        )
        st.markdown("### Plant summary")
        table_df = pd.DataFrame(active_rows if active_rows else [])
        if table_df.empty:
            st.warning("No active plants selected. Enable plants from the Optimizer page.")
        else:
            st.dataframe(table_df, use_container_width=True, hide_index=True)
            st.metric("Average deadline", f"{table_df['deadline'].mean():.1f} hr")
            st.metric("Average consumption", f"{table_df['cons_rate'].mean():.2f} T/hr")

    with right:
        st.markdown("### Network map")
        render_plant_map(active_rows, depot, plot_key="network_plant_map")


def render_optimizer() -> None:
    render_header()
    depot = FIXED_SCENARIO["depot"]

    setup_tab, results_tab = st.tabs(["Scenario setup", "Results"])

    with setup_tab:
        top_left, top_right = st.columns([1.25, 0.95])

        with top_left:
            st.markdown("### Select active plants")
            info_panel(
                "Plant setup",
                "Turn plants on or off, then adjust capacity, stock, consumption, and deadline values. Keeping only relevant plants makes the scenario easier to read.",
            )

            columns = st.columns(2)
            for idx, plant in enumerate(st.session_state.fixed_plants):
                with columns[idx % 2]:
                    with st.container(border=True):
                        toggle_col, title_col = st.columns([0.8, 1.2])
                        with toggle_col:
                            plant["enabled"] = st.toggle(
                                f"Use {plant['name']}",
                                value=plant["enabled"],
                                key=f"enabled_{idx}",
                            )
                        with title_col:
                            st.markdown(f"**{plant['name']}**")
                            st.caption(f"Lat {plant['lat']:.4f} | Lon {plant['lon']:.4f}")

                        c1, c2 = st.columns(2)
                        plant["cap"] = c1.number_input(
                            f"Capacity - {plant['name']}",
                            min_value=0.0,
                            value=float(plant["cap"]),
                            step=10.0,
                            key=f"cap_{idx}",
                        )
                        plant["init_stock"] = c2.number_input(
                            f"Initial stock - {plant['name']}",
                            min_value=0.0,
                            value=float(plant["init_stock"]),
                            step=10.0,
                            key=f"init_{idx}",
                        )
                        c3, c4 = st.columns(2)
                        plant["cons_rate"] = c3.number_input(
                            f"Consumption - {plant['name']}",
                            min_value=0.01,
                            value=float(plant["cons_rate"]),
                            step=0.1,
                            key=f"cons_{idx}",
                        )
                        plant["deadline"] = c4.number_input(
                            f"Deadline - {plant['name']}",
                            min_value=0.1,
                            value=float(plant.get("deadline") or plant["init_stock"] / plant["cons_rate"]),
                            step=1.0,
                            key=f"ddl_{idx}",
                        )

        with top_right:
            st.markdown("### Vessel and solver settings")
            with st.container(border=True):
                c1, c2 = st.columns(2)
                empty_weight = c1.number_input("Empty weight (T)", min_value=0.0, value=DEFAULT_SHIP["empty_weight"], step=100.0)
                pump_rate = c2.number_input("Pump rate (T/hr)", min_value=0.1, value=DEFAULT_SHIP["pump_rate"], step=5.0)
                prep_time = c1.number_input("Preparation time (hr)", min_value=0.0, value=DEFAULT_SHIP["prep_time"], step=0.1)
                charter_rate = c2.number_input("Charter rate ($/hr)", min_value=0.0, value=DEFAULT_SHIP["charter_rate"], step=50.0)
                fuel_cost = c1.number_input("Fuel cost ($/Ton-NM)", min_value=0.0, value=DEFAULT_SHIP["fuel_cost"], step=0.01, format="%.4f")
                speed = c2.number_input("Speed (NM/hr)", min_value=0.1, value=DEFAULT_SHIP["speed"], step=1.0)

            with st.container(border=True):
                o1, o2, o3 = st.columns(3)
                return_to_depot = o1.toggle("Closed route", value=False, help="If enabled, the vessel returns to depot after the last delivery.")
                top_n = o2.number_input("Top N solutions", min_value=1, max_value=10, value=1, step=1)
                penalty = o3.number_input(
                    "Penalty coefficient (P)",
                    min_value=0.0,
                    value=1_000_000.0,
                    step=100_000.0,
                    format="%.0f",
                    help="Higher penalty makes the model avoid lateness more strongly.",
                )
                st.caption("Soft-deadline model: lateness is allowed but penalized.")

            active_rows = make_active_plant_rows()
            route_mode = "Closed route" if return_to_depot else "Open route"
            ship = Ship(
                empty_weight=empty_weight,
                pump_rate=pump_rate,
                prep_time=prep_time,
                charter_rate=charter_rate,
                fuel_cost=fuel_cost,
                speed=speed,
            )

            show_summary = st.container(border=True)
            with show_summary:
                st.markdown("#### Quick summary")
                a, b, c, d = st.columns(4)
                a.metric("Active plants", len(active_rows))
                b.metric("Route type", route_mode)
                c.metric("Vessel speed", f"{ship.speed:.1f} NM/hr")
                d.metric("Pump rate", f"{ship.pump_rate:.1f} T/hr")

            if active_rows:
                plants = make_plants(active_rows)
                dist = compute_distance_matrix(depot["lat"], depot["lon"], active_rows)
                diagnostics = quick_diagnostics(plants, ship, dist, return_to_depot=return_to_depot)

                for warning in diagnostics.get("warnings", []):
                    st.warning(warning)
                for issue in diagnostics.get("issues", []):
                    st.error(issue)

                if st.button("Run optimization", type="primary", use_container_width=True):
                    with st.spinner("Solving..."):
                        result = run_solver(
                            plants,
                            ship,
                            dist,
                            penalty=penalty,
                            return_to_depot=return_to_depot,
                            top_n=int(top_n),
                        )
                    st.session_state.last_result = result
                    st.session_state.last_inputs = {"active_rows": active_rows, "depot": depot}
                    st.success("Optimization complete. Open the Results tab.")
            else:
                st.error("Select at least one plant to create a scenario.")

        active_rows = make_active_plant_rows()
        if active_rows:
            st.markdown("### Active plant table")
            st.dataframe(pd.DataFrame(active_rows), use_container_width=True, hide_index=True)

    with results_tab:
        st.markdown("### Optimization results")
        if st.session_state.last_result is None:
            info_panel(
                "No result yet",
                "Run the model from the Scenario setup tab to view optimization results here.",
            )
        else:
            render_results(
                st.session_state.last_result,
                st.session_state.last_inputs["active_rows"],
                st.session_state.last_inputs["depot"],
            )


# -----------------------------------------------------------------------------
# Session state
# -----------------------------------------------------------------------------

if "fixed_plants" not in st.session_state:
    st.session_state.fixed_plants = [dict(item, enabled=True) for item in FIXED_SCENARIO["plants"]]
if "last_result" not in st.session_state:
    st.session_state.last_result = None
if "last_inputs" not in st.session_state:
    st.session_state.last_inputs = None
if "nav_page" not in st.session_state:
    st.session_state.nav_page = "Home"


# -----------------------------------------------------------------------------
# App shell
# -----------------------------------------------------------------------------

render_sidebar()

if st.session_state.nav_page == "Home":
    render_home()
elif st.session_state.nav_page == "Optimizer":
    render_optimizer()
else:
    render_plant_map_page()
