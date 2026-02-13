import streamlit as st

# Neutral Palette
VINTAGE_WHITE = "#FAF6F0"
CREAM = "#F5F0E8"
PARCHMENT = "#EBE4D8"
WARM_SILVER = "#D1C8BB"
WARM_GRAY = "#8A7F75"
DRIFTWOOD = "#5C504A"
ESPRESSO = "#3A302A"
CHARCOAL = "#1E1814"

# Signal Palette
OLIVE = "#4B6A3A"
OCHRE = "#856517"
RUST = "#9B3B28"
DENIM = "#4A6A8A"

# Signal Tints
OLIVE_TINT = "#E8F0E4"
OCHRE_TINT = "#F5EDDA"
RUST_TINT = "#F5E4DF"
DENIM_TINT = "#E2EBF2"

# Accents
AMBER = "#C67D3E"
WALNUT = "#4A3728"

# Readability Fixes
INPUT_BG = "#FBFBF2"
INPUT_INK = "#2C241B"
SAND_BEIGE = "#EDE0D4"
WARM_STONE = "#E5E0D8"
DARK_SLATE = "#2E2A25"

def apply_theme():
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;700&display=swap');

    .stApp {{
        background-color: {CREAM};
    }}
    
    [data-testid="stSidebar"] {{
        background-color: {WALNUT};
    }}
    
    [data-testid="stSidebar"] * {{
        color: {PARCHMENT};
    }}
    
    [data-testid="stSidebar"] label p {{
        color: {SAND_BEIGE} !important;
        font-weight: bold;
    }}
    
    /* Sidebar Inputs */
    [data-testid="stSidebar"] input, 
    [data-testid="stSidebar"] select, 
    [data-testid="stSidebar"] div[data-baseweb="select"] > div {{
        background-color: {INPUT_BG} !important;
        color: {INPUT_INK} !important;
        font-weight: bold !important;
        font-size: 1.25rem !important;
    }}

    /* Metrics & Numbers */
    [data-testid="stMetricValue"] {{
        color: {CHARCOAL} !important;
        font-weight: bold;
        font-family: 'Roboto Mono', monospace !important;
    }}
    
    [data-testid="stMetricLabel"] {{
        color: {DRIFTWOOD} !important;
    }}
    
    /* Primary Buttons */
    div[data-testid="stButton"] button[kind="primary"],
    div[data-testid="stDownloadButton"] button {{
        background-color: {AMBER} !important;
        color: {CHARCOAL} !important;
        border: none;
    }}
    div[data-testid="stButton"] button[kind="primary"]:hover,
    div[data-testid="stDownloadButton"] button:hover {{
        background-color: {OCHRE} !important;
        color: {VINTAGE_WHITE} !important;
    }}
    
    /* Active Tabs */
    .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {{
        color: {AMBER} !important;
        border-bottom-color: {AMBER} !important;
    }}
    
    /* HTML Tables */
    table {{
        border: 1px solid {WARM_SILVER} !important;
        font-family: 'Roboto Mono', monospace;
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 1rem;
    }}
    th {{
        background-color: {PARCHMENT};
        color: {CHARCOAL};
        padding: 8px;
        border: 1px solid {WARM_SILVER};
        text-align: left;
    }}
    td {{
        padding: 8px;
        border: 1px solid {WARM_SILVER};
        color: {ESPRESSO};
    }}
    
    hr {{ border-color: {WARM_SILVER} !important; }}

    /* Custom Info Boxes */
    .info-box {{
        background-color: {WARM_STONE};
        border-left: 4px solid {DRIFTWOOD};
        color: {DARK_SLATE};
        padding: 12px;
        border-radius: 4px;
        margin-bottom: 12px;
    }}
    
    /* Signal Banners */
    .banner-success {{ background-color: {OLIVE_TINT}; color: {OLIVE}; border-left: 5px solid {OLIVE}; padding: 15px; font-weight: bold; margin-bottom: 15px; border-radius: 4px; }}
    .banner-warning {{ background-color: {OCHRE_TINT}; color: {OCHRE}; border-left: 5px solid {OCHRE}; padding: 15px; font-weight: bold; margin-bottom: 15px; border-radius: 4px; }}
    .banner-error {{ background-color: {RUST_TINT}; color: {RUST}; border-left: 5px solid {RUST}; padding: 15px; font-weight: bold; margin-bottom: 15px; border-radius: 4px; }}
    </style>
    """, unsafe_allow_html=True)

def priority_badge(level):
    if level == "HIGH":
        return f'<span style="background-color: {OLIVE_TINT}; color: {OLIVE}; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.8rem;">{level}</span>'
    elif level == "LOW":
        return f'<span style="background-color: {RUST_TINT}; color: {RUST}; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.8rem;">{level}</span>'
    return f'<span style="background-color: {DENIM_TINT}; color: {DENIM}; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.8rem;">{level}</span>'

def status_indicator(status):
    if "UNDER" in status.upper():
        return f'<span style="color: {OLIVE}; font-weight: bold;">{status}</span>'
    elif "OVER" in status.upper():
        return f'<span style="color: {RUST}; font-weight: bold;">{status}</span>'
    return f'<span style="color: {OCHRE}; font-weight: bold;">{status}</span>'

def alert_badge(alert_type):
    if not alert_type: return ""
    if "100K+ CLIFF" in alert_type:
        return f'<span style="background-color: {RUST_TINT}; color: {RUST}; padding: 4px 8px; border-radius: 4px; font-weight: bold; border-left: 4px solid {RUST}; font-size: 0.8rem;">{alert_type}</span>'
    return f'<span style="background-color: {OCHRE_TINT}; color: {OCHRE}; padding: 4px 8px; border-radius: 4px; font-weight: bold; border-left: 4px solid {OCHRE}; font-size: 0.8rem;">{alert_type}</span>'
