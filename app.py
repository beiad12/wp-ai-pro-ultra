import streamlit as st
import requests, base64, json, time, urllib.parse, csv, os, threading, ssl, socket, re

# Lets a background worker thread safely touch st.session_state — the officially
# documented pattern for background threads in Streamlit. Falls back to a no-op
# on very old Streamlit versions where background plan execution just won't be
# offered (checked at call time via _BG_CTX_OK below).
try:
    from streamlit.runtime.scriptrunner import add_script_run_ctx as _add_script_run_ctx
    _BG_CTX_OK = True
except ImportError:
    _BG_CTX_OK = False

# Optional AI provider SDKs — imported lazily so a missing package only
# disables that one provider instead of crashing the whole app.
try:
    import google.generativeai as genai
except ModuleNotFoundError:
    genai = None
try:
    import anthropic as anthropic_sdk
except ModuleNotFoundError:
    anthropic_sdk = None
try:
    import openai as openai_sdk
except ModuleNotFoundError:
    openai_sdk = None
try:
    from PIL import Image as PILImage
except ModuleNotFoundError:
    PILImage = None
import io
from io import StringIO
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

# Core dependencies — required. If missing, show a clear fix instead of a
# raw traceback (usually means pip installed into a different Python than
# the one running Streamlit — use "python -m pip install -r requirements.txt"
# and "python -m streamlit run app.py" with the SAME python each time).
_missing_core = []
try:
    from bs4 import BeautifulSoup
except ModuleNotFoundError:
    _missing_core.append("beautifulsoup4")
try:
    import pandas as pd
except ModuleNotFoundError:
    _missing_core.append("pandas")

if _missing_core:
    st.set_page_config(page_title="WP Pro Ultra — Setup needed", page_icon="⚠️")
    st.error(
        f"Missing required package(s): **{', '.join(_missing_core)}**\n\n"
        "This almost always means `pip` installed into a different Python than the one "
        "running Streamlit. Fix it by running BOTH commands with the exact same `python`:\n\n"
        "```\npython -m pip install --upgrade -r requirements.txt\npython -m streamlit run app.py\n```\n\n"
        "(On Mac/Linux use `python3` instead of `python`.) "
        "If you have multiple Python installs, this mismatch is the #1 cause of this error."
    )
    st.stop()

# ════════════════════════════════════════════════════════════
#  PAGE CONFIG + GLOBAL CSS
# ════════════════════════════════════════════════════════════
st.set_page_config(page_title="WP Pro Ultra", page_icon="⚡", layout="wide",
                   initial_sidebar_state="expanded")

# ════════════════════════════════════════════════════════════
#  THEME (light / dark) — must run before the big CSS block
# ════════════════════════════════════════════════════════════
if "theme" not in st.session_state:
    st.session_state.theme = "dark"

THEMES = {
    "dark": {
        "bg": "#0f0c1e",
        "sidebar-1": "#130d2e", "sidebar-2": "#0d0a20",
        "text-primary": "#e8e3ff", "text-secondary": "#c4b8f0", "text-muted": "#a89ddc",
        "muted-rgb": "168,157,220",
        "surface-rgb": "255,255,255", "surface-a1": "0.03", "surface-a2": "0.025", "surface-a3": "0.04",
        "input-rgb": "20,15,45",
        "shadow": "0 8px 28px rgba(0,0,0,0.35)",
    },
    "light": {
        "bg": "#f4f2fb",
        "sidebar-1": "#ffffff", "sidebar-2": "#f1eefb",
        "text-primary": "#1f1a3a", "text-secondary": "#453a72", "text-muted": "#6a5ea6",
        "muted-rgb": "106,94,166",
        "surface-rgb": "76,60,150", "surface-a1": "0.045", "surface-a2": "0.035", "surface-a3": "0.06",
        "input-rgb": "255,255,255",
        "shadow": "0 8px 28px rgba(90,80,150,0.12)",
    },
}
_T = THEMES[st.session_state.theme]
_root_vars = "\n".join(f"  --{k}: {v};" for k, v in _T.items())
st.markdown(f"<style>:root {{\n{_root_vars}\n}}</style>", unsafe_allow_html=True)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 0 !important; max-width: 100% !important; }
.stApp { background: var(--bg) !important; }
section[data-testid="stMain"] { background: var(--bg) !important; }

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, var(--sidebar-1) 0%, var(--sidebar-2) 100%) !important;
    border-right: 1px solid rgba(127,119,221,0.15) !important;
    min-width: 260px !important;
}
[data-testid="stSidebar"] > div { padding: 0 !important; }
[data-testid="stSidebar"] * { color: var(--text-muted) !important; }
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
    font-size: 9.5px !important;
    font-weight: 600 !important;
    letter-spacing: .12em !important;
    text-transform: uppercase !important;
    color: rgba(127,119,221,0.45) !important;
    margin: 18px 0 6px !important;
    padding: 0 4px;
}
[data-testid="stSidebar"] input {
    background: rgba(var(--surface-rgb),var(--surface-a3)) !important;
    border: 1px solid rgba(127,119,221,0.2) !important;
    border-radius: 10px !important;
    color: var(--text-primary) !important;
    font-size: 12.5px !important;
    transition: border-color .2s !important;
}
[data-testid="stSidebar"] input:focus {
    border-color: rgba(127,119,221,0.7) !important;
    box-shadow: 0 0 0 3px rgba(127,119,221,0.12) !important;
}
[data-testid="stSidebar"] input::placeholder { color: rgba(var(--muted-rgb),0.35) !important; }
[data-testid="stSidebar"] [data-baseweb="select"] > div {
    background: rgba(var(--surface-rgb),var(--surface-a3)) !important;
    border: 1px solid rgba(127,119,221,0.2) !important;
    border-radius: 10px !important;
    color: var(--text-primary) !important;
    font-size: 12.5px !important;
}
[data-testid="stSidebar"] [data-baseweb="popover"] {
    background: #1a1040 !important;
    border: 1px solid rgba(127,119,221,0.25) !important;
    border-radius: 12px !important;
}
[data-testid="stSidebar"] [role="option"] { background: transparent !important; color: var(--text-secondary) !important; }
[data-testid="stSidebar"] [role="option"]:hover { background: rgba(127,119,221,0.15) !important; }
[data-testid="stSidebar"] [aria-selected="true"] { background: rgba(127,119,221,0.2) !important; }
[data-testid="stSidebar"] [data-testid="stToggle"] label { color: var(--text-secondary) !important; font-size: 12.5px !important; }
[data-testid="stSidebar"] [data-testid="stToggle"] span[aria-checked="true"] {
    background: linear-gradient(135deg,#7F77DD,#534AB7) !important;
}
[data-testid="stSidebar"] [data-baseweb="tag"] {
    background: rgba(127,119,221,0.25) !important;
    border: 1px solid rgba(127,119,221,0.4) !important;
    border-radius: 6px !important;
}
[data-testid="stSidebar"] [data-baseweb="tag"] span { color: #d4cff5 !important; }
[data-testid="stSidebar"] [data-testid="stNumberInput"] input {
    background: rgba(var(--surface-rgb),var(--surface-a3)) !important;
    border: 1px solid rgba(127,119,221,0.2) !important;
}
[data-testid="stSidebar"] [data-testid="stSlider"] div[role="slider"] {
    background: #7F77DD !important;
    box-shadow: 0 0 8px rgba(127,119,221,0.5) !important;
}
[data-testid="stSidebar"] .stButton > button {
    width: 100% !important;
    background: rgba(127,119,221,0.1) !important;
    border: 1px solid rgba(127,119,221,0.25) !important;
    border-radius: 10px !important;
    color: var(--text-secondary) !important;
    font-size: 12.5px !important;
    font-weight: 500 !important;
    padding: 7px 14px !important;
    transition: all .2s !important;
    margin-bottom: 4px !important;
    text-align: left !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(127,119,221,0.22) !important;
    border-color: rgba(127,119,221,0.5) !important;
    color: #fff !important;
    transform: translateX(2px) !important;
}
[data-testid="stSidebar"] hr {
    border-color: rgba(127,119,221,0.12) !important;
    margin: 8px 0 !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] {
    background: rgba(var(--surface-rgb),var(--surface-a1)) !important;
    border: 1px solid rgba(127,119,221,0.15) !important;
    border-radius: 10px !important;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label { color: var(--text-secondary) !important; font-size: 12.5px !important; }

.conn-pill {
    display: flex !important; align-items: center !important; gap: 7px !important;
    padding: 6px 10px !important;
    background: rgba(var(--surface-rgb),var(--surface-a1)) !important;
    border: 1px solid rgba(127,119,221,0.12) !important;
    border-radius: 8px !important;
    font-size: 11.5px !important; color: var(--text-muted) !important; margin: 3px 0 !important;
}
.conn-dot { width: 7px !important; height: 7px !important; border-radius: 50% !important;
    background: #1D9E75 !important; flex-shrink: 0 !important;
    box-shadow: 0 0 6px rgba(29,158,117,0.5) !important; }
.conn-dot.off { background: #444 !important; box-shadow: none !important; }
.conn-dot.warn { background: #d4a012 !important; box-shadow: 0 0 6px rgba(212,160,18,0.4) !important; }

.stButton > button {
    font-family: 'Inter', sans-serif !important;
    border-radius: 12px !important;
    font-size: 12.5px !important;
    font-weight: 500 !important;
    transition: all .18s ease !important;
    letter-spacing: .01em !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #7F77DD 0%, #534AB7 100%) !important;
    border: 1px solid transparent !important;
    color: #fff !important;
    box-shadow: 0 4px 14px rgba(127,119,221,0.35) !important;
}
.stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #9189e8 0%, #6358c9 100%) !important;
    box-shadow: 0 6px 20px rgba(127,119,221,0.5) !important;
    transform: translateY(-1px) !important;
}
.stButton > button:not([kind="primary"]) {
    background: rgba(var(--surface-rgb),var(--surface-a3)) !important;
    border: 1px solid rgba(127,119,221,0.2) !important;
    color: var(--text-muted) !important;
}
.stButton > button:not([kind="primary"]):hover {
    background: rgba(127,119,221,0.12) !important;
    border-color: rgba(127,119,221,0.4) !important;
    color: #d4cff5 !important;
}

.stTextArea textarea, .stTextInput input, textarea,
input[type="text"], input[type="password"], input[type="number"] {
    background: rgba(var(--input-rgb),0.85) !important;
    border: 1px solid rgba(127,119,221,0.25) !important;
    border-radius: 12px !important;
    color: var(--text-primary) !important;
    caret-color: var(--text-muted) !important;
    font-size: 13px !important;
    font-family: 'Inter', sans-serif !important;
    transition: border-color .2s, box-shadow .2s !important;
}
.stTextArea textarea:focus, .stTextInput input:focus, textarea:focus, input:focus {
    border-color: rgba(127,119,221,0.7) !important;
    box-shadow: 0 0 0 3px rgba(127,119,221,0.15) !important;
    background: rgba(var(--input-rgb),0.95) !important;
    outline: none !important;
}
.stTextArea textarea::placeholder, .stTextInput input::placeholder,
textarea::placeholder, input::placeholder { color: rgba(var(--muted-rgb),0.35) !important; }
[data-baseweb="textarea"] textarea, [data-baseweb="input"] input {
    background: rgba(var(--input-rgb),0.85) !important;
    color: var(--text-primary) !important;
    caret-color: var(--text-muted) !important;
}
[data-baseweb="textarea"], [data-baseweb="input"] {
    background: rgba(var(--input-rgb),0.85) !important;
    border: 1px solid rgba(127,119,221,0.25) !important;
    border-radius: 12px !important;
}
[data-baseweb="select"] > div {
    background: rgba(var(--surface-rgb),var(--surface-a3)) !important;
    border: 1px solid rgba(127,119,221,0.2) !important;
    border-radius: 12px !important;
    color: var(--text-primary) !important;
    font-size: 13px !important;
}
[data-testid="stNumberInput"] input {
    background: rgba(var(--surface-rgb),var(--surface-a3)) !important;
    border: 1px solid rgba(127,119,221,0.2) !important;
    border-radius: 10px !important;
    color: var(--text-primary) !important;
}
[data-testid="stToggle"] label { color: var(--text-secondary) !important; font-size: 13px !important; }
[data-testid="stToggle"] span[aria-checked="true"] {
    background: linear-gradient(135deg,#7F77DD,#534AB7) !important;
    box-shadow: 0 0 8px rgba(127,119,221,0.4) !important;
}
[data-testid="stRadio"] label { color: var(--text-secondary) !important; font-size: 13px !important; }
[data-testid="stSlider"] div[role="slider"] {
    background: #7F77DD !important;
    box-shadow: 0 0 8px rgba(127,119,221,0.5) !important;
}
[data-testid="stSlider"] [data-testid="stMarkdownContainer"] { color: var(--text-muted) !important; font-size: 12px !important; }
.stProgress > div > div {
    background: linear-gradient(90deg, #7F77DD, var(--text-muted)) !important;
    border-radius: 99px !important;
    box-shadow: 0 0 10px rgba(127,119,221,0.4) !important;
}
.stProgress > div { background: rgba(127,119,221,0.1) !important; border-radius: 99px !important; height: 6px !important; }
.stAlert { border-radius: 12px !important; }
[data-testid="stNotification"] { border-radius: 12px !important; }
.stSpinner > div { border-top-color: #7F77DD !important; }
[data-baseweb="tag"] {
    background: rgba(127,119,221,0.2) !important;
    border: 1px solid rgba(127,119,221,0.35) !important;
    border-radius: 6px !important;
}
[data-baseweb="tag"] span { color: #d4cff5 !important; }
hr { border-color: rgba(127,119,221,0.1) !important; }
[data-testid="stExpander"] {
    background: rgba(var(--surface-rgb),var(--surface-a1)) !important;
    border: 1px solid rgba(127,119,221,0.15) !important;
    border-radius: 12px !important;
}
[data-testid="stExpander"] summary { color: var(--text-secondary) !important; font-size: 13px !important; }
[data-testid="stDownloadButton"] button {
    background: rgba(29,158,117,0.12) !important;
    border: 1px solid rgba(29,158,117,0.3) !important;
    border-radius: 10px !important;
    color: #1D9E75 !important;
    font-weight: 500 !important;
}
[data-testid="stDownloadButton"] button:hover {
    background: rgba(29,158,117,0.22) !important;
    border-color: rgba(29,158,117,0.5) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 14px rgba(29,158,117,0.25) !important;
}
[data-testid="stImage"] { border-radius: 12px !important; overflow: hidden !important; }
[data-testid="stImage"] img { border-radius: 12px !important; border: 1px solid rgba(127,119,221,0.15) !important; }
[data-testid="stMetric"] {
    background: rgba(var(--surface-rgb),var(--surface-a1)) !important;
    border: 1px solid rgba(127,119,221,0.15) !important;
    border-radius: 12px !important; padding: 14px 16px !important;
}
[data-testid="stMetricLabel"] { color: var(--text-muted) !important; font-size: 12px !important; }
[data-testid="stMetricValue"] { color: var(--text-primary) !important; font-size: 24px !important; font-weight: 600 !important; }
.stCodeBlock { border-radius: 10px !important; border: 1px solid rgba(127,119,221,0.15) !important; }

.stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; padding: 20px 24px 0; }
.stat-card {
    background: rgba(var(--surface-rgb),var(--surface-a1)); border: 1px solid rgba(127,119,221,0.15);
    border-radius: 16px; padding: 20px; position: relative; overflow: hidden;
    transition: transform .2s, box-shadow .2s;
}
.stat-card:hover { transform: translateY(-2px); box-shadow: var(--shadow); }
.stat-card::before { content:''; position:absolute; top:0;left:0;right:0; height:2px; background:var(--c); }
.stat-card.purple { --c: linear-gradient(90deg,#7F77DD,#534AB7); }
.stat-card.teal   { --c: linear-gradient(90deg,#1D9E75,#0F6E56); }
.stat-card.coral  { --c: linear-gradient(90deg,#D85A30,#993C1D); }
.stat-card.blue   { --c: linear-gradient(90deg,#378ADD,#1a5da8); }
.stat-card.amber  { --c: linear-gradient(90deg,#d4a012,#a07808); }
.stat-icon { width:40px;height:40px;border-radius:11px;display:flex;align-items:center;
    justify-content:center;font-size:19px;margin-bottom:14px; }
.stat-icon.purple { background: rgba(127,119,221,0.15); }
.stat-icon.teal   { background: rgba(29,158,117,0.15);  }
.stat-icon.coral  { background: rgba(216,90,48,0.15);   }
.stat-icon.blue   { background: rgba(55,138,221,0.15);  }
.stat-icon.amber  { background: rgba(212,160,18,0.15);  }
.stat-label { font-size:11px;font-weight:500;color:rgba(var(--muted-rgb),0.6);text-transform:uppercase;
    letter-spacing:.08em;margin-bottom:6px; }
.stat-val   { font-size:30px;font-weight:700;color:var(--text-primary);line-height:1; }
.stat-delta { font-size:11px;margin-top:6px; }
.stat-delta.good { color:#1D9E75; }
.stat-delta.warn { color:#D85A30; }
.stat-delta.info { color:#d4a012; }

.section-head { display:flex;align-items:center;gap:10px;padding:22px 24px 12px; }
.section-head h3 { font-size:15px;font-weight:600;color:var(--text-primary);flex:1;margin:0; }
.section-head .hint { font-size:12px;color:rgba(var(--muted-rgb),0.5); }

.post-table { margin: 0 24px 20px; }
.post-row-ui {
    display:flex;align-items:center;gap:12px;padding:12px 16px;
    background:rgba(var(--surface-rgb),var(--surface-a1));border:1px solid rgba(127,119,221,0.12);
    border-radius:12px;margin-bottom:6px;transition:all .15s;
}
.post-row-ui:hover { background:rgba(127,119,221,0.07);border-color:rgba(127,119,221,0.3);transform:translateX(2px); }
.post-thumb {
    width:40px;height:40px;border-radius:10px;background:rgba(127,119,221,0.1);
    display:flex;align-items:center;justify-content:center;font-size:17px;flex-shrink:0;
    border:1px solid rgba(127,119,221,0.15);
}
.post-thumb.has { background:rgba(29,158,117,0.12);border-color:rgba(29,158,117,0.2); }
.post-info { flex:1;min-width:0; }
.post-title-ui { font-size:13.5px;font-weight:500;color:var(--text-primary);white-space:nowrap;overflow:hidden;text-overflow:ellipsis; }
.post-meta-ui  { font-size:11.5px;color:rgba(var(--muted-rgb),0.55);margin-top:3px; }

.pill {
    display:inline-flex;align-items:center;gap:4px;padding:3px 10px;border-radius:999px;
    font-size:10.5px;font-weight:600;flex-shrink:0;letter-spacing:.02em;
}
.pill.pub     { background:rgba(29,158,117,0.15); color:#1D9E75; border:1px solid rgba(29,158,117,0.3); }
.pill.draft   { background:rgba(127,119,221,0.15);color:var(--text-muted); border:1px solid rgba(127,119,221,0.3); }
.pill.noimg   { background:rgba(216,90,48,0.15);  color:#D85A30; border:1px solid rgba(216,90,48,0.3); }
.pill.done    { background:rgba(29,158,117,0.15); color:#1D9E75; border:1px solid rgba(29,158,117,0.3); }
.pill.running { background:rgba(127,119,221,0.2); color:var(--text-secondary); border:1px solid rgba(127,119,221,0.4); }
.pill.err     { background:rgba(216,90,48,0.15);  color:#D85A30; border:1px solid rgba(216,90,48,0.3); }
.pill.skip    { background:rgba(234,179,8,0.15);  color:#d4a012; border:1px solid rgba(234,179,8,0.3); }
.pill.sched   { background:rgba(55,138,221,0.15); color:#378ADD; border:1px solid rgba(55,138,221,0.3); }

.panel-box {
    background:rgba(var(--surface-rgb),var(--surface-a1));border:1px solid rgba(127,119,221,0.15);
    border-radius:16px;margin:0 24px 16px;overflow:hidden;
}
.panel-box-head {
    display:flex;align-items:center;gap:10px;padding:14px 18px;
    border-bottom:1px solid rgba(127,119,221,0.1);background:rgba(127,119,221,0.04);
}
.panel-box-head h4 { font-size:13.5px;font-weight:600;color:var(--text-primary);flex:1;margin:0; }
.panel-box-head .hint { font-size:11px;color:rgba(var(--muted-rgb),0.5); }

.run-badge { display:inline-flex;align-items:center;gap:5px;padding:4px 12px;border-radius:999px;font-size:12px;font-weight:600; }
.run-badge.ok   { background:rgba(29,158,117,0.15);color:#1D9E75;border:1px solid rgba(29,158,117,0.3); }
.run-badge.err  { background:rgba(216,90,48,0.15); color:#D85A30;border:1px solid rgba(216,90,48,0.3); }
.run-badge.skip { background:rgba(127,119,221,0.15);color:var(--text-muted);border:1px solid rgba(127,119,221,0.3); }
.run-badge.gate { background:rgba(234,179,8,0.15); color:#d4a012;border:1px solid rgba(234,179,8,0.3); }
.run-badge.sched{ background:rgba(55,138,221,0.15);color:#378ADD;border:1px solid rgba(55,138,221,0.3); }

.sched-card {
    background: rgba(55,138,221,0.06);
    border: 1px solid rgba(55,138,221,0.2);
    border-radius: 14px;
    margin: 0 24px 16px;
    overflow: hidden;
}
.sched-card-head {
    display:flex;align-items:center;justify-content:space-between;
    padding:12px 18px;
    background: rgba(55,138,221,0.08);
    border-bottom:1px solid rgba(55,138,221,0.15);
}
.sched-card-title { font-size:13px;font-weight:600;color:#378ADD; }
.sched-card-badge {
    background:rgba(55,138,221,0.15);color:#378ADD;
    border:1px solid rgba(55,138,221,0.3);border-radius:999px;
    padding:2px 10px;font-size:11px;font-weight:600;
}
.sched-row {
    display:flex;align-items:center;gap:10px;padding:8px 18px;
    border-bottom:1px solid rgba(55,138,221,0.07);font-size:12.5px;
}
.sched-row:last-child { border-bottom:none; }
.sched-idx { width:28px;height:28px;border-radius:8px;background:rgba(55,138,221,0.12);
    display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;color:#378ADD;flex-shrink:0; }
.sched-time { color:#378ADD;font-weight:600;min-width:120px; }
.sched-label { color:var(--text-secondary);flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis; }
.sched-status { font-size:11px;font-weight:600;flex-shrink:0; }
.sched-status.future { color:#378ADD; }
.sched-status.now    { color:#1D9E75; }

.dash-progress-wrap {
    margin:16px 24px 0;background:rgba(var(--surface-rgb),var(--surface-a2));
    border:1px solid rgba(127,119,221,0.15);border-radius:14px;padding:18px 22px;
}
.dash-progress-head { display:flex;align-items:center;justify-content:space-between;margin-bottom:10px; }
.dash-progress-label { font-size:13px;font-weight:500;color:var(--text-secondary); }
.dash-progress-pct   { font-size:20px;font-weight:700;color:#7F77DD; }
.dash-pbar-track { height:8px;background:rgba(127,119,221,0.1);border-radius:4px;overflow:hidden;margin-bottom:10px; }
.dash-pbar-fill  { height:100%;background:linear-gradient(90deg,#1D9E75,#7F77DD);border-radius:4px;
    transition:width .6s ease;box-shadow:0 0 12px rgba(29,158,117,0.3); }
.dash-progress-sub { display:flex;gap:12px;font-size:12px;font-weight:500; }

.status-card, .alert-card, .summary-card, .getting-started {
    background:rgba(var(--surface-rgb),var(--surface-a2));border:1px solid rgba(127,119,221,0.15);
    border-radius:14px;padding:16px 18px;margin-bottom:12px;
}
.status-card-head { font-size:12px;font-weight:600;color:rgba(var(--muted-rgb),0.6);
    text-transform:uppercase;letter-spacing:.08em;margin-bottom:12px; }
.status-row { display:flex;align-items:center;gap:9px;padding:6px 0;border-bottom:1px solid rgba(127,119,221,0.07); }
.status-row:last-child { border-bottom:none; }
.status-dot { width:8px;height:8px;border-radius:50%;flex-shrink:0; }
.status-dot.on   { background:#1D9E75;box-shadow:0 0 6px rgba(29,158,117,0.5); }
.status-dot.off  { background:rgba(var(--muted-rgb),0.2); }
.status-dot.warn { background:#d4a012;box-shadow:0 0 6px rgba(212,160,18,0.4); }
.status-label { font-size:12.5px;color:var(--text-secondary); }
.alert-card { border-color:rgba(216,90,48,0.25); }
.alert-card .status-card-head { color:#D85A30; }
.alert-item { display:flex;align-items:center;gap:8px;padding:5px 0;font-size:12.5px;color:var(--text-secondary);
    border-bottom:1px solid rgba(216,90,48,0.07); }
.alert-item:last-child { border-bottom:none; }
.alert-dot { width:6px;height:6px;border-radius:50%;flex-shrink:0; }
.alert-dot.red { background:#D85A30;box-shadow:0 0 5px rgba(216,90,48,0.4); }
.summary-row { display:flex;align-items:center;justify-content:space-between;padding:7px 0;
    font-size:13px;color:rgba(var(--muted-rgb),0.7);border-bottom:1px solid rgba(127,119,221,0.07); }
.summary-row:last-child { border-bottom:none; }
.summary-row b { color:var(--text-primary);font-weight:600; }
.gs-step { display:flex;align-items:flex-start;gap:10px;padding:7px 0;font-size:12.5px;color:var(--text-secondary);
    border-bottom:1px solid rgba(127,119,221,0.07);line-height:1.5; }
.gs-step:last-child { border-bottom:none; }
.gs-num { width:20px;height:20px;border-radius:6px;background:rgba(127,119,221,0.2);
    border:1px solid rgba(127,119,221,0.3);display:flex;align-items:center;justify-content:center;
    font-size:11px;font-weight:700;color:#7F77DD;flex-shrink:0;margin-top:1px; }

.empty-feed { text-align:center;padding:50px 20px; }
.empty-icon  { font-size:40px;margin-bottom:14px;opacity:.5; }
.empty-title { font-size:15px;font-weight:600;color:var(--text-secondary);margin-bottom:6px; }
.empty-sub   { font-size:12.5px;color:rgba(var(--muted-rgb),0.45);line-height:1.6; }

.create-card { background:rgba(var(--surface-rgb),var(--surface-a2));border:1px solid rgba(127,119,221,0.15);
    border-radius:16px;padding:24px;margin:0 24px 20px; }

.hero-banner {
    margin: 18px 24px 0; padding: 16px 20px; border-radius: 14px;
    background: linear-gradient(135deg, rgba(127,119,221,0.12), rgba(29,158,117,0.08));
    border: 1px solid rgba(127,119,221,0.2);
    display: flex; align-items: center; gap: 14px;
}

/* ═══ Agent tab ═══ */
@keyframes agentPulse { 0%{box-shadow:0 0 0 0 rgba(127,119,221,0.55);} 70%{box-shadow:0 0 0 14px rgba(127,119,221,0);} 100%{box-shadow:0 0 0 0 rgba(127,119,221,0);} }
@keyframes agentFloat { 0%,100%{transform:translateY(0);} 50%{transform:translateY(-3px);} }
@keyframes agentFadeUp { from{opacity:0; transform:translateY(10px);} to{opacity:1; transform:translateY(0);} }
@keyframes agentGlowSpin { 0%{transform:rotate(0deg);} 100%{transform:rotate(360deg);} }
@keyframes dotBounce { 0%,60%,100%{transform:translateY(0); opacity:.4;} 30%{transform:translateY(-5px); opacity:1;} }
@keyframes onlineBlink { 0%,100%{opacity:1;} 50%{opacity:.35;} }

.agent-hero {
    margin: 18px 24px 16px; padding: 22px 26px; border-radius: 20px; position: relative; overflow: hidden;
    background: linear-gradient(135deg, rgba(127,119,221,0.16), rgba(29,158,117,0.07) 60%, rgba(55,138,221,0.08));
    border: 1px solid rgba(127,119,221,0.22);
    display: flex; align-items: center; gap: 18px;
}
.agent-hero::before {
    content: ''; position: absolute; top: -60%; right: -10%; width: 260px; height: 260px; border-radius: 50%;
    background: radial-gradient(circle, rgba(127,119,221,0.25), transparent 70%);
    animation: agentGlowSpin 18s linear infinite;
}
.agent-orb {
    width: 54px; height: 54px; border-radius: 50%; flex-shrink: 0; position: relative; z-index: 1;
    background: linear-gradient(135deg,#9189e8,#534AB7);
    display: flex; align-items: center; justify-content: center; font-size: 24px;
    box-shadow: 0 6px 20px rgba(127,119,221,0.45);
    animation: agentFloat 3.4s ease-in-out infinite, agentPulse 2.6s ease-in-out infinite;
}
.agent-hero-body { position: relative; z-index: 1; flex: 1; }
.agent-hero-title { font-size: 17px; font-weight: 700; color: var(--text-primary); display: flex; align-items: center; gap: 8px; }
.agent-hero-sub { font-size: 12.5px; color: var(--text-muted); margin-top: 4px; }
.agent-online-dot { width: 8px; height: 8px; border-radius: 50%; background: #1D9E75; box-shadow: 0 0 6px rgba(29,158,117,0.6); animation: onlineBlink 2s ease-in-out infinite; }
.agent-online-pill {
    display: inline-flex; align-items: center; gap: 6px; font-size: 11px; font-weight: 600; color: #1D9E75;
    background: rgba(29,158,117,0.12); border: 1px solid rgba(29,158,117,0.3); border-radius: 999px; padding: 3px 10px;
}
.agent-status-row { position: relative; z-index: 1; display: flex; gap: 10px; align-items: center; flex-wrap: wrap; margin-top: 8px; }
.agent-status-chip {
    font-size: 11.5px; color: var(--text-secondary); background: rgba(var(--surface-rgb),var(--surface-a3));
    border: 1px solid rgba(127,119,221,0.15); border-radius: 999px; padding: 4px 11px;
}

/* Chat bubbles (targets Streamlit's native chat_message component) */
[data-testid="stChatMessage"] { animation: agentFadeUp .4s cubic-bezier(.2,.7,.3,1) both; margin-bottom: 6px !important; }
[data-testid="stChatMessageContent"] {
    background: rgba(var(--surface-rgb),var(--surface-a2)) !important;
    border: 1px solid rgba(127,119,221,0.16) !important;
    border-radius: 16px !important; padding: 12px 16px !important;
}
[data-testid="stChatMessageAvatarAssistant"] {
    background: linear-gradient(135deg,#9189e8,#534AB7) !important;
    animation: agentPulse 2.6s ease-in-out infinite;
}
[data-testid="stChatMessageAvatarUser"] {
    background: linear-gradient(135deg,#378ADD,#1a5da8) !important;
}

.typing-dots { display: inline-flex; gap: 4px; padding: 4px 2px; }
.typing-dots span {
    width: 6px; height: 6px; border-radius: 50%; background: #9189e8;
    animation: dotBounce 1.2s ease-in-out infinite;
}
.typing-dots span:nth-child(2) { animation-delay: .15s; }
.typing-dots span:nth-child(3) { animation-delay: .3s; }

/* Suggestion-chip action buttons, scoped to the agent menu container */
div[class*="st-key-agent_menu"] .stButton > button {
    border-radius: 14px !important; padding: 14px 10px !important; font-size: 12.5px !important;
    background: rgba(var(--surface-rgb),var(--surface-a2)) !important;
    border: 1px solid rgba(127,119,221,0.18) !important;
    transition: transform .18s ease, box-shadow .18s ease, border-color .18s ease !important;
}
div[class*="st-key-agent_menu"] .stButton > button:hover:not(:disabled) {
    transform: translateY(-3px) !important;
    border-color: rgba(127,119,221,0.55) !important;
    box-shadow: 0 8px 20px rgba(127,119,221,0.25) !important;
}
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
#  HELPERS
# ════════════════════════════════════════════════════════════
PROGRESS_FILE = "wp_pro_progress.json"
PROFILES_FILE = "wp_pro_profiles.json"

def load_profiles():
    try:
        with open(PROFILES_FILE) as f: return json.load(f)
    except Exception: return {}

def save_profile(name, data):
    profiles = load_profiles()
    profiles[name] = data
    with open(PROFILES_FILE, "w") as f: json.dump(profiles, f, indent=2)

def delete_profile(name):
    profiles = load_profiles()
    profiles.pop(name, None)
    with open(PROFILES_FILE, "w") as f: json.dump(profiles, f, indent=2)

SETTINGS_FILE = "wp_pro_settings.json"

def load_settings():
    try:
        with open(SETTINGS_FILE) as f: return json.load(f)
    except Exception: return {}

def save_settings(data):
    with open(SETTINGS_FILE, "w") as f: json.dump(data, f)

def get_greeting(name):
    hour = datetime.now().hour
    if 5 <= hour < 12: part = "Good morning"
    elif 12 <= hour < 18: part = "Good afternoon"
    else: part = "Good evening"
    return f"{part}, {name}!" if name else f"{part}!"

def make_auth(user, pw):
    clean = pw.replace(" ", "").strip()
    return base64.b64encode(f"{user}:{clean}".encode()).decode()

def load_progress():
    try:
        with open(PROGRESS_FILE) as f: return json.load(f)
    except Exception: return {"processed": [], "results": []}

def save_progress(state):
    with open(PROGRESS_FILE, "w") as f: json.dump(state, f)

def reset_progress():
    if os.path.exists(PROGRESS_FILE): os.remove(PROGRESS_FILE)

def fetch_all_posts(auth, target_domain, statuses, max_count):
    all_posts, page, per_page = [], 1, 100
    headers = {"Authorization": f"Basic {auth}"}
    while True:
        url = f"https://{target_domain}/wp-json/wp/v2/posts"
        params = {"status": ",".join(statuses), "per_page": per_page, "page": page,
                  "_fields": "id,title,content,excerpt,status,slug,link,date,modified,featured_media"}
        try:
            r = requests.get(url, headers=headers, params=params, timeout=30)
            if r.status_code == 400: break
            r.raise_for_status()
            batch = r.json()
            if not batch: break
            all_posts.extend(batch)
            if page >= int(r.headers.get("X-WP-TotalPages", 1)) or (max_count and len(all_posts) >= max_count): break
            page += 1
            time.sleep(0.2)
        except Exception: break
    return all_posts[:max_count] if max_count else all_posts

def fetch_wp_categories(auth, target_domain):
    url = f"https://{target_domain}/wp-json/wp/v2/categories"
    hdr = {"Authorization": f"Basic {auth}"}
    cats = {}
    try:
        r = requests.get(url, headers=hdr,
                         params={"per_page": 100, "_fields": "id,name,slug,count"}, timeout=20)
        r.raise_for_status()
        for c in r.json():
            cats[c["name"]] = c["id"]
    except Exception:
        pass
    return cats

def ai_pick_category(title, content_text, categories_dict, prov, key, model,
                     enable_fallback=False, fallback_keys=None):
    if not categories_dict:
        return None
    cat_list = "\n".join(f"- {name} (id:{cid})" for name, cid in categories_dict.items())
    system = "You are a WordPress content classifier. Return JSON only — no markdown."
    prompt = (
        f"Post title: {title}\n"
        f"Content excerpt: {content_text[:300]}\n\n"
        f"Available WordPress categories:\n{cat_list}\n\n"
        "Pick the single best matching category. "
        "Return JSON: {\"category_id\": <integer>, \"category_name\": \"<name>\"}\n"
        "If nothing matches well, return {\"category_id\": null, \"category_name\": \"uncategorized\"}."
    )
    try:
        raw  = run_ai(prompt, prov, key, model, 0.1, system, enable_fallback, fallback_keys)
        data = json.loads(raw.replace("```json","").replace("```","").strip())
        return data.get("category_id")
    except Exception:
        return None

# ── Smart 24h scheduling helper ─────────────────────────────
def calculate_post_schedule(n_posts, posts_per_day, start_hour=6, start_from_now=False):
    interval_minutes = (24 * 60) / max(posts_per_day, 1)
    now_utc = datetime.utcnow()

    if start_from_now:
        base = now_utc + timedelta(minutes=interval_minutes)
    else:
        base = now_utc.replace(hour=start_hour, minute=0, second=0, microsecond=0)
        if base <= now_utc:
            base += timedelta(days=1)

    return [base + timedelta(minutes=i * interval_minutes) for i in range(n_posts)]

FALLBACK_ORDER = ["claude", "openai", "mistral", "gemini"]

def friendly_error(e):
    s = str(e)
    if "429" in s or "Too Many Requests" in s: return "⏳ Rate limit — retrying..."
    if "401" in s or "Unauthorized" in s or "authentication" in s.lower(): return "🔑 API key invalid"
    if "403" in s or "Forbidden" in s: return "🚫 API key lacks permission"
    if "timeout" in s.lower() or "timed out" in s.lower(): return "⏱️ Request timed out"
    if "503" in s or "502" in s or "ConnectionError" in s: return "🔌 Provider unavailable"
    if "image" in s.lower() and ("content-type" in s.lower() or "non-image" in s.lower()): return "🖼️ Invalid image response"
    if "JSONDecodeError" in s or "json" in s.lower(): return "⚠️ Unexpected AI response format"
    short = s.split("\n")[0][:80]
    return short if short else "Unknown error"

def run_ai_provider(prompt, prov, key, model, temperature=0.3, system=None):
    if prov == "Claude" and anthropic_sdk is None:
        raise ModuleNotFoundError("The 'anthropic' package isn't installed. Run: python -m pip install anthropic")
    if prov == "OpenAI" and openai_sdk is None:
        raise ModuleNotFoundError("The 'openai' package isn't installed. Run: python -m pip install openai")
    if prov == "Gemini" and genai is None:
        raise ModuleNotFoundError("The 'google-generativeai' package isn't installed. Run: python -m pip install google-generativeai")
    if prov == "Claude":
        client = anthropic_sdk.Anthropic(api_key=key)
        msgs   = [{"role": "user", "content": prompt}]
        kwargs = {"model": model, "max_tokens": 4096, "messages": msgs}
        if system: kwargs["system"] = system
        return client.messages.create(**kwargs).content[0].text.strip()
    elif prov == "OpenAI":
        client = openai_sdk.OpenAI(api_key=key)
        msgs = []
        if system: msgs.append({"role": "system", "content": system})
        msgs.append({"role": "user", "content": prompt})
        return client.chat.completions.create(model=model, messages=msgs,
               temperature=temperature, max_tokens=4096).choices[0].message.content.strip()
    elif prov == "Mistral":
        url = "https://api.mistral.ai/v1/chat/completions"
        hdr = {"Content-Type": "application/json", "Authorization": f"Bearer {key}"}
        msgs = []
        if system: msgs.append({"role": "system", "content": system})
        msgs.append({"role": "user", "content": prompt})
        r = requests.post(url, headers=hdr, json={"model": model, "messages": msgs,
                          "temperature": temperature}, timeout=90)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    elif prov == "Gemini":
        genai.configure(api_key=key)
        full = f"{system}\n\n{prompt}" if system else prompt
        return genai.GenerativeModel(model).generate_content(full).text.strip()
    raise ValueError(f"Unknown provider: {prov}")

def run_ai(prompt, prov, key, model, temperature=0.3, system=None,
           enable_fallback=False, fallback_keys=None):
    last_err = None
    for attempt in range(5):
        try:
            return run_ai_provider(prompt, prov, key, model, temperature, system)
        except Exception as e:
            last_err = e
            err_str = str(e).lower()
            if "429" in err_str or "too many requests" in err_str or "rate limit" in err_str:
                wait = 20 * (attempt + 1)
            elif "503" in err_str or "502" in err_str or "timeout" in err_str:
                wait = 5 * (attempt + 1)
            elif attempt < 4:
                wait = 2 ** attempt
            else:
                break
            time.sleep(wait)
    if enable_fallback and fallback_keys:
        for fb_name in FALLBACK_ORDER:
            fb_key = (fallback_keys or {}).get(fb_name, "").strip()
            if not fb_key or fb_name.lower() == prov.lower(): continue
            fb_prov  = fb_name.capitalize()
            fb_model = {"claude": "claude-sonnet-4-20250514", "openai": "gpt-4o",
                        "mistral": "mistral-small-latest", "gemini": "gemini-1.5-flash"}[fb_name]
            try: return run_ai_provider(prompt, fb_prov, fb_key, fb_model, temperature, system)
            except Exception: continue
    raise last_err

def generate_seo_meta(title, content_text, prov, key, model, fb=False, fbk=None):
    sys = "You are an expert SEO copywriter. Return JSON only — no markdown."
    p   = (f"Post title: {title}\nContent: {content_text[:500]}\n"
           "Return JSON with keys: meta_description (≤155 chars), focus_keyword (2-4 words), excerpt (1-2 sentences).")
    raw = run_ai(p, prov, key, model, 0.1, sys, fb, fbk)
    return json.loads(raw.replace("```json","").replace("```","").strip())

def generate_schema_jsonld(title, url, date_pub, desc):
    return json.dumps({"@context":"https://schema.org","@type":"Article",
                        "headline":title,"url":url,"datePublished":date_pub,
                        "description":desc,"publisher":{"@type":"Organization","name":"WordPress Site"}},
                      ensure_ascii=False)

def quality_gate(html_content, min_words):
    words = len(BeautifulSoup(html_content, "html.parser").get_text().split())
    return words, words >= min_words

def gen_image_dalle(prompt_text, openai_key, style):
    if openai_sdk is None:
        raise ModuleNotFoundError("The 'openai' package isn't installed. Run: python -m pip install openai")
    client   = openai_sdk.OpenAI(api_key=openai_key)
    resp     = client.images.generate(model="dall-e-3", prompt=prompt_text[:3000],
                                      size="1792x1024", style=style, n=1)
    img_resp = requests.get(resp.data[0].url, timeout=90)
    if "image" not in img_resp.headers.get("Content-Type",""):
        raise ValueError("Non-image returned")
    return img_resp.content

def gen_image_pollinations(prompt_text):
    safe = " ".join(prompt_text.split())[:800]
    url  = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(safe,safe='')}?width=1200&height=630&nologo=true&seed=42"
    r    = requests.get(url, timeout=90, headers={"User-Agent":"Mozilla/5.0"})
    r.raise_for_status()
    if "image" not in r.headers.get("Content-Type",""):
        raise ValueError("Non-image returned")
    return r.content

def upload_wp_image(img_bytes, title, alt_text, auth, target_domain, do_seo):
    media_url = f"https://{target_domain}/wp-json/wp/v2/media"
    safe_fn   = "".join(x for x in title if x.isalnum() or x in " -").replace(" ","-").lower()[:60]+"-featured.jpg"
    up_hdr    = {"Authorization":f"Basic {auth}","Content-Disposition":f'attachment; filename="{safe_fn}"',
                 "Content-Type":"image/jpeg","User-Agent":"WP-Pro-Ultra/2.0"}
    media_id  = None
    for attempt in range(3):
        try:
            r = requests.post(media_url, headers=up_hdr, data=img_bytes, timeout=60)
            r.raise_for_status(); media_id = r.json().get("id"); break
        except Exception as e:
            if attempt == 2: raise e
            time.sleep(2**attempt)
    if do_seo and media_id:
        ph = {"Authorization":f"Basic {auth}","Content-Type":"application/json"}
        for _ in range(3):
            try:
                requests.post(f"{media_url}/{media_id}", headers=ph,
                              json={"alt_text":alt_text,"title":title,"description":alt_text,"caption":alt_text},
                              timeout=30); break
            except Exception: time.sleep(1)
    return media_id

def wp_update_post(post_id, payload, auth, target_domain):
    url = f"https://{target_domain}/wp-json/wp/v2/posts/{post_id}"
    hdr = {"Authorization":f"Basic {auth}","Content-Type":"application/json"}
    r   = None
    for attempt in range(3):
        try:
            r = requests.post(url, headers=hdr, json=payload, timeout=45)
            r.raise_for_status(); return r
        except Exception:
            if attempt == 2: return r
            time.sleep(2**attempt)

def wp_create_post(payload, auth, target_domain):
    url = f"https://{target_domain}/wp-json/wp/v2/posts"
    hdr = {"Authorization":f"Basic {auth}","Content-Type":"application/json"}
    r   = None
    for attempt in range(3):
        try:
            r = requests.post(url, headers=hdr, json=payload, timeout=45)
            r.raise_for_status(); return r
        except Exception:
            if attempt == 2: return r
            time.sleep(2**attempt)

def update_yoast_meta(post_id, meta_desc, focus_kw, auth, target_domain):
    url = f"https://{target_domain}/wp-json/wp/v2/posts/{post_id}"
    hdr = {"Authorization":f"Basic {auth}","Content-Type":"application/json"}
    payload = {"meta":{"_yoast_wpseo_metadesc":meta_desc,"_yoast_wpseo_focuskw":focus_kw,
                        "rank_math_description":meta_desc,"rank_math_focus_keyword":focus_kw}}
    try: requests.post(url, headers=hdr, json=payload, timeout=30)
    except Exception: pass

def wp_install_plugin(slug, auth, target_domain, activate=True):
    """Installs (and optionally activates) a plugin straight from the
    WordPress.org repository via the core wp/v2/plugins REST endpoint
    (WP 5.5+). Requires an Application Password for a user with
    'install_plugins' capability, and a host that allows direct
    filesystem writes (most do; some shared hosts require FTP creds,
    in which case this fails cleanly with a manual-install message)."""
    base = f"https://{target_domain}/wp-json/wp/v2/plugins"
    hdr  = {"Authorization": f"Basic {auth}", "Content-Type": "application/json"}
    try:
        r = requests.post(base, headers=hdr,
                           json={"slug": slug, "status": "active" if activate else "inactive"},
                           timeout=60)
        if r.status_code in (200, 201):
            return True, "Installed and activated." if activate else "Installed."
        # Possibly already installed — find it and just activate
        try:
            lr = requests.get(base, headers=hdr, params={"search": slug}, timeout=30)
            if lr.status_code == 200:
                for p in lr.json():
                    if slug in p.get("plugin",""):
                        if activate and p.get("status") != "active":
                            ar = requests.put(f"{base}/{p['plugin']}", headers=hdr,
                                               json={"status":"active"}, timeout=30)
                            if ar.status_code == 200:
                                return True, "Was already installed — activated now."
                            return False, f"Found the plugin but couldn't activate it (HTTP {ar.status_code})."
                        return True, "Already installed and active."
        except Exception:
            pass
        detail = ""
        try: detail = r.json().get("message","")
        except Exception: pass
        return False, (detail or
            f"HTTP {r.status_code} — your host likely requires FTP credentials for plugin installs "
            f"(common on shared hosting). Install '{slug}' manually: WP Admin → Plugins → Add New → search, install, activate.")
    except Exception as e:
        return False, friendly_error(e)

# ════════════════════════════════════════════════════════════
#  GROWTH & DATA HELPERS (Pinterest / keyword research / analytics)
#  All three need a real, paid or free-tier third-party account —
#  same pattern as the PageSpeed/DALL-E keys above: paste your own
#  key/token in the sidebar, nothing is faked if it's missing.
# ════════════════════════════════════════════════════════════
def post_to_pinterest(image_url, title, description, link, board_id, access_token):
    """Creates a Pinterest Pin via the Pinterest API v5. Requires a Pinterest
    access token (Developers → your app → Generate token) and a board ID
    (visible in the board's URL). Returns (ok, message)."""
    if not access_token or not board_id:
        return False, ("Pinterest isn't configured — add a Pinterest access token and board ID "
                       "in the sidebar under GROWTH & DATA APIs.")
    if not image_url:
        return False, "This post has no image to pin — add a featured image first."
    try:
        r = requests.post(
            "https://api.pinterest.com/v5/pins",
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
            json={"board_id": board_id, "title": title[:100], "description": description[:500],
                  "link": link, "media_source": {"source_type": "image_url", "url": image_url}},
            timeout=30)
        if r.status_code in (200, 201):
            data = r.json()
            return True, f"Pinned to board — pin id {data.get('id','?')}. https://pinterest.com/pin/{data.get('id','')}/"
        try: detail = r.json().get("message", r.text[:200])
        except Exception: detail = r.text[:200]
        return False, f"Pinterest API error (HTTP {r.status_code}): {detail}"
    except Exception as e:
        return False, friendly_error(e)

def keyword_research_dataforseo(keyword, login, password, location_code=2840, language_code="en"):
    """Looks up search volume / CPC / competition for a keyword via DataForSEO's
    Google Ads search-volume endpoint. Requires a DataForSEO login+password
    (dataforseo.com, pay-as-you-go). Returns (ok, data-dict-or-message)."""
    if not login or not password:
        return False, ("Keyword research isn't configured — add your DataForSEO login and password "
                       "in the sidebar under GROWTH & DATA APIs.")
    try:
        r = requests.post(
            "https://api.dataforseo.com/v3/keywords_data/google_ads/search_volume/live",
            auth=(login, password), timeout=30,
            json=[{"keywords": [keyword], "location_code": location_code, "language_code": language_code}])
        if r.status_code != 200:
            return False, f"DataForSEO error (HTTP {r.status_code}): {r.text[:200]}"
        data = r.json()
        tasks = data.get("tasks") or []
        if not tasks or not tasks[0].get("result"):
            return False, "No data returned for that keyword — check spelling or try a broader term."
        result = tasks[0]["result"][0]
        return True, {
            "keyword": result.get("keyword", keyword),
            "search_volume": result.get("search_volume"),
            "competition": result.get("competition"),
            "cpc": result.get("cpc"),
            "monthly_trend": [m.get("search_volume") for m in (result.get("monthly_searches") or [])[-6:]],
        }
    except Exception as e:
        return False, friendly_error(e)

def fetch_ga4_report(property_id, access_token, days=28):
    """Pulls a basic traffic summary (sessions, active users, top pages) from
    the Google Analytics 4 Data API. Requires a GA4 property ID and a Google
    OAuth access token pasted in the sidebar — access tokens expire in about
    an hour, so this needs a fresh one from Google's OAuth Playground or your
    own token-refresh setup each time. Returns (ok, data-dict-or-message)."""
    if not property_id or not access_token:
        return False, ("Analytics isn't configured — add a GA4 property ID and access token in the "
                       "sidebar under GROWTH & DATA APIs.")
    try:
        r = requests.post(
            f"https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:runReport",
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
            json={
                "dateRanges": [{"startDate": f"{days}daysAgo", "endDate": "today"}],
                "dimensions": [{"name": "pagePath"}],
                "metrics": [{"name": "sessions"}, {"name": "activeUsers"}, {"name": "screenPageViews"}],
                "orderBys": [{"metric": {"metricName": "sessions"}, "desc": True}],
                "limit": 10,
            }, timeout=30)
        if r.status_code != 200:
            try: detail = r.json().get("error", {}).get("message", r.text[:200])
            except Exception: detail = r.text[:200]
            return False, f"Google Analytics error (HTTP {r.status_code}): {detail}"
        data = r.json()
        rows = data.get("rows") or []
        top_pages = [{"path": row["dimensionValues"][0]["value"],
                      "sessions": row["metricValues"][0]["value"],
                      "users": row["metricValues"][1]["value"],
                      "views": row["metricValues"][2]["value"]} for row in rows]
        totals = (data.get("totals") or [{}])[0].get("metricValues", [])
        return True, {
            "days": days,
            "total_sessions": totals[0]["value"] if len(totals) > 0 else None,
            "total_users": totals[1]["value"] if len(totals) > 1 else None,
            "total_views": totals[2]["value"] if len(totals) > 2 else None,
            "top_pages": top_pages,
        }
    except Exception as e:
        return False, friendly_error(e)

# ════════════════════════════════════════════════════════════
#  THEME & DESIGN HELPERS
# ════════════════════════════════════════════════════════════
def fetch_wp_settings(auth, target_domain):
    """GET /wp-json/wp/v2/settings — requires manage_options on the
    Application Password's user. Returns (settings_dict, error_message)."""
    url = f"https://{target_domain}/wp-json/wp/v2/settings"
    hdr = {"Authorization": f"Basic {auth}"}
    try:
        r = requests.get(url, headers=hdr, timeout=20)
        if r.status_code == 200:
            return r.json(), ""
        return {}, f"HTTP {r.status_code}: {r.text[:300]}"
    except Exception as e:
        return {}, friendly_error(e)

def update_wp_settings(fields, auth, target_domain):
    """POST partial fields to /wp-json/wp/v2/settings. Returns (ok, message)
    with the real response text on failure — never a generic error."""
    url = f"https://{target_domain}/wp-json/wp/v2/settings"
    hdr = {"Authorization": f"Basic {auth}", "Content-Type": "application/json"}
    try:
        r = requests.post(url, headers=hdr, json=fields, timeout=30)
        if r.status_code == 200:
            return True, "Saved."
        return False, f"HTTP {r.status_code}: {r.text[:300]}"
    except Exception as e:
        return False, friendly_error(e)

def generate_alt_text(title, prov, key, model, fb=False, fbk=None):
    """Same alt-text prompt used in the Fix Images tab, factored out so
    the Theme & Design media manager can reuse it instead of duplicating."""
    raw = run_ai(f"SEO image alt text under 120 chars for '{title}'. No quotes.",
                 prov, key, model, 0.1, enable_fallback=fb, fallback_keys=fbk)
    return raw.replace('"', '').strip()

def crop_square(img_bytes, size=512):
    """Center-crops to a square and resizes to size x size — WordPress
    requires the site icon to be square (512x512 recommended)."""
    if PILImage is None:
        raise ModuleNotFoundError("Pillow isn't installed. Run: python -m pip install Pillow")
    im = PILImage.open(io.BytesIO(img_bytes)).convert("RGB")
    w, h = im.size
    side = min(w, h)
    left, top = (w - side) // 2, (h - side) // 2
    im = im.crop((left, top, left + side, top + side)).resize((size, size), PILImage.LANCZOS)
    out = io.BytesIO()
    im.save(out, format="JPEG", quality=90)
    return out.getvalue()

def fetch_active_theme_info(auth, target_domain):
    """GET /wp-json/wp/v2/themes?status=active — requires edit_theme_options
    (or manage_options). Returns (theme_dict_or_None, error_message)."""
    url = f"https://{target_domain}/wp-json/wp/v2/themes"
    hdr = {"Authorization": f"Basic {auth}"}
    try:
        r = requests.get(url, headers=hdr, params={"status": "active"}, timeout=20)
        if r.status_code != 200:
            return None, f"HTTP {r.status_code}: {r.text[:300]}"
        data = r.json()
        return (data[0], "") if data else (None, "No active theme returned.")
    except Exception as e:
        return None, friendly_error(e)

def fetch_global_styles(theme_slug, auth, target_domain):
    """Read-only resolved global styles (colors/typography) for a block
    theme, via the stable core endpoint added in WP 6.0. Classic
    (non-block) themes don't have one — callers should check first."""
    url = f"https://{target_domain}/wp-json/wp/v2/global-styles/themes/{theme_slug}"
    hdr = {"Authorization": f"Basic {auth}"}
    try:
        r = requests.get(url, headers=hdr, timeout=20)
        if r.status_code == 200:
            return r.json(), ""
        return None, f"HTTP {r.status_code}: {r.text[:300]}"
    except Exception as e:
        return None, friendly_error(e)

def find_user_global_styles_link(theme_info):
    """The writable per-site Global Styles record isn't at a fixed URL —
    it's discovered via the active theme's _links, the same mechanism the
    Site Editor itself uses to bootstrap. Returns the href or None."""
    links = (theme_info or {}).get("_links", {})
    for rel, entries in links.items():
        if "global-styles" in rel.lower():
            for e in entries:
                if e.get("href"):
                    return e["href"]
    return None

PALETTE_PRESETS = {
    "Navy / Cyan Fintech":            {"primary": "#0B1F3A", "secondary": "#0E2A52", "accent": "#22D3EE", "text": "#0B1220"},
    "Charcoal / Gold Editorial":      {"primary": "#1C1C1C", "secondary": "#2A2A2A", "accent": "#C9A227", "text": "#1A1A1A"},
    "Deep Blue / White Classic News": {"primary": "#0A2A66", "secondary": "#123B8F", "accent": "#FFFFFF", "text": "#111111"},
}

def build_style_variation_snippet(palette):
    """Builds a valid theme.json-format 'settings.color.palette' + 'styles'
    block for the chosen palette — the safe fallback the user can hand-paste
    when a direct REST write isn't possible (classic theme, missing
    capability, older WP version)."""
    variation = {
        "$schema": "https://schemas.wp.org/trunk/theme.json",
        "version": 2,
        "settings": {"color": {"palette": [
            {"slug": "primary",   "name": "Primary",   "color": palette["primary"]},
            {"slug": "secondary", "name": "Secondary", "color": palette["secondary"]},
            {"slug": "accent",    "name": "Accent",    "color": palette["accent"]},
            {"slug": "text",      "name": "Text",      "color": palette["text"]},
        ]}},
        "styles": {
            "color": {"background": palette["primary"], "text": palette["text"]},
            "elements": {
                "link":   {"color": {"text": palette["accent"]}},
                "button": {"color": {"background": palette["accent"], "text": palette["primary"]}},
            },
        },
    }
    return json.dumps(variation, indent=2)

def apply_global_styles_colors(palette, auth, target_domain, theme_info):
    """Best-effort direct write: reads the FULL existing Global Styles
    object and writes it back with only the palette merged in — never a
    blind partial patch, which risks wiping out settings the theme author
    configured. Returns (ok, message)."""
    href = find_user_global_styles_link(theme_info)
    if not href:
        return False, "This theme doesn't expose a writable Global Styles record (classic themes don't have one)."
    hdr = {"Authorization": f"Basic {auth}"}
    try:
        r = requests.get(href, headers=hdr, timeout=20)
        if r.status_code != 200:
            return False, f"Couldn't read current Global Styles (HTTP {r.status_code}): {r.text[:300]}"
        current = r.json()
        if not current.get("id"):
            return False, "Global Styles record has no id — can't safely write back."

        settings = current.get("settings") or {}
        color_settings = settings.get("color") or {}
        kept = [c for c in (color_settings.get("palette") or [])
                if c.get("slug") not in ("primary", "secondary", "accent", "text")]
        color_settings["palette"] = kept + [
            {"slug": "primary",   "name": "Primary",   "color": palette["primary"]},
            {"slug": "secondary", "name": "Secondary", "color": palette["secondary"]},
            {"slug": "accent",    "name": "Accent",    "color": palette["accent"]},
            {"slug": "text",      "name": "Text",      "color": palette["text"]},
        ]
        settings["color"] = color_settings
        current["settings"] = settings

        styles = current.get("styles") or {}
        styles["color"] = {"background": palette["primary"], "text": palette["text"]}
        current["styles"] = styles

        put_hdr = {"Authorization": f"Basic {auth}", "Content-Type": "application/json"}
        pr = requests.post(href, headers=put_hdr, json=current, timeout=30)
        if pr.status_code == 200:
            return True, "Global Styles updated — check Appearance → Editor to confirm."
        return False, f"HTTP {pr.status_code}: {pr.text[:300]}"
    except Exception as e:
        return False, friendly_error(e)

def fetch_media_library(auth, target_domain, page=1, per_page=20):
    """Paginated GET /wp-json/wp/v2/media. Returns (items, total_pages, error)."""
    url = f"https://{target_domain}/wp-json/wp/v2/media"
    hdr = {"Authorization": f"Basic {auth}"}
    params = {"page": page, "per_page": per_page, "media_type": "image",
              "_fields": "id,source_url,media_details,alt_text,title,mime_type,date"}
    try:
        r = requests.get(url, headers=hdr, params=params, timeout=30)
        if r.status_code != 200:
            return [], 0, f"HTTP {r.status_code}: {r.text[:300]}"
        return r.json(), int(r.headers.get("X-WP-TotalPages", 1)), ""
    except Exception as e:
        return [], 0, friendly_error(e)

def find_posts_using_media(media_item, posts):
    """Cross-references only the currently loaded posts (there's no REST
    'what uses this image' reverse lookup) — as a featured image, or as an
    <img> inline in the content."""
    used_in = []
    src = media_item.get("source_url", "")
    for p in posts:
        if p.get("featured_media") == media_item["id"]:
            used_in.append({"id": p["id"], "title": p["title"]["rendered"], "as": "featured image"})
        elif src and src in p.get("content", {}).get("rendered", ""):
            used_in.append({"id": p["id"], "title": p["title"]["rendered"], "as": "inline image"})
    return used_in

def repoint_media_references(old_media_item, new_media_id, new_url, posts, auth, target_domain, is_dry_run=True):
    """After uploading a replacement image, points every loaded post that
    used the old one (as featured image or inline <img>) at the new one."""
    old_id, old_url = old_media_item["id"], old_media_item.get("source_url", "")
    results = []
    for p in posts:
        pid, title = p["id"], p["title"]["rendered"]
        payload, new_html = {}, None
        html = p.get("content", {}).get("rendered", "")
        if p.get("featured_media") == old_id:
            payload["featured_media"] = new_media_id
        if old_url and old_url in html:
            new_html = html.replace(old_url, new_url)
            payload["content"] = new_html
        if not payload:
            continue
        if is_dry_run:
            results.append({"id": pid, "title": title, "status": "ok",
                             "detail": "Preview: would update " + ", ".join(payload.keys())})
        else:
            try:
                wp_update_post(pid, payload, auth, target_domain)
                if "featured_media" in payload: p["featured_media"] = new_media_id
                if new_html is not None: p["content"]["rendered"] = new_html
                results.append({"id": pid, "title": title, "status": "ok",
                                 "detail": "Updated " + ", ".join(payload.keys())})
            except Exception as e:
                results.append({"id": pid, "title": title, "status": "error", "detail": friendly_error(e)})
    return results

def recompress_image(media_item, max_dimension=1600, quality=78, size_budget=400_000):
    """Downloads an existing media item and re-encodes it if it's larger
    than budget. Returns new JPEG bytes, or None if already within budget
    (nothing to do)."""
    if PILImage is None:
        raise ModuleNotFoundError("Pillow isn't installed. Run: python -m pip install Pillow")
    url = media_item.get("source_url")
    if not url:
        return None
    r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    original_size = len(r.content)
    im = PILImage.open(io.BytesIO(r.content))
    w, h = im.size
    if max(w, h) <= max_dimension and original_size <= size_budget:
        return None
    if max(w, h) > max_dimension:
        ratio = max_dimension / max(w, h)
        im = im.resize((max(1, int(w * ratio)), max(1, int(h * ratio))), PILImage.LANCZOS)
    out = io.BytesIO()
    im.convert("RGB").save(out, format="JPEG", quality=quality, optimize=True)
    return out.getvalue()

def fetch_block_patterns(auth, target_domain):
    """GET /wp-json/wp/v2/block-patterns/patterns — every pattern
    registered by the active theme or any plugin, core endpoint since 5.5."""
    url = f"https://{target_domain}/wp-json/wp/v2/block-patterns/patterns"
    hdr = {"Authorization": f"Basic {auth}"}
    try:
        r = requests.get(url, headers=hdr, timeout=20)
        if r.status_code == 200:
            return r.json(), ""
        return [], f"HTTP {r.status_code}: {r.text[:300]}"
    except Exception as e:
        return [], friendly_error(e)

def find_ticker_patterns(patterns):
    """Looks for a registered pattern that looks like a breaking-news
    ticker or a crypto price ticker, by slug/title keyword. Returns
    {'breaking': pattern_or_None, 'crypto': pattern_or_None}."""
    hits = {"breaking": None, "crypto": None}
    for p in patterns:
        haystack = ((p.get("name") or "") + " " + (p.get("title") or "")).lower()
        if hits["crypto"] is None and "crypto" in haystack:
            hits["crypto"] = p
        elif hits["breaking"] is None and ("breaking" in haystack or "ticker" in haystack):
            hits["breaking"] = p
    return hits

def get_homepage_page_id(settings):
    if settings.get("show_on_front") == "page" and settings.get("page_on_front"):
        return settings["page_on_front"]
    return None

TICKER_MARKERS = {
    "breaking": ("<!-- bemo:breaking-ticker:start -->", "<!-- bemo:breaking-ticker:end -->"),
    "crypto":   ("<!-- bemo:crypto-ticker:start -->", "<!-- bemo:crypto-ticker:end -->"),
}

def check_ticker_enabled(kind, page_id, auth, target_domain):
    """Reads the live homepage content to see whether our marker is already
    there — so the on/off state shown to the user reflects reality instead
    of assuming it starts disabled."""
    start_marker, _ = TICKER_MARKERS[kind]
    url = f"https://{target_domain}/wp-json/wp/v2/pages/{page_id}"
    hdr = {"Authorization": f"Basic {auth}"}
    try:
        r = requests.get(url, headers=hdr, params={"context": "edit", "_fields": "content"}, timeout=20)
        if r.status_code != 200:
            return None, f"HTTP {r.status_code}: {r.text[:300]}"
        content = r.json().get("content", {})
        raw = content.get("raw") or content.get("rendered") or ""
        return start_marker in raw, ""
    except Exception as e:
        return None, friendly_error(e)

def toggle_homepage_pattern(kind, enable, pattern, page_id, auth, target_domain, is_dry_run=True):
    """Inserts (or removes) a registered block pattern's markup at the top
    of the homepage, wrapped in an HTML comment marker so toggling it back
    off finds and removes exactly what was inserted — nothing else on the
    page is touched. Returns (ok, message)."""
    start_marker, end_marker = TICKER_MARKERS[kind]
    url = f"https://{target_domain}/wp-json/wp/v2/pages/{page_id}"
    hdr = {"Authorization": f"Basic {auth}"}
    try:
        r = requests.get(url, headers=hdr, params={"context": "edit", "_fields": "content"}, timeout=20)
        if r.status_code != 200:
            return False, f"Couldn't read homepage (HTTP {r.status_code}): {r.text[:300]}"
        content = r.json().get("content", {})
        raw = content.get("raw") or content.get("rendered") or ""
    except Exception as e:
        return False, friendly_error(e)

    if enable:
        if start_marker in raw:
            return True, "Already enabled."
        new_content = f"{start_marker}\n{pattern.get('content', '')}\n{end_marker}\n{raw}"
        msg_ok = "Added to the top of your homepage."
    else:
        if start_marker not in raw:
            return True, "Already disabled."
        block_re = re.compile(re.escape(start_marker) + r".*?" + re.escape(end_marker) + r"\n?", re.S)
        new_content = block_re.sub("", raw)
        msg_ok = "Removed from your homepage."

    if is_dry_run:
        return True, f"🟡 Sandbox preview — {msg_ok}"
    try:
        wr = requests.post(url, headers={**hdr, "Content-Type": "application/json"},
                            json={"content": new_content}, timeout=30)
        if wr.status_code == 200:
            return True, msg_ok
        return False, f"HTTP {wr.status_code}: {wr.text[:300]}"
    except Exception as e:
        return False, friendly_error(e)

def apply_content_fix_now(post_ids, mode, auth, target_domain, extra_instructions="", is_dry_run=True):
    """Runs a real fix immediately (not a navigate-and-click-run detour) for
    a batch of post IDs. mode: 'image' | 'meta' | 'rewrite'.
    On success (not dry-run), also updates st.session_state.posts in place —
    otherwise re-running a check would just re-analyze the same stale cached
    data and look like nothing happened."""
    results = []
    posts_by_id = {p["id"]: p for p in st.session_state.posts}
    for pid in post_ids:
        post = posts_by_id.get(pid)
        if not post:
            continue
        title = post["title"]["rendered"]
        res = {"id": pid, "title": title, "status": "ok", "detail": ""}
        try:
            if mode == "image":
                raw = run_ai(f"Write a 2-sentence photorealistic image prompt for '{title}'. Raw text only.",
                              provider, ai_key, ai_model, 0.1,
                              enable_fallback=enable_fallback, fallback_keys=fallback_keys)
                img_prompt = " ".join(raw.replace("*","").replace('"','').split())[:800]
                seo_alt = run_ai(f"SEO image alt text under 120 chars for '{title}'. No quotes.",
                                  provider, ai_key, ai_model, 0.1,
                                  enable_fallback=enable_fallback, fallback_keys=fallback_keys).replace('"','')
                use_dalle = image_provider == "DALL-E 3" and bool(dalle_key or ai_key)
                img_bytes = gen_image_dalle(img_prompt, dalle_key or ai_key, dalle_style) if use_dalle else gen_image_pollinations(img_prompt)
                if is_dry_run:
                    res["detail"] = "Preview only — Sandbox mode is ON"
                else:
                    media_id = upload_wp_image(img_bytes, title, seo_alt, auth, target_domain, optimize_seo_img)
                    wp_update_post(pid, {"featured_media": media_id}, auth, target_domain)
                    post["featured_media"] = media_id
                    res["detail"] = "Image generated & attached"
            elif mode == "meta":
                plain = BeautifulSoup(post["content"]["rendered"], "html.parser").get_text()
                seo = generate_seo_meta(title, plain, provider, ai_key, ai_model, enable_fallback, fallback_keys)
                if is_dry_run:
                    res["detail"] = f"Preview: {seo.get('meta_description','')[:80]}"
                else:
                    wp_update_post(pid, {"excerpt": seo.get("excerpt","")}, auth, target_domain)
                    update_yoast_meta(pid, seo.get("meta_description",""), seo.get("focus_keyword",""), auth, target_domain)
                    if "excerpt" in post: post["excerpt"]["rendered"] = seo.get("excerpt","")
                    res["detail"] = "Meta description & focus keyword updated"
            elif mode == "rewrite":
                sys_p = ("You are a strict WordPress HTML editor. "
                         "Return ONLY fixed HTML — no markdown, no commentary.")
                p = f"Title: {title}\nInstructions: {extra_instructions}\nHTML:\n{post['content']['rendered'][:12000]}"
                fixed_html = run_ai(p, provider, ai_key, ai_model, system=sys_p,
                                     enable_fallback=enable_fallback, fallback_keys=fallback_keys
                                     ).replace("```html","").replace("```","").strip()
                if is_dry_run:
                    res["detail"] = f"Preview: {len(fixed_html.split())} words generated"
                else:
                    wp_update_post(pid, {"content": fixed_html}, auth, target_domain)
                    post["content"]["rendered"] = fixed_html
                    post["modified"] = datetime.utcnow().isoformat()
                    res["detail"] = "Content rewritten & pushed"
        except Exception as e:
            res["status"] = "error"; res["detail"] = friendly_error(e)
        results.append(res)
    return results

def fix_image_dimensions_now(posts, auth, target_domain, is_dry_run=True, max_images_per_post=15):
    """Real fix for layout-shift (CLS): finds <img> tags missing width/height,
    fetches each image to read its real pixel size, and writes the attributes
    back into the post content. This is what actually stops content jumping
    around as images load — not just a recommendation."""
    if PILImage is None:
        return [{"id": None, "title": "—", "status": "error",
                  "detail": "Pillow isn't installed. Run: python -m pip install Pillow"}]
    results = []
    for post in posts:
        pid, title = post["id"], post["title"]["rendered"]
        html = post.get("content", {}).get("rendered", "")
        soup = BeautifulSoup(html, "html.parser")
        imgs = [i for i in soup.find_all("img") if not (i.get("width") and i.get("height"))][:max_images_per_post]
        if not imgs:
            results.append({"id": pid, "title": title, "status": "ok", "detail": "No images needed fixing"})
            continue
        fixed_count = 0
        for img in imgs:
            src = img.get("src")
            if not src:
                continue
            try:
                r = requests.get(src, timeout=15, headers={"User-Agent": "Mozilla/5.0"}, stream=True)
                data = r.raw.read(3_000_000, decode_content=True)
                im = PILImage.open(io.BytesIO(data))
                w, h = im.size
                img["width"] = str(w)
                img["height"] = str(h)
                fixed_count += 1
            except Exception:
                continue
        if fixed_count == 0:
            results.append({"id": pid, "title": title, "status": "ok", "detail": "Couldn't read any image dimensions (unreachable images)"})
        elif is_dry_run:
            results.append({"id": pid, "title": title, "status": "ok",
                             "detail": f"Preview: would add dimensions to {fixed_count} image(s)"})
        else:
            try:
                wp_update_post(pid, {"content": str(soup)}, auth, target_domain)
                post["content"]["rendered"] = str(soup)
                results.append({"id": pid, "title": title, "status": "ok",
                                 "detail": f"Added width/height to {fixed_count} image(s)"})
            except Exception as e:
                results.append({"id": pid, "title": title, "status": "error", "detail": friendly_error(e)})
    return results

def build_and_publish_post(topic, domain, auth, *, language="English",
                            tone="Informative & SEO-optimized", word_count=800,
                            wp_status="draft", date_iso=None, do_image=True, do_seo=True,
                            do_schema=True, auto_category=True, manual_category_id=None,
                            tag_ids=None, is_dry_run=True, progress_cb=None):
    """Writes one AI post and (unless dry-run) publishes it to WordPress via the
    real REST API — the single code path used by both the Create Posts tab and
    the Agent's create_post tool, so neither one can drift out of sync."""
    def _log(msg):
        if progress_cb: progress_cb(msg)

    result = {"topic": topic, "ok": False, "post_id": None, "link": None,
              "meta_desc": "", "focus_kw": "", "excerpt": "", "content_html": "",
              "category_name": None, "category_id": None, "image_alt": "",
              "image_bytes": None, "wp_status": wp_status, "date_iso": date_iso, "error": None}
    try:
        _log("✍️ Writing content...")
        sys_c = ("You are an expert SEO content writer and WordPress editor. "
                 "Write well-structured HTML using h2, h3, p, ul, strong tags. "
                 "No html/head/body/title tags. No markdown fences. Raw HTML only.")
        p_c = (f"Blog post about: {topic}\nLanguage: {language}\nTone: {tone}\n"
               f"~{word_count} words. Include intro, subheadings, tips, CTA.\nReturn HTML body only.")
        post_html = run_ai(p_c, provider, ai_key, ai_model, 0.6, sys_c,
                           enable_fallback, fallback_keys).replace("```html", "").replace("```", "").strip()

        meta_desc = focus_kw = exc_text = ""
        if do_seo:
            _log("🔍 Generating SEO meta...")
            plain = BeautifulSoup(post_html, "html.parser").get_text()
            seo = generate_seo_meta(topic, plain, provider, ai_key, ai_model, enable_fallback, fallback_keys)
            meta_desc = seo.get("meta_description", "")
            focus_kw  = seo.get("focus_keyword", "")
            exc_text  = seo.get("excerpt", "")
        result["meta_desc"], result["focus_kw"], result["excerpt"] = meta_desc, focus_kw, exc_text

        if do_schema:
            tag = ('<script type="application/ld+json">'
                   + generate_schema_jsonld(topic, f"https://{domain}/",
                                            (date_iso or datetime.utcnow().isoformat()),
                                            meta_desc or exc_text)
                   + '</script>')
            post_html = tag + "\n" + post_html
        result["content_html"] = post_html

        img_bytes, seo_alt = None, ""
        if do_image:
            _log("🎨 Generating featured image...")
            raw = run_ai(f"2-sentence photorealistic image prompt for '{topic}'. Raw text only.",
                         provider, ai_key, ai_model, 0.1,
                         enable_fallback=enable_fallback, fallback_keys=fallback_keys)
            ipr = " ".join(raw.replace("*", "").replace('"', "").split())[:800]
            seo_alt = run_ai(f"SEO image alt text under 120 chars for '{topic}'. No quotes.",
                             provider, ai_key, ai_model, 0.1,
                             enable_fallback=enable_fallback, fallback_keys=fallback_keys).replace('"', "")
            for attempt in range(3):
                try:
                    use_dalle = image_provider == "DALL-E 3" and bool(dalle_key or ai_key)
                    img_bytes = gen_image_dalle(ipr, dalle_key or ai_key, dalle_style) if use_dalle else gen_image_pollinations(ipr)
                    break
                except Exception as ie:
                    if attempt == 2:
                        result["error"] = f"Image failed: {ie}"
                    else:
                        time.sleep(3)
        result["image_alt"], result["image_bytes"] = seo_alt, img_bytes

        if is_dry_run:
            result["ok"] = True
            return result

        media_id = None
        if img_bytes:
            try:
                media_id = upload_wp_image(img_bytes, topic, seo_alt, auth, domain, optimize_seo_img)
            except Exception as ue:
                result["error"] = f"Upload failed: {ue}"

        pl = {"title": topic, "content": post_html, "status": wp_status, "excerpt": exc_text}
        if media_id: pl["featured_media"] = media_id
        if date_iso: pl["date"] = date_iso

        resolved_cat = None
        if auto_category:
            wp_cats = fetch_wp_categories(auth, domain)
            if wp_cats:
                plain_txt = BeautifulSoup(post_html, "html.parser").get_text()
                resolved_cat = ai_pick_category(topic, plain_txt, wp_cats, provider, ai_key, ai_model,
                                                enable_fallback, fallback_keys)
                if resolved_cat:
                    result["category_name"] = next((n for n, cid in wp_cats.items() if cid == resolved_cat), "?")
        elif manual_category_id:
            resolved_cat = manual_category_id
        if resolved_cat:
            pl["categories"] = [resolved_cat]
            result["category_id"] = resolved_cat
        if tag_ids:
            pl["tags"] = tag_ids

        r = wp_create_post(pl, auth, domain)
        if r and r.status_code == 201:
            new_id, new_link = r.json().get("id"), r.json().get("link", "")
            if do_seo and meta_desc:
                update_yoast_meta(new_id, meta_desc, focus_kw, auth, domain)
            result.update(ok=True, post_id=new_id, link=new_link)
        else:
            result["error"] = f"HTTP {r.status_code if r else 'no response'}"
    except Exception as e:
        result["error"] = friendly_error(e)
    return result

# ════════════════════════════════════════════════════════════
#  SITE HEALTH & PERFORMANCE ANALYZER
# ════════════════════════════════════════════════════════════
def _check_ssl_cert(hostname, port=443):
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((hostname, port), timeout=8) as sock:
            with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
        exp = datetime.strptime(cert['notAfter'], "%b %d %H:%M:%S %Y %Z")
        days_left = (exp - datetime.utcnow()).days
        return True, days_left
    except Exception:
        return False, None

def run_site_health_check(target_domain):
    """Runs technical, on-page SEO and performance checks against the live
    homepage and returns a list of result dicts: id/label/status/detail/
    recommendation/fix_tab."""
    checks = []
    base = f"https://{target_domain}"

    ssl_ok, days_left = _check_ssl_cert(target_domain)
    if ssl_ok:
        status = "pass" if (days_left or 0) > 14 else "warn"
        checks.append({"id":"ssl","label":"SSL certificate","status":status,
            "detail": f"Valid, expires in {days_left} days" if days_left is not None else "Valid",
            "recommendation":"No action needed." if status=="pass" else "Renew soon — certificates expiring within 2 weeks can break HTTPS.",
            "fix_tab": None})
    else:
        checks.append({"id":"ssl","label":"SSL certificate","status":"fail",
            "detail":"Could not establish a valid HTTPS connection.",
            "recommendation":"Install/renew an SSL certificate (e.g. via Let's Encrypt or your host) — HTTPS is required for SEO and visitor trust.",
            "fix_tab": None})

    html_text, headers_resp, load_ms, page_bytes = "", {}, None, 0
    try:
        t0 = time.time()
        r = requests.get(base, timeout=15, headers={"User-Agent":"Mozilla/5.0 (WP-Pro-Ultra HealthCheck)"})
        load_ms = int((time.time() - t0) * 1000)
        html_text, headers_resp = r.text, r.headers
        page_bytes = len(r.content)
    except Exception as e:
        checks.append({"id":"reachability","label":"Homepage reachability","status":"fail",
            "detail":f"Could not load {base}: {e}",
            "recommendation":"Check that the domain is correct and the server is online.",
            "fix_tab": None})
        return checks

    if load_ms is not None:
        status = "pass" if load_ms < 800 else ("warn" if load_ms < 2000 else "fail")
        checks.append({"id":"speed","label":"Homepage response time","status":status,
            "detail":f"{load_ms} ms",
            "recommendation":"Good speed." if status=="pass" else "Add a caching plugin (WP Rocket / W3 Total Cache), compress images, and consider a CDN or faster host.",
            "fix_tab": None})

    kb = round(page_bytes/1024, 1)
    status = "pass" if kb < 700 else ("warn" if kb < 1500 else "fail")
    checks.append({"id":"weight","label":"HTML page size","status":status,
        "detail":f"{kb} KB",
        "recommendation":"Good." if status=="pass" else "Trim unused plugins/scripts and enable minification (HTML/CSS/JS).",
        "fix_tab": None})

    enc = headers_resp.get("Content-Encoding","")
    status = "pass" if enc in ("gzip","br") else "warn"
    checks.append({"id":"compression","label":"GZIP / Brotli compression","status":status,
        "detail": enc if enc else "Not detected",
        "recommendation":"Enabled." if status=="pass" else "Enable GZIP/Brotli compression on your server or via a caching plugin.",
        "fix_tab": None})

    soup = BeautifulSoup(html_text, "html.parser")

    title_tag = soup.find("title")
    tlen = len(title_tag.get_text().strip()) if title_tag else 0
    status = "pass" if 10 <= tlen <= 60 else ("warn" if tlen else "fail")
    checks.append({"id":"title","label":"Homepage <title> tag","status":status,
        "detail": f"{tlen} characters" if tlen else "Missing",
        "recommendation":"Good length." if status=="pass" else "Aim for a 10-60 character, keyword-rich title tag.",
        "fix_tab": None})

    md = soup.find("meta", attrs={"name":"description"})
    mlen = len(md.get("content","").strip()) if md and md.get("content") else 0
    status = "pass" if 50 <= mlen <= 160 else ("warn" if mlen else "fail")
    checks.append({"id":"metadesc","label":"Homepage meta description","status":status,
        "detail": f"{mlen} characters" if mlen else "Missing",
        "recommendation":"Good length." if status=="pass" else "Add/adjust a 50-160 character meta description via Yoast/RankMath.",
        "fix_tab": None})

    vp = soup.find("meta", attrs={"name":"viewport"})
    checks.append({"id":"viewport","label":"Mobile viewport tag","status":"pass" if vp else "fail",
        "detail":"Present" if vp else "Missing",
        "recommendation":"Good." if vp else "Add a responsive <meta name='viewport'> tag via your theme — required for mobile SEO.",
        "fix_tab": None})

    h1s = soup.find_all("h1")
    status = "pass" if len(h1s)==1 else "warn"
    checks.append({"id":"h1","label":"Single H1 heading","status":status,
        "detail": f"{len(h1s)} found",
        "recommendation":"Good." if status=="pass" else "Use exactly one H1 per page for clear content hierarchy.",
        "fix_tab": None})

    imgs = soup.find_all("img")
    missing_alt = [i for i in imgs if not (i.get("alt") or "").strip()]
    status = "pass" if not missing_alt else ("warn" if len(missing_alt) <= 3 else "fail")
    checks.append({"id":"alt","label":"Homepage images with alt text","status":status,
        "detail": f"{len(missing_alt)}/{len(imgs)} missing alt text" if imgs else "No images found",
        "recommendation":"Good." if status=="pass" else "Add descriptive alt text to every image for accessibility and image SEO.",
        "fix_tab": "images" if missing_alt else None})

    try:
        rr = requests.get(f"{base}/robots.txt", timeout=8)
        blocks_all = "Disallow: /" in rr.text and "User-agent: *" in rr.text
        checks.append({"id":"robots","label":"robots.txt","status":"fail" if (rr.status_code!=200 or blocks_all) else "pass",
            "detail":"Blocking all crawlers!" if blocks_all else (f"HTTP {rr.status_code}" if rr.status_code!=200 else "Present & OK"),
            "recommendation":"Fix robots.txt — it's currently blocking search engines." if blocks_all else ("Add a robots.txt file." if rr.status_code!=200 else "No action needed."),
            "fix_tab": None})
    except Exception:
        checks.append({"id":"robots","label":"robots.txt","status":"warn","detail":"Could not fetch",
            "recommendation":"Verify robots.txt is reachable.","fix_tab": None})

    try:
        sr = requests.get(f"{base}/sitemap.xml", timeout=8)
        ok = sr.status_code == 200
        checks.append({"id":"sitemap","label":"XML sitemap","status":"pass" if ok else "warn",
            "detail":"Found" if ok else "Not found at /sitemap.xml",
            "recommendation":"Good." if ok else "Enable a sitemap via Yoast/RankMath and submit it to Google Search Console.",
            "fix_tab": None})
    except Exception:
        checks.append({"id":"sitemap","label":"XML sitemap","status":"warn","detail":"Could not fetch",
            "recommendation":"Verify sitemap.xml is reachable.","fix_tab": None})

    return checks

def analyze_content_health(posts, min_words=200):
    """Content-level issues this app can actually fix, with post IDs to
    pre-select for the relevant tab."""
    issues = []
    if not posts:
        return issues
    no_img = [p for p in posts if not p.get("featured_media")]
    thin   = [p for p in posts
              if len(BeautifulSoup(p.get("content",{}).get("rendered",""),"html.parser").get_text().split()) < min_words]

    n = len(posts)
    issues.append({"id":"c_img","label":"Posts missing a featured image",
        "status":"pass" if not no_img else ("warn" if len(no_img) < n*0.2 else "fail"),
        "detail": f"{len(no_img)} of {n} posts", "count": len(no_img),
        "recommendation":"Good coverage." if not no_img else "Generate & attach AI featured images to these posts.",
        "fix_tab": "images" if no_img else None, "select_ids":[p["id"] for p in no_img],
        "fix_mode": "image" if no_img else None})

    issues.append({"id":"c_thin","label":f"Thin content (under {min_words} words)",
        "status":"pass" if not thin else ("warn" if len(thin) < n*0.2 else "fail"),
        "detail": f"{len(thin)} of {n} posts", "count": len(thin),
        "recommendation":"Good." if not thin else "Expand these posts, or run the optimizer with rewrite instructions.",
        "fix_tab": "optimize" if thin else None, "select_ids":[p["id"] for p in thin],
        "fix_mode": "rewrite" if thin else None,
        "fix_instructions": "Expand this post with more useful detail, examples, and depth. Keep the same topic and tone, but grow it well past the current length."})

    return issues

# ════════════════════════════════════════════════════════════
#  SECURITY CHECKS  (plain HTTP — no WP login required)
# ════════════════════════════════════════════════════════════
def run_security_check(target_domain):
    checks = []
    base = f"https://{target_domain}"
    try:
        r = requests.get(base, timeout=15, headers={"User-Agent":"Mozilla/5.0 (WP-Pro-Ultra SecurityScan)"})
        h = r.headers
    except Exception as e:
        return [{"id":"sec_reach","label":"Security scan","status":"fail","detail":f"Could not reach site: {e}",
                  "recommendation":"Check the domain is correct and reachable.","fix_tab":None}]

    def hdr_check(cid, label, header_name, good_hint, missing_hint):
        present = header_name.lower() in {k.lower() for k in h.keys()}
        checks.append({"id":cid,"label":label,"status":"pass" if present else "warn",
            "detail":"Present" if present else "Missing",
            "recommendation": good_hint if present else missing_hint, "fix_tab": None,
            "fix_group": "headers" if not present else None})

    hdr_check("hsts","Strict-Transport-Security (HSTS)","Strict-Transport-Security",
              "Good — forces HTTPS on repeat visits.",
              "Add HSTS via your host or a security plugin (e.g. Really Simple SSL) to force HTTPS.")
    hdr_check("xfo","Clickjacking protection (X-Frame-Options / CSP)","X-Frame-Options",
              "Good.", "Add X-Frame-Options or a CSP frame-ancestors directive to prevent clickjacking.")
    hdr_check("csp","Content-Security-Policy","Content-Security-Policy",
              "Good.", "Consider a Content-Security-Policy header — reduces XSS risk. Optional but recommended.")
    hdr_check("xcto","X-Content-Type-Options","X-Content-Type-Options",
              "Good.", "Add 'X-Content-Type-Options: nosniff' to stop MIME-sniffing attacks.")
    hdr_check("refpol","Referrer-Policy","Referrer-Policy",
              "Good.", "Add a Referrer-Policy header to control what's leaked to external links.")

    # XML-RPC exposure
    try:
        xr = requests.get(f"{base}/xmlrpc.php", timeout=10)
        exposed = xr.status_code == 200 and "XML-RPC server accepts POST requests only" in xr.text
        checks.append({"id":"xmlrpc","label":"XML-RPC exposure","status":"fail" if exposed else "pass",
            "detail":"Publicly reachable" if exposed else "Not exposed / blocked",
            "recommendation":"Disable or block xmlrpc.php (via a security plugin or .htaccess) — it's a common brute-force and DDoS amplification target." if exposed else "Good.",
            "fix_tab": None, "fix_plugin_slug": "disable-xml-rpc" if exposed else None,
            "fix_plugin_label": "Install & activate 'Disable XML-RPC'"})
    except Exception:
        checks.append({"id":"xmlrpc","label":"XML-RPC exposure","status":"warn","detail":"Could not check",
            "recommendation":"Verify manually.","fix_tab":None})

    # Directory listing
    try:
        dl = requests.get(f"{base}/wp-content/uploads/", timeout=10)
        listing = "Index of /" in dl.text
        checks.append({"id":"dirlist","label":"Directory listing on /wp-content/uploads/","status":"fail" if listing else "pass",
            "detail":"Enabled — file list is public!" if listing else "Disabled",
            "recommendation":"Disable directory listing (Options -Indexes in .htaccess, or your host's config)." if listing else "Good.",
            "fix_tab": None})
    except Exception:
        checks.append({"id":"dirlist","label":"Directory listing","status":"warn","detail":"Could not check",
            "recommendation":"Verify manually.","fix_tab":None})

    # WordPress version leak
    try:
        soup = BeautifulSoup(r.text, "html.parser")
        gen = soup.find("meta", attrs={"name":"generator"})
        leaked = gen and "wordpress" in (gen.get("content","").lower())
        checks.append({"id":"verleak","label":"WordPress version disclosure","status":"warn" if leaked else "pass",
            "detail":gen.get("content","") if leaked else "Not disclosed in homepage meta tag",
            "recommendation":"Remove the generator meta tag (most SEO plugins have this option) so attackers can't target known version-specific exploits." if leaked else "Good.",
            "fix_tab": None})
    except Exception:
        pass

    # Admin/author enumeration
    try:
        ae = requests.get(f"{base}/?author=1", timeout=10, allow_redirects=False,
                          headers={"User-Agent":"Mozilla/5.0"})
        loc = ae.headers.get("Location","")
        enum_possible = "/author/" in loc
        checks.append({"id":"authenum","label":"Author/username enumeration","status":"warn" if enum_possible else "pass",
            "detail":f"Reveals: {loc.rstrip('/').split('/')[-1]}" if enum_possible else "Not exposed",
            "recommendation":"Block author enumeration (?author=1 style URLs) with a security plugin — it helps attackers guess valid usernames for login attacks." if enum_possible else "Good.",
            "fix_tab": None})
    except Exception:
        pass

    return checks

# ════════════════════════════════════════════════════════════
#  SITE-WIDE SEO CRAWL  (crawls multiple live post URLs, not just homepage)
# ════════════════════════════════════════════════════════════
def _fetch_page_seo(url):
    out = {"url":url, "ok":False, "title":"", "meta_desc":"", "canonical":"",
           "has_og":False, "h1_count":0, "internal_links":[], "broken_sample":[], "error":""}
    try:
        r = requests.get(url, timeout=15, headers={"User-Agent":"Mozilla/5.0 (WP-Pro-Ultra SEOCrawl)"})
        out["ok"] = r.status_code == 200
        if not out["ok"]:
            out["error"] = f"HTTP {r.status_code}"
            return out
        soup = BeautifulSoup(r.text, "html.parser")
        t = soup.find("title")
        out["title"] = t.get_text().strip() if t else ""
        md = soup.find("meta", attrs={"name":"description"})
        out["meta_desc"] = (md.get("content","").strip() if md else "")
        cn = soup.find("link", attrs={"rel":"canonical"})
        out["canonical"] = cn.get("href","") if cn else ""
        out["has_og"] = bool(soup.find("meta", attrs={"property":"og:title"}))
        out["h1_count"] = len(soup.find_all("h1"))
        domain_netloc = urllib.parse.urlparse(url).netloc
        links = set()
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith("#") or href.startswith("mailto:") or href.startswith("tel:"): continue
            full = urllib.parse.urljoin(url, href)
            if urllib.parse.urlparse(full).netloc == domain_netloc:
                links.add(full.split("#")[0])
        out["internal_links"] = list(links)[:40]
    except Exception as e:
        out["error"] = str(e)[:100]
    return out

def crawl_site_seo(posts, max_pages=20, workers=6):
    """Crawls up to max_pages live post URLs concurrently and returns
    per-page results plus aggregate issue summaries."""
    targets = [p["link"] for p in posts if p.get("link")][:max_pages]
    pages = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(_fetch_page_seo, u): u for u in targets}
        for fut in as_completed(futures):
            pages.append(fut.result())

    ok_pages = [p for p in pages if p["ok"]]
    broken   = [p for p in pages if not p["ok"]]
    title_map, desc_map = {}, {}
    for p in ok_pages:
        title_map.setdefault(p["title"].lower(), []).append(p["url"])
        if p["meta_desc"]:
            desc_map.setdefault(p["meta_desc"].lower(), []).append(p["url"])
    dup_titles = {k:v for k,v in title_map.items() if len(v) > 1 and k}
    dup_descs  = {k:v for k,v in desc_map.items() if len(v) > 1 and k}
    missing_desc = [p for p in ok_pages if not p["meta_desc"]]
    missing_canon = [p for p in ok_pages if not p["canonical"]]
    missing_og  = [p for p in ok_pages if not p["has_og"]]
    bad_h1      = [p for p in ok_pages if p["h1_count"] != 1]

    all_linked = set()
    for p in ok_pages: all_linked.update(p["internal_links"])
    crawled_urls = {p["url"] for p in ok_pages}
    orphans_in_sample = [u for u in crawled_urls if u not in all_linked]
    link_to_id = {p["link"]: p["id"] for p in posts if p.get("link")}

    issues = [
        {"id":"crawl_broken","label":"Broken / unreachable pages","status":"pass" if not broken else "fail",
         "detail": f"{len(broken)} of {len(pages)} crawled", "items":[p["url"] for p in broken],
         "recommendation":"Good." if not broken else "Fix or redirect these URLs — broken pages hurt SEO and user trust."},
        {"id":"crawl_dup_title","label":"Duplicate page titles","status":"pass" if not dup_titles else "warn",
         "detail": f"{len(dup_titles)} duplicate title groups", "items":dup_titles,
         "recommendation":"Good." if not dup_titles else "Give each page a unique, descriptive <title>."},
        {"id":"crawl_dup_desc","label":"Duplicate meta descriptions","status":"pass" if not dup_descs else "warn",
         "detail": f"{len(dup_descs)} duplicate description groups", "items":dup_descs,
         "recommendation":"Good." if not dup_descs else "Write a unique meta description per page (use the SEO tab's batch tool)."},
        {"id":"crawl_missing_desc","label":"Pages missing a meta description","status":"pass" if not missing_desc else "warn",
         "detail": f"{len(missing_desc)} of {len(ok_pages)} pages", "items":[p["url"] for p in missing_desc],
         "recommendation":"Good." if not missing_desc else "Run the SEO batch tool on these posts.",
         "fix_tab":"seo" if missing_desc else None,
         "select_ids":[link_to_id[p["url"]] for p in missing_desc if p["url"] in link_to_id],
         "fix_mode": "meta" if missing_desc else None,
         "count": len([p for p in missing_desc if p["url"] in link_to_id])},
        {"id":"crawl_missing_canon","label":"Pages missing a canonical tag","status":"pass" if not missing_canon else "warn",
         "detail": f"{len(missing_canon)} of {len(ok_pages)} pages", "items":[p["url"] for p in missing_canon],
         "recommendation":"Good." if not missing_canon else "Most SEO plugins add this automatically — verify the plugin is active on these pages."},
        {"id":"crawl_missing_og","label":"Pages missing Open Graph tags","status":"pass" if not missing_og else "warn",
         "detail": f"{len(missing_og)} of {len(ok_pages)} pages", "items":[p["url"] for p in missing_og],
         "recommendation":"Good." if not missing_og else "Add Open Graph tags (via Yoast/RankMath) for better social-share previews."},
        {"id":"crawl_h1","label":"Pages with 0 or 2+ H1 tags","status":"pass" if not bad_h1 else "warn",
         "detail": f"{len(bad_h1)} of {len(ok_pages)} pages", "items":[p["url"] for p in bad_h1],
         "recommendation":"Good." if not bad_h1 else "Use exactly one H1 per page."},
        {"id":"crawl_orphan","label":"Possible orphan pages (within crawled sample)","status":"pass" if not orphans_in_sample else "warn",
         "detail": f"{len(orphans_in_sample)} of {len(ok_pages)} pages not linked from any other crawled page", "items":orphans_in_sample,
         "recommendation":"Good." if not orphans_in_sample else "Add internal links to these pages — orphan pages are harder for search engines to find. Note: this only checks links within the crawled sample, not the whole site."},
    ]
    return {"pages": pages, "issues": issues}

# ════════════════════════════════════════════════════════════
#  CORE WEB VITALS  (Google PageSpeed Insights API)
# ════════════════════════════════════════════════════════════
def check_core_web_vitals(target_domain, api_key="", strategy="mobile"):
    url = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
    params = {"url": f"https://{target_domain}", "strategy": strategy, "category": "performance"}
    if api_key: params["key"] = api_key
    try:
        r = requests.get(url, params=params, timeout=45)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        return {"error": friendly_error(e)}

    audits = data.get("lighthouseResult", {}).get("audits", {})
    perf_score = data.get("lighthouseResult", {}).get("categories", {}).get("performance", {}).get("score")
    def metric(key):
        a = audits.get(key, {})
        return a.get("displayValue", "—"), a.get("score")

    lcp_val, lcp_score = metric("largest-contentful-paint")
    cls_val, cls_score = metric("cumulative-layout-shift")
    tbt_val, tbt_score = metric("total-blocking-time")
    fcp_val, fcp_score = metric("first-contentful-paint")

    def status_of(score):
        if score is None: return "warn"
        return "pass" if score >= 0.9 else ("warn" if score >= 0.5 else "fail")

    return {
        "error": None,
        "overall_score": round(perf_score*100) if perf_score is not None else None,
        "metrics": [
            {"id":"lcp","label":"Largest Contentful Paint (loading)","status":status_of(lcp_score),"detail":lcp_val,
             "recommendation":"Good." if status_of(lcp_score)=="pass" else "Compress images, use a caching plugin, and consider a CDN to speed up the largest visible element."},
            {"id":"cls","label":"Cumulative Layout Shift (visual stability)","status":status_of(cls_score),"detail":cls_val,
             "recommendation":"Good." if status_of(cls_score)=="pass" else "Set explicit width/height on images and ads to stop content jumping around while loading."},
            {"id":"tbt","label":"Total Blocking Time (interactivity)","status":status_of(tbt_score),"detail":tbt_val,
             "recommendation":"Good." if status_of(tbt_score)=="pass" else "Reduce/defer JavaScript — disable unused plugins or use an asset-optimization plugin."},
            {"id":"fcp","label":"First Contentful Paint","status":status_of(fcp_score),"detail":fcp_val,
             "recommendation":"Good." if status_of(fcp_score)=="pass" else "Enable server-side caching and a CDN to serve the first paint faster."},
        ]
    }

# ════════════════════════════════════════════════════════════
#  CONTENT QUALITY AT SCALE  (readability, duplicates, staleness)
# ════════════════════════════════════════════════════════════
def _flesch_reading_ease(text):
    words = text.split()
    n_words = len(words)
    if n_words == 0: return None
    sentences = max(1, text.count(".") + text.count("!") + text.count("?"))
    def count_syllables(word):
        word = word.lower().strip(".,!?;:\"'()")
        vowels = "aeiouy"
        cnt, prev_vowel = 0, False
        for ch in word:
            is_v = ch in vowels
            if is_v and not prev_vowel: cnt += 1
            prev_vowel = is_v
        if word.endswith("e") and cnt > 1: cnt -= 1
        return max(cnt, 1)
    n_syll = sum(count_syllables(w) for w in words)
    score = 206.835 - 1.015*(n_words/sentences) - 84.6*(n_syll/n_words)
    return round(score, 1)

def _jaccard_similarity(a_words, b_words):
    if not a_words or not b_words: return 0
    inter = len(a_words & b_words)
    union = len(a_words | b_words)
    return inter/union if union else 0

def analyze_content_quality_at_scale(posts, stale_days=180, similarity_threshold=0.55):
    if not posts:
        return []
    texts, word_sets = {}, {}
    for p in posts:
        plain = BeautifulSoup(p.get("content",{}).get("rendered",""), "html.parser").get_text()
        texts[p["id"]] = plain
        word_sets[p["id"]] = set(w.lower() for w in plain.split() if len(w) > 3)

    # Readability
    scores = {pid: _flesch_reading_ease(t) for pid, t in texts.items() if t.strip()}
    hard_to_read = [pid for pid, s in scores.items() if s is not None and s < 30]

    # Near-duplicate detection (O(n^2) — fine for the loaded batch sizes this app targets)
    ids = list(word_sets.keys())
    dup_pairs = []
    for i in range(len(ids)):
        for j in range(i+1, len(ids)):
            sim = _jaccard_similarity(word_sets[ids[i]], word_sets[ids[j]])
            if sim >= similarity_threshold:
                dup_pairs.append((ids[i], ids[j], round(sim*100)))

    # Staleness
    now = datetime.utcnow()
    stale = []
    for p in posts:
        mod = p.get("modified") or p.get("date")
        try:
            mod_dt = datetime.fromisoformat(mod.replace("Z",""))
            if (now - mod_dt).days > stale_days:
                stale.append(p["id"])
        except Exception:
            pass

    n = len(posts)
    id_title = {p["id"]: p["title"]["rendered"] for p in posts}
    issues = [
        {"id":"cq_read","label":"Hard-to-read posts (Flesch score < 30)","status":"pass" if not hard_to_read else ("warn" if len(hard_to_read)<n*0.2 else "fail"),
         "detail": f"{len(hard_to_read)} of {n} posts", "count": len(hard_to_read),
         "recommendation":"Good." if not hard_to_read else "Simplify sentence structure and vocabulary — run the optimizer with 'improve readability' instructions.",
         "fix_tab":"optimize" if hard_to_read else None, "select_ids": hard_to_read,
         "fix_mode": "rewrite" if hard_to_read else None,
         "fix_instructions":"Rewrite for a simpler, more conversational reading level. Shorter sentences, plainer words, more line breaks."},
        {"id":"cq_dup","label":"Near-duplicate content pairs","status":"pass" if not dup_pairs else "warn",
         "detail": f"{len(dup_pairs)} similar pairs found (≥{int(similarity_threshold*100)}% word overlap)",
         "count": len(dup_pairs),
         "recommendation":"Good." if not dup_pairs else "Differentiate or merge these posts to avoid keyword cannibalization.",
         "pairs":[(id_title.get(a,a), id_title.get(b,b), s) for a,b,s in dup_pairs[:15]]},
        {"id":"cq_stale","label":f"Stale content (not updated in {stale_days}+ days)","status":"pass" if not stale else ("warn" if len(stale)<n*0.3 else "fail"),
         "detail": f"{len(stale)} of {n} posts", "count": len(stale),
         "recommendation":"Good." if not stale else "Refresh these with current info — run the optimizer with 'update with current information' instructions.",
         "fix_tab":"optimize" if stale else None, "select_ids": stale,
         "fix_mode": "rewrite" if stale else None,
         "fix_instructions":"Update this post with current, up-to-date information. Refresh any outdated facts, statistics, or examples."},
    ]
    return issues

# ════════════════════════════════════════════════════════════
#  SCORE HISTORY  (per-domain, stored locally as JSON)
# ════════════════════════════════════════════════════════════
HISTORY_FILE = "wp_pro_health_history.json"

def load_health_history():
    try:
        with open(HISTORY_FILE) as f: return json.load(f)
    except Exception: return []

def save_health_snapshot(domain, scores):
    hist = load_health_history()
    hist.append({"domain": domain, "timestamp": datetime.utcnow().isoformat(), **scores})
    hist = hist[-200:]
    with open(HISTORY_FILE, "w") as f: json.dump(hist, f)
    return hist

# ════════════════════════════════════════════════════════════
#  PDF REPORT  (branded, for client delivery)
# ════════════════════════════════════════════════════════════
def generate_pdf_report(domain, agency_name, scores, all_issue_groups):
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(83, 74, 183)
    pdf.cell(0, 12, agency_name or "WP Pro Ultra", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(90, 90, 90)
    pdf.cell(0, 8, f"Site Health Report — {domain}", ln=True)
    pdf.cell(0, 8, f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", ln=True)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(20, 20, 20)
    pdf.cell(0, 10, "Score summary", ln=True)
    pdf.set_font("Helvetica", "", 11)
    for label, val in scores.items():
        pdf.set_text_color(50,50,50)
        pdf.cell(90, 8, label)
        color = (29,158,117) if (val or 0) >= 80 else ((212,160,18) if (val or 0) >= 50 else (216,90,48))
        pdf.set_text_color(*color)
        pdf.cell(0, 8, f"{val}%" if val is not None else "not scanned", ln=True)

    for group_title, issues in all_issue_groups:
        if not issues: continue
        pdf.ln(4)
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(20,20,20)
        pdf.cell(0, 10, group_title, ln=True)
        pdf.set_font("Helvetica", "", 10)
        for res in issues:
            status = res.get("status","warn")
            icon = {"pass":"[OK]","warn":"[!]","fail":"[X]"}.get(status,"[?]")
            color = {"pass":(29,158,117),"warn":(212,160,18),"fail":(216,90,48)}.get(status,(90,90,90))
            pdf.set_text_color(*color)
            pdf.multi_cell(0, 6, f"{icon} {res.get('label','')} — {res.get('detail','')}")
            pdf.set_text_color(90,90,90)
            rec = res.get("recommendation","")
            if rec:
                pdf.set_font("Helvetica","I",9)
                pdf.multi_cell(0, 5, f"   {rec}")
                pdf.set_font("Helvetica","",10)
            pdf.ln(1)

    return bytes(pdf.output(dest="S"))


for k, v in [("posts",[]),("selected",[]),("active_tab","dashboard"),
             ("run_log",[]),("created_log",[]),("health_results",None),
             ("health_content",None),("security_results",None),
             ("crawl_results",None),("cwv_results",None),
             ("content_quality_results",None),("prefill_fix_instructions",""),
             ("_fix_toast",None),("agent_plan",[]),
             ("design_logo_preview",None),("design_favicon_preview",None),
             ("design_media_page",1),("design_media_cache",None),
             ("design_palette_preview",None),("design_theme_info",None),
             ("design_global_styles",None),("design_wp_settings",None),
             ("design_patterns",None),("design_ticker_state",{}),
             ("design_cmd_image",None),("design_cmd_log",[]),("design_cmd_plan",[]),
             ("agent_bg_job",None)]:
    if k not in st.session_state: st.session_state[k] = v

# ════════════════════════════════════════════════════════════
#  AGENT TOOL-CALLING  (Stage 2) — a fixed, whitelisted registry of real
#  functions the connected LLM may plan against. It never writes or executes
#  code itself; it only proposes {tool, args} steps from this exact list,
#  which get shown to the user for confirmation before anything real runs.
# ════════════════════════════════════════════════════════════
# ── Master tool registry ────────────────────────────────────
# Every tool the AI Agent can call, across the whole app, tagged by domain
# so the plan UI and any future reporting can group them. This is the single
# source of truth for the general Agent tab. The Theme & Design tab's own
# command box uses DESIGN_TOOLS below instead — a filtered view containing
# only the "design" group — so it can never select anything outside that scope.
AGENT_TOOLS = {
    "load_posts": {"group": "content",
        "desc": "Fetch posts from WordPress into memory. Args: statuses (list of 'publish'/'draft'/'private', "
                "default ['publish']), max_count (int, 0 = all, default 0)."},
    "run_full_audit": {"group": "health",
        "desc": "Run the full site health audit — technical, security, performance, SEO crawl, content quality. No args."},
    "improve_website": {"group": "health",
        "desc": "Run the full site audit, then automatically apply whatever real fixes match what it finds — "
                "missing featured images, thin/stale content, missing SEO meta, missing image dimensions. "
                "This is the 'improve my website' one-shot tool. No args."},
    "fix_missing_images": {"group": "images",
        "desc": "Generate & upload AI featured images with SEO alt text for posts missing one. "
                "Args: max_count (int, 0 = all, default 0)."},
    "rewrite_thin_stale_content": {"group": "content",
        "desc": "AI-rewrite posts that are thin (under the quality-gate word count) or stale (not updated "
                "recently). Args: max_count (int, 0 = all, default 0), instructions (optional extra rewrite instructions)."},
    "fix_seo_meta": {"group": "seo",
        "desc": "Generate and push a meta description + focus keyword to Yoast/RankMath for posts missing one. "
                "Args: max_count (int, 0 = all, default 0)."},
    "fix_image_dimensions": {"group": "images",
        "desc": "Scan post images missing width/height attributes and write real pixel dimensions to fix "
                "layout shift (CLS). No args."},
    "install_caching_plugin": {"group": "health",
        "desc": "Install & activate a verified caching plugin (WP Super Cache) to speed up LCP/FCP. "
                "Requires Sandbox mode OFF. No args."},
    "harden_security": {"group": "health",
        "desc": "Install & activate verified security plugins (Disable XML-RPC, Really Simple Security). "
                "Requires Sandbox mode OFF. No args."},
    "generate_pdf_report": {"group": "health",
        "desc": "Build a branded PDF report from the most recent scan results. No args."},
    "create_post": {"group": "content",
        "desc": "Write and publish one new AI-generated blog post with SEO meta, a featured image, and schema.org "
                "markup. Args: topic (string, required), word_count (int, default 800), "
                "publish (bool, default false — false publishes as a draft for review)."},
    "create_posts_batch": {"group": "content",
        "desc": "Write and publish several AI-generated blog posts in one run. Args: topics (list of strings) "
                "— OR topic_theme (string) + topic_count (int) to have the AI brainstorm that many titles first "
                "— plus word_count (int, default 800) and publish (bool, default false)."},
    "set_site_title_tagline": {"group": "design",
        "desc": "Update the site title and/or tagline. Args: title (optional string), tagline (optional string)."},
    "set_site_logo": {"group": "design",
        "desc": "Set the site logo — uses the attached image if one was uploaded, otherwise generates one from "
                "a text description. Args: prompt (string describing the logo, only used if no image is attached)."},
    "set_site_icon": {"group": "design",
        "desc": "Set the site icon/favicon, auto-cropped to a 512x512 square — uses the attached image if one was "
                "uploaded, otherwise generates one from a text description. Args: prompt (string, only used if no "
                "image is attached)."},
    "apply_color_palette": {"group": "design",
        "desc": "Apply a color palette to the site's design. Args: preset (one of: " + ", ".join(PALETTE_PRESETS) +
                "), OR primary/secondary/accent/text (hex color strings, for a custom palette not matching a preset)."},
    "post_to_pinterest": {"group": "social",
        "desc": "Create a Pinterest Pin from a post's featured image. Args: post_id (int, required — must already "
                "be loaded). Requires a Pinterest access token + board ID configured in the sidebar."},
    "keyword_research": {"group": "seo",
        "desc": "Look up monthly search volume, competition, and CPC for a keyword or topic. Args: keyword "
                "(string, required). Requires a DataForSEO login/password configured in the sidebar."},
    "fetch_analytics_report": {"group": "analytics",
        "desc": "Pull a traffic summary (sessions, users, top pages) from Google Analytics 4 for the last N days. "
                "Args: days (int, default 28). Requires a GA4 property ID + access token configured in the sidebar."},
}

# A separate, deliberately narrow registry for the Theme & Design tab's own
# command box — it should only ever touch branding/identity/color, never
# posts, SEO, security, or caching. Passed to run_agent_planner instead of
# AGENT_TOOLS so the model can't select anything outside this scope.
DESIGN_TOOLS = {name: meta for name, meta in AGENT_TOOLS.items() if meta["group"] == "design"}

def run_agent_planner(user_request, context_summary, tools=None):
    """Asks the connected LLM to turn a free-text request into a short plan of
    steps drawn ONLY from the given tool registry (AGENT_TOOLS by default).
    Returns {"reply": str, "steps": [...]}. Any tool name the model invents
    that isn't in the registry is dropped — the model proposes, it never
    executes."""
    tools = tools or AGENT_TOOLS
    tools_desc = "\n".join(f"- {name}: {meta['desc']}" for name, meta in tools.items())
    system = (
        "You are the planning brain for a WordPress agency assistant. You never write or run code yourself — "
        "you only choose from this fixed list of whitelisted tools and respond with strict JSON, nothing else, "
        "no markdown fences, no commentary outside the JSON.\n\n"
        f"Available tools:\n{tools_desc}\n\n"
        "Respond with exactly this JSON shape:\n"
        '{"reply": "one short friendly sentence about the plan", '
        '"steps": [{"tool": "<tool name>", "args": {}, "why": "short reason"}]}\n\n'
        "Rules: use only tool names from the list above, at most 5 steps, only include args the tool actually "
        "accepts. If the request doesn't match any tool, return an empty steps list and explain why in reply."
    )
    prompt = f"Site context: {context_summary}\n\nUser request: {user_request}"
    try:
        raw = run_ai(prompt, provider, ai_key, ai_model, 0.2, system, enable_fallback, fallback_keys).strip()
    except Exception as e:
        return {"reply": f"I couldn't reach the AI provider to plan that: {friendly_error(e)}", "steps": []}
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"): raw = raw[4:]
    try:
        data = json.loads(raw)
    except Exception:
        return {"reply": "I couldn't build a clear plan from that — try rephrasing.", "steps": []}

    clean_steps = []
    for step in (data.get("steps") or [])[:5]:
        tool = step.get("tool")
        if tool not in tools:
            continue
        args = step.get("args") if isinstance(step.get("args"), dict) else {}
        clean_steps.append({"tool": tool, "args": args, "why": step.get("why", "")})
    return {"reply": data.get("reply") or "Here's what I'd do:", "steps": clean_steps}

def execute_agent_tool(tool, args, auth, domain, is_dry_run, uploaded_image=None):
    """Runs one whitelisted agent tool call for real, through the exact same
    wrapper functions as the dedicated tabs. Returns (ok: bool, message: str).
    uploaded_image is the raw bytes of a file the user attached to their
    free-text request, if any — only the *_image / *_logo / *_icon tools
    below consume it."""
    args = args or {}

    if tool == "load_posts":
        statuses = [s for s in (args.get("statuses") or ["publish"]) if s in ("publish", "draft", "private")] or ["publish"]
        posts = fetch_all_posts(auth, domain, statuses, int(args.get("max_count") or 0))
        st.session_state.posts = posts
        st.session_state.selected = [p["id"] for p in posts]
        return True, f"Loaded {len(posts)} post(s) from {domain}."

    if tool == "run_full_audit":
        try: st.session_state.health_results = run_site_health_check(domain)
        except Exception: pass
        try: st.session_state.security_results = run_security_check(domain)
        except Exception: pass
        st.session_state.cwv_results = check_core_web_vitals(domain, pagespeed_key)
        if st.session_state.posts:
            try: st.session_state.crawl_results = crawl_site_seo(st.session_state.posts, crawl_max_pages)
            except Exception: pass
            st.session_state.health_content = analyze_content_health(st.session_state.posts, gate_min_words)
            st.session_state.content_quality_results = analyze_content_quality_at_scale(st.session_state.posts, stale_days)
        return True, "Full audit complete — see the Site Health tab for details."

    if tool == "fix_missing_images":
        targets = [p["id"] for p in st.session_state.posts if not p.get("featured_media")]
        if args.get("max_count"): targets = targets[:int(args["max_count"])]
        if not targets: return True, "Every post already has a featured image."
        if not ai_key: return False, "I need an AI API key in the sidebar first."
        results = apply_content_fix_now(targets, "image", auth, domain, is_dry_run=is_dry_run)
        ok_n = sum(1 for r in results if r["status"] == "ok")
        if is_dry_run: return True, f"🟡 Sandbox preview — {ok_n} post(s) would get a new featured image."
        st.session_state.health_content = analyze_content_health(st.session_state.posts, gate_min_words)
        return True, f"Generated and attached images to {ok_n} post(s). ✅"

    if tool == "rewrite_thin_stale_content":
        thin = [p["id"] for p in st.session_state.posts
                if len(BeautifulSoup(p.get("content", {}).get("rendered", ""), "html.parser").get_text().split()) < gate_min_words]
        now, stale = datetime.utcnow(), []
        for p in st.session_state.posts:
            mod = p.get("modified") or p.get("date")
            try:
                if (now - datetime.fromisoformat(mod.replace("Z", ""))).days > stale_days:
                    stale.append(p["id"])
            except Exception:
                pass
        targets = list(set(thin + stale))
        if args.get("max_count"): targets = targets[:int(args["max_count"])]
        if not targets: return True, "Nothing thin or stale right now."
        if not ai_key: return False, "I need an AI API key in the sidebar first."
        instructions = args.get("instructions") or (
            "Expand thin sections with more useful detail, and refresh anything outdated with current "
            "information. Keep the same topic and tone.")
        results = apply_content_fix_now(targets, "rewrite", auth, domain,
                                        extra_instructions=instructions, is_dry_run=is_dry_run)
        ok_n = sum(1 for r in results if r["status"] == "ok")
        if is_dry_run: return True, f"🟡 Sandbox preview — {ok_n} post(s) would be rewritten."
        st.session_state.health_content = analyze_content_health(st.session_state.posts, gate_min_words)
        st.session_state.content_quality_results = analyze_content_quality_at_scale(st.session_state.posts, stale_days)
        return True, f"Improved {ok_n} post(s). ✅"

    if tool == "fix_seo_meta":
        targets = [p["id"] for p in st.session_state.posts if not p.get("excerpt", {}).get("rendered", "").strip()]
        if args.get("max_count"): targets = targets[:int(args["max_count"])]
        if not targets: return True, "Every loaded post already has a meta description."
        if not ai_key: return False, "I need an AI API key in the sidebar first."
        results = apply_content_fix_now(targets, "meta", auth, domain, is_dry_run=is_dry_run)
        ok_n = sum(1 for r in results if r["status"] == "ok")
        if is_dry_run: return True, f"🟡 Sandbox preview — {ok_n} post(s) would get new meta descriptions."
        return True, f"Wrote meta descriptions & focus keywords for {ok_n} post(s). ✅"

    if tool == "fix_image_dimensions":
        if not st.session_state.posts: return False, "Load posts first."
        results = fix_image_dimensions_now(st.session_state.posts, auth, domain, is_dry_run=is_dry_run)
        fixed = sum(1 for r in results if r["status"] == "ok" and "Preview" not in r["detail"] and "No images" not in r["detail"])
        if is_dry_run: return True, f"🟡 Sandbox preview — dimensions would be added on {fixed} post(s)."
        return True, f"Added missing image dimensions on {fixed} post(s). ✅"

    if tool == "install_caching_plugin":
        if is_dry_run: return False, "Sandbox mode is on — turn it off to install a plugin (can't be previewed)."
        ok, msg = wp_install_plugin("wp-super-cache", auth, domain)
        return ok, msg + (" Finish in WP Admin → Settings → WP Super Cache → Easy tab → 'Caching On'." if ok else "")

    if tool == "harden_security":
        if is_dry_run: return False, "Sandbox mode is on — turn it off to install plugins (can't be previewed)."
        ok1, msg1 = wp_install_plugin("disable-xml-rpc", auth, domain)
        ok2, msg2 = wp_install_plugin("really-simple-ssl", auth, domain)
        return (ok1 and ok2), f"XML-RPC: {msg1}\nHeaders: {msg2} Finish the setup in WP Admin → Really Simple Security."

    if tool == "generate_pdf_report":
        has_any = any([st.session_state.health_results, st.session_state.security_results,
                       st.session_state.crawl_results, st.session_state.content_quality_results])
        if not has_any: return False, "No scan results yet — run the audit first."
        def score(issues):
            if not issues: return None
            return round(sum(1 for r in issues if r["status"] == "pass") / len(issues) * 100)
        scores = {
            "Technical": score(st.session_state.health_results),
            "Security": score(st.session_state.security_results),
            "SEO": score((st.session_state.crawl_results or {}).get("issues")) if st.session_state.crawl_results else None,
            "Content": score(st.session_state.content_quality_results),
            "Performance": st.session_state.cwv_results.get("overall_score")
                if st.session_state.cwv_results and not st.session_state.cwv_results.get("error") else None,
        }
        groups = [
            ("Technical & Performance", st.session_state.health_results or []),
            ("Security", st.session_state.security_results or []),
            ("Site-wide SEO Crawl", (st.session_state.crawl_results or {}).get("issues", [])),
            ("Content Quality", st.session_state.content_quality_results or []),
            ("Content Health", st.session_state.health_content or []),
        ]
        st.session_state["_agent_pdf"] = generate_pdf_report(domain, agency_name, scores, groups)
        return True, "Your report's ready — download it below. 📄"

    if tool == "create_post":
        topic = (args.get("topic") or "").strip()
        if not topic: return False, "I need a topic to write about."
        if not ai_key: return False, "I need an AI API key in the sidebar first."
        word_count = int(args.get("word_count") or 800)
        publish = bool(args.get("publish"))
        r = build_and_publish_post(topic, domain, auth, word_count=word_count,
                                   wp_status=("publish" if publish else "draft"), is_dry_run=is_dry_run)
        if is_dry_run:
            return True, f"🟡 Sandbox preview — would create '{topic}' ({word_count} words, {'publish' if publish else 'draft'})."
        if r["ok"]:
            return True, f"Created post #{r['post_id']} — {r['link']} ✅"
        return False, f"Couldn't create the post: {r['error']}"

    if tool == "create_posts_batch":
        if not ai_key: return False, "I need an AI API key in the sidebar first."
        topics = args.get("topics")
        if isinstance(topics, str):
            topics = [t.strip() for t in topics.split(",") if t.strip()]
        if not topics:
            theme = (args.get("topic_theme") or "").strip()
            count = int(args.get("topic_count") or 0)
            if not theme or not count:
                return False, "Give me either a list of topics, or a theme plus how many to write."
            count = min(count, 20)
            try:
                raw = run_ai(f"Give me {count} distinct, specific blog post title ideas about: {theme}. "
                             f"Reply with exactly {count} lines, one title per line, no numbering, no extra text.",
                             provider, ai_key, ai_model, 0.7, "You are a content strategist.",
                             enable_fallback, fallback_keys)
                topics = [t.strip("-•* ").strip() for t in raw.strip().split("\n") if t.strip()][:count]
            except Exception as e:
                return False, f"Couldn't generate topic ideas: {friendly_error(e)}"
        if not topics:
            return False, "No topics to write about."
        word_count = int(args.get("word_count") or 800)
        publish = bool(args.get("publish"))
        if is_dry_run:
            return True, f"🟡 Sandbox preview — would create {len(topics)} post(s): " + "; ".join(topics)
        lines, ok_n = [], 0
        for topic in topics:
            r = build_and_publish_post(topic, domain, auth, word_count=word_count,
                                       wp_status=("publish" if publish else "draft"), is_dry_run=is_dry_run)
            if r["ok"]:
                ok_n += 1
                lines.append(f"#{r['post_id']} {topic} — {r['link']}")
            else:
                lines.append(f"❌ {topic}: {r['error']}")
        return True, f"Created {ok_n}/{len(topics)} post(s):\n" + "\n".join(f"- {l}" for l in lines)

    if tool == "improve_website":
        if not st.session_state.posts:
            ok, msg = execute_agent_tool("load_posts", {}, auth, domain, is_dry_run)
            if not ok: return False, msg
        _, audit_msg = execute_agent_tool("run_full_audit", {}, auth, domain, is_dry_run)
        report = [f"🩺 Audit — {audit_msg}"]
        for sub_tool in ("fix_missing_images", "fix_seo_meta", "fix_image_dimensions", "rewrite_thin_stale_content"):
            ok, msg = execute_agent_tool(sub_tool, {}, auth, domain, is_dry_run)
            report.append(f"{'✅' if ok else '⚠️'} {sub_tool} — {msg}")
        return True, "Ran a full improvement pass:\n\n" + "\n".join(f"- {r}" for r in report)

    if tool == "post_to_pinterest":
        post_id = args.get("post_id")
        post = next((p for p in st.session_state.posts if p["id"] == post_id), None) if post_id else None
        if not post:
            return False, "I need a post_id from your loaded posts to pin — load posts first."
        image_url = (post.get("_embedded", {}).get("wp:featuredmedia", [{}])[0] or {}).get("source_url")
        if not image_url:
            return False, "That post has no featured image to pin."
        title = BeautifulSoup(post.get("title", {}).get("rendered", ""), "html.parser").get_text()
        desc = BeautifulSoup(post.get("excerpt", {}).get("rendered", ""), "html.parser").get_text()
        link = post.get("link", f"https://{domain}/")
        if is_dry_run:
            return True, f"🟡 Sandbox preview — would pin '{title}' to your Pinterest board."
        return post_to_pinterest(image_url, title, desc or title, link,
                                 st.session_state.get("cfg_pinterest_board_id", ""),
                                 st.session_state.get("cfg_pinterest_token", ""))

    if tool == "keyword_research":
        keyword = (args.get("keyword") or "").strip()
        if not keyword:
            return False, "Tell me which keyword or topic to look up."
        ok, data = keyword_research_dataforseo(keyword, st.session_state.get("cfg_dataforseo_login", ""),
                                               st.session_state.get("cfg_dataforseo_password", ""))
        if not ok: return False, data
        trend = ", ".join(str(v) for v in data["monthly_trend"]) if data.get("monthly_trend") else "n/a"
        return True, (f"**{data['keyword']}** — {data['search_volume']:,} searches/mo" if data.get("search_volume") is not None
                      else f"**{data['keyword']}**") + \
                     f"\ncompetition: {data.get('competition')}, CPC: ${data.get('cpc')}\nrecent trend: {trend}"

    if tool == "fetch_analytics_report":
        days = int(args.get("days") or 28)
        ok, data = fetch_ga4_report(st.session_state.get("cfg_ga4_property_id", ""),
                                    st.session_state.get("cfg_ga4_access_token", ""), days)
        if not ok: return False, data
        lines = [f"Last {data['days']} days — {data.get('total_sessions','?')} sessions, "
                 f"{data.get('total_users','?')} users, {data.get('total_views','?')} views."]
        for pg in data.get("top_pages", [])[:5]:
            lines.append(f"  {pg['path']} — {pg['sessions']} sessions")
        return True, "\n".join(lines)

    if tool == "set_site_title_tagline":
        title, tagline = args.get("title"), args.get("tagline")
        if not title and not tagline:
            return False, "Tell me the new site title and/or tagline."
        fields = {}
        if title: fields["title"] = title
        if tagline: fields["description"] = tagline
        if is_dry_run:
            return True, f"🟡 Sandbox preview — would set {fields}."
        ok, msg = update_wp_settings(fields, auth, domain)
        return ok, (f"Updated {fields}. ✅" if ok else msg)

    if tool in ("set_site_logo", "set_site_icon"):
        img_bytes = uploaded_image
        if img_bytes is None:
            prompt_text = (args.get("prompt") or "").strip()
            if not prompt_text:
                return False, "No image was attached and no description was given — attach an image or describe what you want."
            if not ai_key:
                return False, "I need an AI API key in the sidebar to generate an image."
            try:
                _use_dalle = image_provider == "DALL-E 3" and bool(dalle_key or ai_key)
                img_bytes = gen_image_dalle(prompt_text, dalle_key or ai_key, dalle_style) if _use_dalle else gen_image_pollinations(prompt_text)
            except Exception as e:
                return False, f"Image generation failed: {friendly_error(e)}"

        if tool == "set_site_icon":
            if is_dry_run:
                return True, "🟡 Sandbox preview — would crop this image to 512×512 and set it as your site icon."
            try:
                square = crop_square(img_bytes, 512)
                media_id = upload_wp_image(square, "Site Icon", "Site icon", auth, domain, True)
            except Exception as e:
                return False, str(e) if isinstance(e, ModuleNotFoundError) else f"Upload failed: {friendly_error(e)}"
            ok, msg = update_wp_settings({"site_icon": media_id}, auth, domain)
            return ok, (f"Site icon set (media ID {media_id}). ✅" if ok else msg)

        if is_dry_run:
            return True, "🟡 Sandbox preview — would upload this image and use it as your site logo."
        try:
            media_id = upload_wp_image(img_bytes, "Site Logo", "Site logo", auth, domain, True)
        except Exception as e:
            return False, f"Upload failed: {friendly_error(e)}"
        return True, (
            f"Uploaded (media ID {media_id}). WordPress doesn't expose the site logo through the core REST API "
            f"the way it does the site icon, so finish it in one click: **Appearance → Editor → Styles → Site "
            f"Identity** and pick the image you just uploaded."
        )

    if tool == "apply_color_palette":
        preset = (args.get("preset") or "").strip()
        if preset in PALETTE_PRESETS:
            palette = PALETTE_PRESETS[preset]
        else:
            required = ("primary", "secondary", "accent", "text")
            if all(args.get(k) for k in required):
                palette = {k: args[k] for k in required}
            else:
                return False, f"Tell me a preset name ({', '.join(PALETTE_PRESETS)}) or all four hex colors (primary/secondary/accent/text)."
        if is_dry_run:
            return True, f"🟡 Sandbox preview — would apply this palette to your site's Global Styles: {palette}"
        theme_info, terr = fetch_active_theme_info(auth, domain)
        snippet = build_style_variation_snippet(palette)
        if not theme_info:
            return False, (f"Couldn't detect your active theme ({terr}). Here's a copy-paste snippet instead:\n"
                           f"```json\n{snippet}\n```\nSave it as `style-variation.json` in your theme's /styles/ folder.")
        ok, msg = apply_global_styles_colors(palette, auth, domain, theme_info)
        if not ok:
            return False, (f"{msg} Here's a copy-paste snippet instead:\n```json\n{snippet}\n```\n"
                           f"Save it as `style-variation.json` in your theme's /styles/ folder.")
        return True, msg

    return False, f"Unknown tool: {tool}"

def _agent_plan_worker(job, steps, auth, domain, is_dry_run):
    """Runs an approved plan step-by-step on a background thread so a long
    job (batch content creation, a full audit + fixes, ...) doesn't freeze the
    UI. `job` is the same dict object living in st.session_state.agent_bg_job
    — the thread was given script-run context via add_script_run_ctx, which
    is Streamlit's documented way to let a background thread touch
    st.session_state safely. There's no push-based UI update: results appear
    the next time you interact with the app (or hit the Refresh button),
    which is why the UI is honest about that instead of promising live
    push updates Streamlit can't actually do."""
    for i, step in enumerate(steps):
        try:
            ok, msg = execute_agent_tool(step["tool"], step["args"], auth, domain, is_dry_run)
        except Exception as e:
            ok, msg = False, friendly_error(e)
        job["log"].append({"tool": step["tool"], "ok": ok, "msg": msg})
        job["done_n"] = i + 1
    job["status"] = "done"

# ════════════════════════════════════════════════════════════
#  SIDEBAR
# ════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""
    <div style='padding:16px 16px 8px;border-bottom:1px solid rgba(127,119,221,0.1);margin-bottom:6px'>
      <div style='font-size:11px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--text-muted)'>⚙️ Settings</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("YOU")
    _settings = load_settings()
    if "cfg_your_name" not in st.session_state:
        st.session_state["cfg_your_name"] = _settings.get("your_name", "")
    your_name = st.text_input("Your name", key="cfg_your_name", label_visibility="collapsed",
                               placeholder="Your name (for the agent's greeting)")
    if your_name != _settings.get("your_name", ""):
        save_settings({**_settings, "your_name": your_name})

    st.markdown("SAVED SITES")
    _profiles = load_profiles()
    _profile_names = list(_profiles.keys())
    _sel = st.selectbox("Load saved site", ["— New / manual —"] + _profile_names,
                        key="profile_selector", label_visibility="collapsed")
    if _sel != "— New / manual —" and st.session_state.get("_last_loaded_profile") != _sel:
        p = _profiles[_sel]
        for src_key, widget_key in [("domain","cfg_domain"), ("wp_user","cfg_wp_user"),
                                     ("wp_pw","cfg_wp_pw"), ("provider","cfg_provider"),
                                     ("ai_key","cfg_ai_key"), ("dalle_key","cfg_dalle_key"),
                                     ("pagespeed_key","cfg_pagespeed_key"),
                                     ("agency_name","cfg_agency_name")]:
            if p.get(src_key) is not None:
                st.session_state[widget_key] = p[src_key]
        for fb in ["claude","openai","mistral","gemini"]:
            fbv = p.get("fallback_keys", {}).get(fb)
            if fbv: st.session_state[f"fb_{fb}"] = fbv
        st.session_state["_last_loaded_profile"] = _sel
        st.rerun()
    if _sel == "— New / manual —":
        st.session_state["_last_loaded_profile"] = None

    st.markdown("SITE")
    domain  = st.text_input("Domain", key="cfg_domain", label_visibility="collapsed", placeholder="yourdomain.com")
    wp_user = st.text_input("Username", key="cfg_wp_user", label_visibility="collapsed", placeholder="WP username")
    wp_pw   = st.text_input("App Password", type="password", key="cfg_wp_pw", label_visibility="collapsed", placeholder="WP App Password")

    with st.expander("💾 Save / manage this site"):
        _default_name = domain or (_sel if _sel != "— New / manual —" else "")
        _save_name = st.text_input("Profile name", value=_default_name, placeholder="e.g. client-acme-com")
        sc1, sc2 = st.columns(2)
        with sc1:
            if st.button("💾 Save", use_container_width=True, disabled=not _save_name.strip()):
                save_profile(_save_name.strip(), {
                    "domain": domain, "wp_user": wp_user, "wp_pw": wp_pw,
                    "provider": st.session_state.get("cfg_provider","Claude"),
                    "ai_key": st.session_state.get("cfg_ai_key",""),
                    "dalle_key": st.session_state.get("cfg_dalle_key",""),
                    "pagespeed_key": st.session_state.get("cfg_pagespeed_key",""),
                    "agency_name": st.session_state.get("cfg_agency_name",""),
                    "fallback_keys": {fb: st.session_state.get(f"fb_{fb}","") for fb in
                                       ["claude","openai","mistral","gemini"]},
                })
                st.session_state["_last_loaded_profile"] = _save_name.strip()
                st.success(f"Saved '{_save_name.strip()}'")
                st.rerun()
        with sc2:
            if st.button("🗑️ Delete", use_container_width=True, disabled=_sel=="— New / manual —"):
                delete_profile(_sel)
                st.session_state["_last_loaded_profile"] = None
                st.success("Deleted.")
                st.rerun()
        st.caption(f"Saved locally in `{PROFILES_FILE}` in this folder, in plain text — this is your own PC only, but don't share this folder or upload it anywhere.")

    st.markdown("AI ENGINE")
    provider = st.selectbox("Provider", ["Claude","OpenAI","Mistral","Gemini"], key="cfg_provider", label_visibility="collapsed")
    ai_key   = st.text_input("API Key", type="password", key="cfg_ai_key", label_visibility="collapsed", placeholder=f"{provider} API Key")
    ai_model_opts = {
        "Claude":  ["claude-sonnet-4-20250514","claude-opus-4-20250514"],
        "OpenAI":  ["gpt-4o","gpt-4o-mini"],
        "Mistral": ["mistral-large-latest","mistral-small-latest"],
        "Gemini":  ["gemini-1.5-pro","gemini-1.5-flash"],
    }
    ai_model        = st.selectbox("Model", ai_model_opts[provider], label_visibility="collapsed")
    enable_fallback = st.toggle("Auto-fallback chain", value=True)
    fallback_keys   = {}
    if enable_fallback:
        with st.expander("Fallback keys"):
            for fb in ["claude","openai","mistral","gemini"]:
                fallback_keys[fb] = st.text_input(f"{fb.capitalize()} key", type="password",
                                   key=f"fb_{fb}", label_visibility="collapsed",
                                   placeholder=f"{fb.capitalize()} fallback key")
    else:
        for fb in ["claude","openai","mistral","gemini"]:
            fallback_keys[fb] = st.session_state.get(f"fb_{fb}","")

    st.markdown("IMAGES")
    generate_images  = st.toggle("Generate featured images", value=True)
    image_provider   = st.selectbox("Image provider", ["Pollinations (free)","DALL-E 3"], label_visibility="collapsed")
    dalle_key  = ""
    dalle_style = "vivid"
    if image_provider == "DALL-E 3":
        dalle_key   = st.text_input("OpenAI key for DALL-E", type="password",
                                    key="cfg_dalle_key", label_visibility="collapsed", placeholder="OpenAI key for images")
        dalle_style = st.selectbox("Style", ["vivid","natural"], label_visibility="collapsed")
    optimize_seo_img = st.toggle("Inject image SEO metadata", value=True)

    st.markdown("SEO")
    seo_meta_desc = st.toggle("Meta description + focus KW", value=True)
    seo_schema    = st.toggle("Schema.org JSON-LD", value=True)
    seo_excerpt   = st.toggle("Rewrite excerpt", value=True)
    seo_fix_slug  = st.toggle("Fix date-based slugs", value=False)

    st.markdown("QUALITY GATE")
    enable_gate    = st.toggle("Enable quality gate", value=True)
    gate_min_words = st.number_input("Min words", min_value=50, value=200, step=50, label_visibility="collapsed")
    gate_auto_skip = st.toggle("Skip posts failing gate", value=True)

    st.markdown("SCHEDULING")
    enable_schedule   = st.toggle("⏰ Smart 24h scheduling", value=True,
                                  help="Spreads posts evenly across 24 hours. WordPress schedules future posts automatically.")
    posts_per_day     = st.number_input("Posts per day target", min_value=1, max_value=500,
                                         value=150, step=10, label_visibility="collapsed",
                                         help="Used to calculate the interval between posts.")
    schedule_start_h  = st.slider("Start hour (UTC)", 0, 23, 6,
                                   label_visibility="collapsed",
                                   help="Hour at which the first post of the day is published (UTC).")
    start_from_now    = st.toggle("Start from now (not midnight)", value=False,
                                  help="If ON, first post goes out immediately and the rest follow at calculated intervals.")
    delay_between_api = st.slider("Delay between API calls (sec)", 1, 60, 5,
                                   label_visibility="collapsed",
                                   help="Pause between each WordPress REST API call to avoid server overload.")

    _interval_min = round(1440 / max(posts_per_day, 1), 1)
    if enable_schedule:
        st.caption(f"📅 1 post every **{_interval_min} min** · start at **{schedule_start_h:02d}:00 UTC**")

    st.markdown("REPORTING & AUDIT")
    agency_name    = st.text_input("Agency / brand name (for PDF reports)", key="cfg_agency_name",
                                    label_visibility="collapsed",
                                    placeholder="Your Agency Name")
    pagespeed_key  = st.text_input("Google PageSpeed API key (optional)", type="password",
                                    key="cfg_pagespeed_key",
                                    label_visibility="collapsed",
                                    placeholder="Optional — improves rate limits",
                                    help="Free key from Google Cloud Console. Works without one at low volume.")
    crawl_max_pages = st.number_input("Max pages for SEO crawl", min_value=5, max_value=200,
                                       value=20, step=5, label_visibility="collapsed",
                                       help="How many live post URLs to crawl for the site-wide SEO scan.")
    stale_days     = st.number_input("Flag content stale after (days)", min_value=30, max_value=1095,
                                      value=180, step=30, label_visibility="collapsed")

    st.markdown("GROWTH & DATA APIs")
    with st.expander("📌 Pinterest, 🔑 keyword research, 📊 analytics (all optional)"):
        st.caption("Paste your own key/token for each — same pattern as the PageSpeed key above. "
                    "Nothing here is faked; leave any of these blank and that tool just says it isn't configured.")
        pinterest_token = st.text_input("Pinterest access token", type="password", key="cfg_pinterest_token",
                                        placeholder="From Pinterest Developers → your app → Generate token")
        pinterest_board_id = st.text_input("Pinterest board ID", key="cfg_pinterest_board_id",
                                           placeholder="Found in the board's URL")
        st.markdown("—")
        dataforseo_login = st.text_input("DataForSEO login", key="cfg_dataforseo_login",
                                         placeholder="dataforseo.com account login")
        dataforseo_password = st.text_input("DataForSEO password", type="password", key="cfg_dataforseo_password",
                                            placeholder="dataforseo.com account password")
        st.markdown("—")
        ga4_property_id = st.text_input("GA4 property ID", key="cfg_ga4_property_id",
                                        placeholder="e.g. 123456789")
        ga4_access_token = st.text_input("GA4 access token", type="password", key="cfg_ga4_access_token",
                                         placeholder="OAuth token — expires ~1hr, from OAuth Playground",
                                         help="Google Analytics tokens expire quickly. Generate a fresh one at "
                                              "developers.google.com/oauthplayground with the analytics.readonly scope.")

    st.markdown("RUN")
    post_status   = st.multiselect("Post status", ["publish","draft","private"],
                                   default=["publish"], label_visibility="collapsed")
    max_posts_in  = st.number_input("Max posts (0=all)", min_value=0, value=0, step=10, label_visibility="collapsed")
    workers       = st.slider("Workers", 1, 8, 3, label_visibility="collapsed")
    update_status = st.selectbox("After fix", ["keep original","publish","draft"], label_visibility="collapsed")
    dry_run       = st.toggle("Sandbox mode", value=True)
    resume_mode   = st.toggle("Resume from last run", value=True)

    st.markdown("---")
    posts_loaded = len(st.session_state.posts)
    no_img_count = sum(1 for p in st.session_state.posts if not p.get("featured_media"))
    sched_dot = "warn" if enable_schedule else "off"
    st.markdown(f"""
    <div class='conn-pill'><div class='conn-dot {"" if (domain and wp_user and wp_pw) else "off"}'></div>
      {domain or "not connected"}</div>
    <div class='conn-pill'><div class='conn-dot'></div>
      {provider} · {ai_model.split("-")[0] if "-" in ai_model else ai_model}</div>
    <div class='conn-pill'><div class='conn-dot{"" if posts_loaded else " off"}'></div>
      {posts_loaded} posts · {no_img_count} missing img</div>
    <div class='conn-pill'><div class='conn-dot {sched_dot}'></div>
      {"⏰ Scheduling ON · " + str(_interval_min) + " min interval" if enable_schedule else "Scheduling OFF"}</div>
    """, unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
#  TOP HEADER BAR — brand, live status, theme toggle
# ════════════════════════════════════════════════════════════
_hdr_l, _hdr_r = st.columns([5,1])
with _hdr_l:
    _connected = bool(domain and wp_user and wp_pw)
    st.markdown(f"""
    <div style='display:flex;align-items:center;gap:12px;padding:16px 24px 4px'>
      <div style='width:36px;height:36px;border-radius:10px;
          background:linear-gradient(135deg,#7F77DD,#534AB7);
          display:flex;align-items:center;justify-content:center;font-size:17px;
          box-shadow:0 4px 14px rgba(127,119,221,0.35)'>⚡</div>
      <div style='flex:1'>
        <div style='font-size:16px;font-weight:700;color:var(--text-primary);line-height:1.1'>WP Pro Ultra</div>
        <div style='font-size:11px;color:var(--text-muted)'>AI Content &amp; Site Optimization Studio</div>
      </div>
      <div style='display:flex;align-items:center;gap:6px;font-size:11.5px;color:var(--text-muted);
          background:rgba(var(--surface-rgb),var(--surface-a3));border:1px solid rgba(127,119,221,0.15);
          border-radius:999px;padding:5px 12px'>
        <div style='width:7px;height:7px;border-radius:50%;
            background:{"#1D9E75" if _connected else "#444"};
            box-shadow:{"0 0 6px rgba(29,158,117,0.5)" if _connected else "none"}'></div>
        {domain if _connected else "not connected"}
      </div>
    </div>
    """, unsafe_allow_html=True)
with _hdr_r:
    st.markdown("<div style='padding:20px 24px 0'></div>", unsafe_allow_html=True)
    _is_light = st.session_state.theme == "light"
    if st.button("☀️ Light" if not _is_light else "🌙 Dark", key="theme_toggle", use_container_width=True):
        st.session_state.theme = "light" if not _is_light else "dark"
        st.rerun()

# ════════════════════════════════════════════════════════════
#  TAB NAVIGATION  (single source of navigation — no duplicate buttons)
# ════════════════════════════════════════════════════════════
TABS = [
    ("dashboard", "🤖 Agent"),
    ("health",    "🩺 Site Health"),
    ("scan",      "📡 Scan & select"),
    ("optimize",  "🔧 Optimize posts"),
    ("images",    "🖼️ Fix images"),
    ("create",    "✨ Create posts"),
    ("seo",       "🔍 SEO tools"),
    ("design",    "🎨 Theme & Design"),
]

tab_cols = st.columns(len(TABS))
for col, (tid, tlabel) in zip(tab_cols, TABS):
    with col:
        is_active = st.session_state.active_tab == tid
        if st.button(tlabel, key=f"tab_{tid}",
                     type="primary" if is_active else "secondary",
                     use_container_width=True):
            st.session_state.active_tab = tid
            st.rerun()

active = st.session_state.active_tab
st.markdown("---")

# ════════════════════════════════════════════════════════════
#  STAT CARDS HELPER
# ════════════════════════════════════════════════════════════
def render_stats():
    posts     = st.session_state.posts
    total     = len(posts)
    no_img    = sum(1 for p in posts if not p.get("featured_media"))
    optimized = total - no_img
    run_log   = st.session_state.run_log
    ok_count  = sum(1 for r in run_log if r.get("status") == "ok")

    st.markdown(f"""
    <div class='stats-grid'>
      <div class='stat-card purple'>
        <div class='stat-icon purple'>📄</div>
        <div class='stat-label'>Total posts</div>
        <div class='stat-val'>{total}</div>
        <div class='stat-delta good'>loaded from WordPress</div>
      </div>
      <div class='stat-card coral'>
        <div class='stat-icon coral'>🚫</div>
        <div class='stat-label'>Missing images</div>
        <div class='stat-val'>{no_img}</div>
        <div class='stat-delta {"warn" if no_img > 0 else "good"}'>
          {"needs attention" if no_img > 0 else "all covered ✓"}
        </div>
      </div>
      <div class='stat-card teal'>
        <div class='stat-icon teal'>✅</div>
        <div class='stat-label'>Have images</div>
        <div class='stat-val'>{optimized}</div>
        <div class='stat-delta good'>{round(optimized/total*100) if total else 0}% complete</div>
      </div>
      <div class='stat-card blue'>
        <div class='stat-icon blue'>🤖</div>
        <div class='stat-label'>AI optimized</div>
        <div class='stat-val'>{ok_count}</div>
        <div class='stat-delta good'>this session</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
#  DASHBOARD TAB
# ════════════════════════════════════════════════════════════
if active == "dashboard":
    _connected = bool(domain and wp_user and wp_pw)
    st.markdown(f"""
    <div class='agent-hero'>
      <div class='agent-orb'>⚡</div>
      <div class='agent-hero-body'>
        <div class='agent-hero-title'>
          WP Pro Ultra Agent
          <span class='agent-online-pill'><span class='agent-online-dot'></span>Online</span>
        </div>
        <div class='agent-hero-sub'>Greets you, checks your site, and runs the tools for you</div>
        <div class='agent-status-row'>
          <span class='agent-status-chip'>{"🔗 " + domain if _connected else "🔌 Not connected"}</span>
          <span class='agent-status-chip'>📄 {len(st.session_state.posts)} post(s) loaded</span>
          <span class='agent-status-chip'>{"🟡 Sandbox mode" if dry_run else "🔴 Live mode"}</span>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    if "agent_log" not in st.session_state: st.session_state.agent_log = []
    if "agent_step" not in st.session_state: st.session_state.agent_step = "start"

    def _agent_say(text):
        st.session_state.agent_log.append({"role": "assistant", "text": text})

    def _agent_user(text):
        st.session_state.agent_log.append({"role": "user", "text": text})

    def _agent_scores():
        def score(issues):
            if not issues: return None
            return round(sum(1 for r in issues if r["status"] == "pass") / len(issues) * 100)
        return {
            "Technical": score(st.session_state.health_results),
            "Security": score(st.session_state.security_results),
            "SEO": score((st.session_state.crawl_results or {}).get("issues")) if st.session_state.crawl_results else None,
            "Content": score(st.session_state.content_quality_results),
            "Performance": st.session_state.cwv_results.get("overall_score")
                if st.session_state.cwv_results and not st.session_state.cwv_results.get("error") else None,
        }

    def _agent_run_audit():
        with st.spinner("Running today's site check — technical, security, performance..."):
            try: st.session_state.health_results = run_site_health_check(domain)
            except Exception: pass
            try: st.session_state.security_results = run_security_check(domain)
            except Exception: pass
            st.session_state.cwv_results = check_core_web_vitals(domain, pagespeed_key)
            if st.session_state.posts:
                try: st.session_state.crawl_results = crawl_site_seo(st.session_state.posts, crawl_max_pages)
                except Exception: pass
                st.session_state.health_content = analyze_content_health(st.session_state.posts, gate_min_words)
                st.session_state.content_quality_results = analyze_content_quality_at_scale(
                    st.session_state.posts, stale_days)

        scores = _agent_scores()
        if domain:
            save_health_snapshot(domain, {
                "technical": scores["Technical"], "security": scores["Security"],
                "seo_crawl": scores["SEO"], "content_quality": scores["Content"],
                "performance": scores["Performance"]})

        issues_found = []
        no_img = sum(1 for p in st.session_state.posts if not p.get("featured_media"))
        if no_img: issues_found.append(f"{no_img} post(s) missing a featured image")
        if st.session_state.health_content:
            for r in st.session_state.health_content:
                if r["status"] != "pass" and r["id"] == "c_thin":
                    issues_found.append(f"{r['detail']} are thin content")
        if st.session_state.content_quality_results:
            for r in st.session_state.content_quality_results:
                if r["status"] != "pass" and r["id"] == "cq_stale":
                    issues_found.append(f"{r['detail']} are stale")
        if st.session_state.cwv_results and not st.session_state.cwv_results.get("error"):
            for m in st.session_state.cwv_results.get("metrics", []):
                if m["status"] != "pass":
                    issues_found.append(f"{m['label']} needs work ({m['detail']})")
        if st.session_state.security_results:
            fails = [r for r in st.session_state.security_results if r["status"] == "fail"]
            if fails: issues_found.append(f"{len(fails)} security issue(s) need attention")

        score_line = " · ".join(f"{k} {v}%" for k, v in scores.items() if v is not None)
        text = f"Here's what I found — {score_line if score_line else 'not everything could be scanned yet'}.\n\n"
        if issues_found:
            text += "A few things worth doing:\n" + "\n".join(f"- {i}" for i in issues_found[:6])
        else:
            text += "Nothing urgent — looking good! 🎉"
        if not st.session_state.posts:
            text += "\n\n(I couldn't check your content yet — load your posts first for the full picture.)"
        return text

    def _run_agent_action(action_id):
        auth = make_auth(wp_user, wp_pw) if (wp_user and wp_pw) else None
        if action_id == "load_posts":
            if not (domain and wp_user and wp_pw):
                _agent_say("I need your domain, username and app password filled in first.")
                return
            with st.spinner("Loading your posts..."):
                posts = fetch_all_posts(auth, domain, post_status, int(max_posts_in))
            st.session_state.posts = posts
            st.session_state.selected = [p["id"] for p in posts]
            _agent_say(f"Loaded {len(posts)} post(s) from {domain}. ✅")

        elif action_id == "fix_images":
            no_img = [p["id"] for p in st.session_state.posts if not p.get("featured_media")]
            if not no_img:
                _agent_say("Every post already has a featured image — nothing to do here. 🎉")
            elif not ai_key:
                _agent_say("I need an AI API key in the sidebar to generate images.")
            else:
                with st.spinner(f"Generating images for {len(no_img)} post(s)..."):
                    results = apply_content_fix_now(no_img, "image", auth, domain, is_dry_run=dry_run)
                ok_n = sum(1 for r in results if r["status"] == "ok")
                if dry_run:
                    _agent_say(f"🟡 Sandbox preview — {ok_n} post(s) would get a new featured image. Turn off Sandbox mode in the sidebar to push for real.")
                else:
                    st.session_state.health_content = analyze_content_health(st.session_state.posts, gate_min_words)
                    _agent_say(f"Done — generated and attached images to {ok_n} post(s). ✅")

        elif action_id == "fix_content":
            thin = [p["id"] for p in st.session_state.posts
                    if len(BeautifulSoup(p.get("content", {}).get("rendered", ""), "html.parser").get_text().split()) < gate_min_words]
            now = datetime.utcnow()
            stale = []
            for p in st.session_state.posts:
                mod = p.get("modified") or p.get("date")
                try:
                    if (now - datetime.fromisoformat(mod.replace("Z", ""))).days > stale_days:
                        stale.append(p["id"])
                except Exception:
                    pass
            targets = list(set(thin + stale))
            if not targets:
                _agent_say("Your content looks healthy — nothing thin or stale right now. 🎉")
            elif not ai_key:
                _agent_say("I need an AI API key in the sidebar to rewrite content.")
            else:
                with st.spinner(f"Improving {len(targets)} post(s)..."):
                    results = apply_content_fix_now(
                        targets, "rewrite", auth, domain,
                        extra_instructions="Expand thin sections with more useful detail, and refresh anything outdated with current information. Keep the same topic and tone.",
                        is_dry_run=dry_run)
                ok_n = sum(1 for r in results if r["status"] == "ok")
                if dry_run:
                    _agent_say(f"🟡 Sandbox preview — {ok_n} post(s) would be rewritten. Turn off Sandbox mode in the sidebar to push for real.")
                else:
                    st.session_state.health_content = analyze_content_health(st.session_state.posts, gate_min_words)
                    st.session_state.content_quality_results = analyze_content_quality_at_scale(st.session_state.posts, stale_days)
                    _agent_say(f"Done — improved {ok_n} post(s). ✅")

        elif action_id == "fix_seo":
            targets = [p["id"] for p in st.session_state.posts
                       if not p.get("excerpt", {}).get("rendered", "").strip()][:crawl_max_pages]
            if not targets:
                _agent_say("Every loaded post already has an excerpt/meta description set. 🎉")
            elif not ai_key:
                _agent_say("I need an AI API key in the sidebar to write SEO meta.")
            else:
                with st.spinner(f"Writing SEO meta for {len(targets)} post(s)..."):
                    results = apply_content_fix_now(targets, "meta", auth, domain, is_dry_run=dry_run)
                ok_n = sum(1 for r in results if r["status"] == "ok")
                if dry_run:
                    _agent_say(f"🟡 Sandbox preview — {ok_n} post(s) would get new meta descriptions. Turn off Sandbox mode in the sidebar to push for real.")
                else:
                    _agent_say(f"Done — wrote meta descriptions & focus keywords for {ok_n} post(s). ✅")

        elif action_id == "speed_up":
            if not (domain and wp_user and wp_pw):
                _agent_say("I need your WordPress login filled in first.")
            elif dry_run:
                _agent_say("Turn off Sandbox mode in the sidebar and ask me again — installing a plugin is a real, live change I won't preview.")
            else:
                with st.spinner("Installing a caching plugin..."):
                    ok, msg = wp_install_plugin("wp-super-cache", auth, domain)
                if ok:
                    _agent_say(f"{msg} One manual step left: WP Admin → Settings → WP Super Cache → 'Easy' tab → check 'Caching On'. I can't click that button for you, but the plugin's ready. ✅")
                else:
                    _agent_say(f"Couldn't install it automatically: {msg}")

        elif action_id == "harden":
            if not (domain and wp_user and wp_pw):
                _agent_say("I need your WordPress login filled in first.")
            elif dry_run:
                _agent_say("Turn off Sandbox mode in the sidebar and ask me again — installing plugins is a real, live change I won't preview.")
            else:
                with st.spinner("Installing security plugins..."):
                    ok1, msg1 = wp_install_plugin("disable-xml-rpc", auth, domain)
                    ok2, msg2 = wp_install_plugin("really-simple-ssl", auth, domain)
                lines = [
                    ("✅ XML-RPC: " + msg1) if ok1 else ("⚠️ XML-RPC: " + msg1),
                    ("✅ Security headers: " + msg2 + " Finish the 1-minute setup in WP Admin → Really Simple Security to actually enable them.") if ok2 else ("⚠️ Headers: " + msg2),
                ]
                _agent_say("\n\n".join(lines))

        elif action_id == "create_posts":
            _agent_say("Let's do that in the Create posts tab — I've opened it for you.")
            st.session_state.active_tab = "create"

        elif action_id == "pdf_report":
            has_any = any([st.session_state.health_results, st.session_state.security_results,
                           st.session_state.crawl_results, st.session_state.content_quality_results])
            if not has_any:
                _agent_say("I don't have any scan results yet — let's run the check first.")
            else:
                scores = _agent_scores()
                groups = [
                    ("Technical & Performance", st.session_state.health_results or []),
                    ("Security", st.session_state.security_results or []),
                    ("Site-wide SEO Crawl", (st.session_state.crawl_results or {}).get("issues", [])),
                    ("Content Quality", st.session_state.content_quality_results or []),
                    ("Content Health", st.session_state.health_content or []),
                ]
                try:
                    pdf_bytes = generate_pdf_report(domain, agency_name, scores, groups)
                    st.session_state["_agent_pdf"] = pdf_bytes
                    _agent_say("Your report's ready — download it below. 📄")
                except Exception as e:
                    _agent_say(f"Couldn't build the PDF: {e}")

        elif action_id == "rerun_check":
            _agent_say(_agent_run_audit())

    # ── Greeting (once per session) ─────────────────────────
    if st.session_state.agent_step == "start":
        _typing_slot = st.empty()
        with _typing_slot.container():
            with st.chat_message("assistant", avatar="⚡"):
                st.markdown("<div class='typing-dots'><span></span><span></span><span></span></div>", unsafe_allow_html=True)
        time.sleep(0.7)
        _typing_slot.empty()

        name = your_name.strip() or wp_user or "there"
        greeting = get_greeting(name)
        if not domain:
            _agent_say(f"{greeting} I'm not connected to a site yet — fill in your domain and WordPress credentials in the sidebar, then come back and I'll get to work. 👋")
            st.session_state.agent_step = "need_site"
        else:
            _agent_say(f"{greeting} I'm ready to work on **{domain}**. Want me to run today's site check?")
            st.session_state.agent_step = "offer_check"

    # ── Execute any pending action from the previous click ──
    _pending = st.session_state.pop("_agent_pending_action", None)
    if _pending:
        _run_agent_action(_pending)
        st.rerun()

    # ── Render the conversation ──────────────────────────────
    for msg in st.session_state.agent_log:
        with st.chat_message("assistant" if msg["role"] == "assistant" else "user",
                              avatar="⚡" if msg["role"] == "assistant" else None):
            st.markdown(msg["text"])

    if st.session_state.get("_agent_pdf"):
        st.download_button("⬇️ Download PDF report", data=st.session_state["_agent_pdf"],
                            file_name=f"{domain or 'site'}_health_report_{datetime.now().strftime('%Y%m%d')}.pdf",
                            mime="application/pdf")

    # ── Action area for the current step ─────────────────────
    if st.session_state.agent_step == "need_site" and domain:
        st.session_state.agent_step = "offer_check"
        st.rerun()

    elif st.session_state.agent_step == "offer_check":
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✅ Yes, run it", type="primary", use_container_width=True, key="agent_run_check"):
                _agent_user("Yes, run today's check.")
                st.session_state["_agent_pending_action"] = "rerun_check"
                st.session_state.agent_step = "menu"
                st.rerun()
        with c2:
            if st.button("⏭️ Skip, show me the menu", use_container_width=True, key="agent_skip_check"):
                _agent_user("Skip the check.")
                _agent_say("No problem — here's what I can help with:")
                st.session_state.agent_step = "menu"
                st.rerun()

    elif st.session_state.agent_step == "menu":
        st.markdown("<div style='padding:4px 0 10px;font-size:12px;color:var(--text-muted)'>What should I take care of?</div>",
                    unsafe_allow_html=True)
        posts_loaded = bool(st.session_state.posts)
        actions = [
            ("📡", "Load my posts", "load_posts", True),
            ("🖼️", "Fix missing images", "fix_images", posts_loaded),
            ("📝", "Fix thin & stale content", "fix_content", posts_loaded),
            ("🔍", "Improve SEO meta", "fix_seo", posts_loaded),
            ("⚡", "Speed up my site", "speed_up", True),
            ("🔒", "Harden security", "harden", True),
            ("✨", "Create new posts", "create_posts", True),
            ("📄", "Get a PDF report", "pdf_report", True),
            ("🔄", "Run the check again", "rerun_check", True),
        ]
        with st.container(key="agent_menu"):
            cols = st.columns(3)
            for i, (icon, label, action_id, enabled) in enumerate(actions):
                with cols[i % 3]:
                    if st.button(f"{icon} {label}", key=f"agent_act_{action_id}",
                                 use_container_width=True, disabled=not enabled):
                        _agent_user(label)
                        st.session_state["_agent_pending_action"] = action_id
                        st.rerun()
        if not posts_loaded:
            st.caption("Some actions need your posts loaded first — try 'Load my posts' to unlock them.")

    # ── Free-text tool-calling (Stage 2) ─────────────────────
    if st.session_state.agent_step in ("menu", "offer_check") and not st.session_state.agent_plan:
        st.markdown("<div style='padding-top:14px;font-size:12px;color:var(--text-muted)'>Or tell me what to do, in your own words</div>",
                    unsafe_allow_html=True)
        fc1, fc2 = st.columns([5, 1])
        with fc1:
            free_text = st.text_input("Free text request", key="agent_free_text",
                                       placeholder="e.g. optimize my thin posts and generate images for anything missing one",
                                       label_visibility="collapsed")
        with fc2:
            plan_clicked = st.button("Plan it →", key="agent_plan_btn", use_container_width=True,
                                      disabled=not (free_text.strip() and ai_key and domain))
        if not ai_key:
            st.caption("Add an AI API key in the sidebar to unlock free-text requests.")
        if plan_clicked and free_text.strip():
            _agent_user(free_text.strip())
            no_img_n = sum(1 for p in st.session_state.posts if not p.get("featured_media"))
            context_summary = (f"{len(st.session_state.posts)} post(s) loaded, {no_img_n} missing images, "
                               f"sandbox={'on' if dry_run else 'off'}, connected to {domain}.")
            with st.spinner("Planning..."):
                plan = run_agent_planner(free_text.strip(), context_summary)
            st.session_state.agent_plan = plan["steps"]
            _agent_say(plan["reply"] if plan["steps"] else plan["reply"] + " Try the menu above instead.")
            st.rerun()

    # ── Plan confirmation — nothing here runs until the user approves ────
    if st.session_state.agent_plan:
        st.markdown("<div class='panel-box' style='margin-top:10px'>", unsafe_allow_html=True)
        st.markdown("**Proposed steps** — review before I run anything:")
        keep = []
        for i, step in enumerate(st.session_state.agent_plan):
            args_str = f" _(args: {step['args']})_" if step["args"] else ""
            group = AGENT_TOOLS.get(step["tool"], {}).get("group", "")
            group_tag = f"`{group}` " if group else ""
            checked = st.checkbox(f"{group_tag}**{step['tool']}** — {step.get('why','')}{args_str}",
                                   value=True, key=f"agent_plan_step_{i}")
            if checked: keep.append(step)
        pc1, pc2, pc3 = st.columns(3)
        with pc1:
            if st.button("▶️ Run selected steps", type="primary", use_container_width=True, key="agent_plan_run"):
                auth = make_auth(wp_user, wp_pw) if (wp_user and wp_pw) else None
                for step in keep:
                    ok, msg = execute_agent_tool(step["tool"], step["args"], auth, domain, dry_run)
                    _agent_say(("✅ " if ok else "⚠️ ") + msg)
                st.session_state.agent_plan = []
                st.rerun()
        with pc2:
            if st.button("🧵 Run in background", use_container_width=True, key="agent_plan_run_bg",
                         disabled=not _BG_CTX_OK, help="Keeps the app usable while a long plan (e.g. a batch of "
                         "posts, or a full audit + fixes) runs. Progress shows up whenever you interact with the "
                         "app — there's no push-based live update, that's not something Streamlit can do."):
                auth = make_auth(wp_user, wp_pw) if (wp_user and wp_pw) else None
                job = {"log": [], "done_n": 0, "total": len(keep), "status": "running"}
                st.session_state.agent_bg_job = job
                t = threading.Thread(target=_agent_plan_worker, args=(job, keep, auth, domain, dry_run), daemon=True)
                _add_script_run_ctx(t)
                t.start()
                st.session_state.agent_plan = []
                _agent_say(f"Started {len(keep)} step(s) in the background — I'll keep working while you do other "
                           f"things. Check back in this tab for progress.")
                st.rerun()
        with pc3:
            if st.button("✖️ Discard plan", use_container_width=True, key="agent_plan_discard"):
                st.session_state.agent_plan = []
                _agent_say("Okay, discarded that plan.")
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Background job status — no live push, refreshes on any interaction ──
    if st.session_state.agent_bg_job:
        job = st.session_state.agent_bg_job
        st.markdown("<div class='panel-box' style='margin-top:10px'>", unsafe_allow_html=True)
        running = job["status"] == "running"
        st.markdown(f"**{'🧵 Running in background…' if running else '✅ Background job finished'}** "
                    f"— {job['done_n']}/{job['total']} step(s)")
        st.progress(job["done_n"] / job["total"] if job["total"] else 1.0)
        for entry in job["log"]:
            st.markdown(("✅ " if entry["ok"] else "⚠️ ") + f"**{entry['tool']}** — {entry['msg']}")
        bc1, bc2 = st.columns(2)
        with bc1:
            if running:
                st.button("🔄 Refresh status", use_container_width=True, key="agent_bg_refresh")
                st.caption("Updates whenever you interact with the app — feel free to keep chatting or switch tabs.")
        with bc2:
            if not running and st.button("Dismiss", use_container_width=True, key="agent_bg_dismiss"):
                st.session_state.agent_bg_job = None
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='padding-top:8px'></div>", unsafe_allow_html=True)
    if st.button("🔄 Start a new conversation", key="agent_reset"):
        st.session_state.agent_log = []
        st.session_state.agent_plan = []
        st.session_state.agent_step = "start"
        st.session_state["_agent_pdf"] = None
        st.rerun()

# ════════════════════════════════════════════════════════════
#  SITE HEALTH TAB
# ════════════════════════════════════════════════════════════
elif active == "health":
    st.markdown("""
    <div class='section-head'>
      <h3>🩺 Site health &amp; performance</h3>
      <span class='hint'>Technical · Security · Site-wide SEO · Performance · Content — with one-click fixes</span>
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.get("_fix_toast"):
        _t = st.session_state["_fix_toast"]
        st.success(f"✅ '{_t['label']}' — fixed {_t['ok']} post(s)" +
                   (f" · ❌ {_t['err']} failed" if _t['err'] else "") +
                   ". The checks below already reflect this — no need to re-scan.")
        with st.expander("View fix details"):
            for r in _t["details"]:
                st.caption(f"{'✅' if r['status']=='ok' else '❌'} {r['title']} — {r['detail']}")
        st.session_state["_fix_toast"] = None

    def _issue_score(issues):
        if not issues: return None
        return round(sum(1 for r in issues if r["status"]=="pass")/len(issues)*100)

    def render_issue_row(res, key_prefix, extra_body=None):
        icon = {"pass":"✅","warn":"⚠️","fail":"❌"}.get(res["status"],"❓")
        pill_cls = {"pass":"pub","warn":"skip","fail":"noimg"}.get(res["status"],"skip")
        colA, colB = st.columns([6,1.3])
        with colA:
            st.markdown(f"""
            <div class='post-row-ui'>
              <div class='post-thumb {"has" if res["status"]=="pass" else ""}'>{icon}</div>
              <div class='post-info'>
                <div class='post-title-ui'>{res["label"]}</div>
                <div class='post-meta-ui'>{res["detail"]} — {res["recommendation"]}</div>
              </div>
              <span class='pill {pill_cls}'>{res["status"]}</span>
            </div>
            """, unsafe_allow_html=True)
            if extra_body: extra_body(res)
        with colB:
            can_direct_fix = res.get("fix_mode") and res.get("count", 1) > 0
            if can_direct_fix:
                disabled = not ai_key or (not domain) or (not wp_user or not wp_pw)
                if st.button("⚡ Fix now", key=f"{key_prefix}_now_{res['id']}",
                             use_container_width=True, type="primary", disabled=disabled):
                    auth = make_auth(wp_user, wp_pw)
                    label = "Previewing" if dry_run else "Fixing"
                    with st.spinner(f"{label} {len(res.get('select_ids', []))} post(s)..."):
                        fix_results = apply_content_fix_now(
                            res.get("select_ids", []), res["fix_mode"], auth, domain,
                            extra_instructions=res.get("fix_instructions",""), is_dry_run=dry_run)
                    ok_n = sum(1 for r in fix_results if r["status"]=="ok")
                    err_n = len(fix_results) - ok_n
                    if dry_run:
                        st.info(f"🟡 Sandbox preview — {ok_n} post(s) would be updated. Turn off Sandbox mode in the sidebar to push for real.")
                        with st.expander("View results"):
                            for r in fix_results:
                                st.caption(f"{'✅' if r['status']=='ok' else '❌'} {r['title']} — {r['detail']}")
                    else:
                        for r in fix_results:
                            st.session_state.run_log.append({"id":r["id"],"title":r["title"],
                                "status":"ok" if r["status"]=="ok" else "error","word_count":0,
                                "media_id":None,"meta_description":"","focus_keyword":"",
                                "error":r["detail"] if r["status"]!="ok" else ""})
                        # Recompute checks that read from the local post cache, so the
                        # fix shows as fixed immediately — not just on the next full scan.
                        st.session_state.health_content = analyze_content_health(st.session_state.posts, gate_min_words)
                        st.session_state.content_quality_results = analyze_content_quality_at_scale(
                            st.session_state.posts, stale_days)
                        st.session_state["_fix_toast"] = {
                            "label": res["label"], "ok": ok_n, "err": err_n, "details": fix_results}
                        st.rerun()
                if disabled:
                    st.caption("Needs AI key + WP login")
            elif res.get("fix_tab") and res.get("count", 1) > 0:
                if st.button("Fix →", key=f"{key_prefix}_{res['id']}", use_container_width=True):
                    if res.get("select_ids"):
                        st.session_state.selected = res["select_ids"]
                    if res.get("fix_instructions"):
                        st.session_state.prefill_fix_instructions = res["fix_instructions"]
                    st.session_state.active_tab = res["fix_tab"]; st.rerun()
            elif res.get("fix_plugin_slug") and res["status"] != "pass":
                disabled = not (domain and wp_user and wp_pw) or dry_run
                if st.button(f"⚡ {res.get('fix_plugin_label','Install fix plugin')}",
                             key=f"{key_prefix}_plugin_{res['id']}", use_container_width=True,
                             type="primary", disabled=disabled):
                    auth = make_auth(wp_user, wp_pw)
                    with st.spinner("Installing & activating plugin..."):
                        ok, msg = wp_install_plugin(res["fix_plugin_slug"], auth, domain)
                    if ok:
                        # This particular fix needs no manual onboarding step (unlike the
                        # headers plugin), so verify it actually took effect right away.
                        with st.spinner("Verifying fix..."):
                            st.session_state.security_results = run_security_check(domain)
                        st.session_state["_fix_toast"] = {
                            "label": res["label"], "ok": 1, "err": 0,
                            "details": [{"status":"ok","title":domain,"detail":msg}]}
                        st.rerun()
                    else:
                        st.error(msg)
                if disabled and dry_run:
                    st.caption("Turn off Sandbox mode to install")

    def render_crawl_row(res, key_prefix):
        render_issue_row(res, key_prefix)
        items = res.get("items")
        if items and res["status"] != "pass":
            with st.expander(f"View affected pages ({len(items) if isinstance(items,list) else len(items)})"):
                if isinstance(items, dict):
                    for k, urls in list(items.items())[:15]:
                        st.caption(f"**{k or '(empty)'}** → " + ", ".join(urls[:5]))
                else:
                    for u in items[:20]:
                        st.caption(u)

    ov_tab, tech_tab, sec_tab, perf_tab, crawl_tab, cq_tab, rep_tab = st.tabs(
        ["📊 Overview", "⚙️ Technical", "🔒 Security", "⚡ Performance", "🔍 SEO Crawl", "📝 Content Quality", "📄 Reports"]
    )

    # ── OVERVIEW ─────────────────────────────────────────────
    with ov_tab:
        tech_score  = _issue_score(st.session_state.health_results)
        sec_score   = _issue_score(st.session_state.security_results)
        crawl_score = _issue_score(st.session_state.crawl_results["issues"]) if st.session_state.crawl_results else None
        cq_score    = _issue_score(st.session_state.content_quality_results)
        cwv         = st.session_state.cwv_results
        perf_score  = cwv.get("overall_score") if cwv and not cwv.get("error") else None

        c1, c2 = st.columns([3,1])
        with c1:
            run_all = st.button("🔍 Run full audit (all checks)", type="primary", use_container_width=True,
                                disabled=not domain)
        with c2:
            if st.button("🗑️ Clear all results", use_container_width=True):
                for k in ["health_results","health_content","security_results","crawl_results",
                          "cwv_results","content_quality_results"]:
                    st.session_state[k] = None
                st.rerun()

        if run_all:
            with st.spinner("Running technical scan..."):
                try: st.session_state.health_results = run_site_health_check(domain)
                except Exception as e: st.error(f"Technical scan failed: {e}")
            with st.spinner("Running security scan..."):
                try: st.session_state.security_results = run_security_check(domain)
                except Exception as e: st.error(f"Security scan failed: {e}")
            with st.spinner("Checking Core Web Vitals (this can take ~20s)..."):
                st.session_state.cwv_results = check_core_web_vitals(domain, pagespeed_key)
            if st.session_state.posts:
                with st.spinner(f"Crawling up to {crawl_max_pages} pages for site-wide SEO..."):
                    try: st.session_state.crawl_results = crawl_site_seo(st.session_state.posts, crawl_max_pages)
                    except Exception as e: st.error(f"SEO crawl failed: {e}")
                st.session_state.health_content = analyze_content_health(st.session_state.posts, gate_min_words)
                st.session_state.content_quality_results = analyze_content_quality_at_scale(
                    st.session_state.posts, stale_days)
            else:
                st.info("💡 Load posts in the 📡 Scan & select tab to also get site-wide SEO crawl and content quality checks.")

            _snap = {"technical": _issue_score(st.session_state.health_results),
                     "security": _issue_score(st.session_state.security_results),
                     "seo_crawl": _issue_score(st.session_state.crawl_results["issues"]) if st.session_state.crawl_results else None,
                     "content_quality": _issue_score(st.session_state.content_quality_results),
                     "performance": st.session_state.cwv_results.get("overall_score") if st.session_state.cwv_results and not st.session_state.cwv_results.get("error") else None}
            if domain:
                save_health_snapshot(domain, _snap)
            st.rerun()

        vals = [v for v in [tech_score, sec_score, crawl_score, cq_score, perf_score] if v is not None]
        overall = round(sum(vals)/len(vals)) if vals else None
        overall_color = "#1D9E75" if (overall or 0)>=80 else ("#d4a012" if (overall or 0)>=50 else "#D85A30")

        st.markdown(f"""
        <div class="stats-grid" style="grid-template-columns:repeat(6,1fr)">
          <div class="stat-card purple">
            <div class="stat-icon purple">🎯</div><div class="stat-label">Overall</div>
            <div class="stat-val" style="color:{overall_color}">{f"{overall}%" if overall is not None else "—"}</div>
            <div class="stat-delta good">weighted average</div>
          </div>
          <div class="stat-card teal">
            <div class="stat-icon teal">⚙️</div><div class="stat-label">Technical</div>
            <div class="stat-val">{f"{tech_score}%" if tech_score is not None else "—"}</div>
            <div class="stat-delta info">{"scanned" if tech_score is not None else "not run"}</div>
          </div>
          <div class="stat-card coral">
            <div class="stat-icon coral">🔒</div><div class="stat-label">Security</div>
            <div class="stat-val">{f"{sec_score}%" if sec_score is not None else "—"}</div>
            <div class="stat-delta info">{"scanned" if sec_score is not None else "not run"}</div>
          </div>
          <div class="stat-card blue">
            <div class="stat-icon blue">🔍</div><div class="stat-label">SEO crawl</div>
            <div class="stat-val">{f"{crawl_score}%" if crawl_score is not None else "—"}</div>
            <div class="stat-delta info">{"scanned" if crawl_score is not None else "not run"}</div>
          </div>
          <div class="stat-card amber">
            <div class="stat-icon amber">⚡</div><div class="stat-label">Performance</div>
            <div class="stat-val">{f"{perf_score}%" if perf_score is not None else "—"}</div>
            <div class="stat-delta info">{"scanned" if perf_score is not None else "not run"}</div>
          </div>
          <div class="stat-card purple">
            <div class="stat-icon purple">📝</div><div class="stat-label">Content</div>
            <div class="stat-val">{f"{cq_score}%" if cq_score is not None else "—"}</div>
            <div class="stat-delta info">{"scanned" if cq_score is not None else "not run"}</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        _hist = [h for h in load_health_history() if h.get("domain")==domain] if domain else []
        if len(_hist) >= 2:
            st.markdown("""<div class="section-head"><h3>📈 Score history</h3><span class="hint">This domain, most recent scans</span></div>""",
                        unsafe_allow_html=True)
            df = pd.DataFrame(_hist)[["timestamp","technical","security","seo_crawl","content_quality","performance"]].set_index("timestamp")
            st.line_chart(df)
        elif not overall:
            st.markdown("""
            <div class="empty-feed">
              <div class="empty-icon">🩺</div>
              <div class="empty-title">No audit yet</div>
              <div class="empty-sub">Click "Run full audit" above, or run individual scans<br>in the Technical / Security / SEO Crawl / Content Quality tabs.</div>
            </div>
            """, unsafe_allow_html=True)

    # ── TECHNICAL ────────────────────────────────────────────
    with tech_tab:
        if st.button("🔍 Run technical scan", type="primary", disabled=not domain, key="run_tech"):
            with st.spinner("Checking SSL, speed, SEO tags, robots.txt, sitemap..."):
                try: st.session_state.health_results = run_site_health_check(domain)
                except Exception as e: st.error(f"Scan failed: {e}")
            st.session_state.health_content = analyze_content_health(st.session_state.posts, gate_min_words)
            st.rerun()

        results = st.session_state.health_results
        if results:
            st.markdown("<div class='post-table'>", unsafe_allow_html=True)
            for res in results:
                render_issue_row(res, "fix_tech")
            st.markdown("</div>", unsafe_allow_html=True)

            content_results = st.session_state.health_content
            if content_results:
                st.markdown("""<div class="section-head"><h3>📝 Quick content checks</h3></div>""", unsafe_allow_html=True)
                st.markdown("<div class='post-table'>", unsafe_allow_html=True)
                for res in content_results:
                    render_issue_row(res, "fix_techcontent")
                st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("Run a technical scan to check SSL, page speed, meta tags, robots.txt and sitemap.")

    # ── SECURITY ─────────────────────────────────────────────
    with sec_tab:
        if st.button("🔒 Run security scan", type="primary", disabled=not domain, key="run_sec"):
            with st.spinner("Checking security headers, XML-RPC, directory listing, version leaks..."):
                try: st.session_state.security_results = run_security_check(domain)
                except Exception as e: st.error(f"Scan failed: {e}")
            st.rerun()

        sec_results = st.session_state.security_results
        if sec_results:
            fails = sum(1 for r in sec_results if r["status"]=="fail")
            if fails:
                st.error(f"🚨 {fails} security issue(s) need attention.")

            header_issues = [r for r in sec_results if r.get("fix_group")=="headers"]
            if header_issues:
                disabled = not (domain and wp_user and wp_pw) or dry_run
                st.markdown(f"""
                <div class='hero-banner' style='margin:0 0 12px'>
                  <span style='font-size:18px'>🛡️</span>
                  <span style='font-size:12.5px;color:var(--text-secondary)'>
                    <b style='color:var(--text-primary)'>{len(header_issues)} security header(s) missing.</b>
                    One plugin covers all of them: <b>Really Simple Security</b> (5M+ installs) adds HSTS, CSP, X-Frame-Options and more.
                  </span>
                </div>
                """, unsafe_allow_html=True)
                if st.button("⚡ Install & activate Really Simple Security", type="primary",
                             disabled=disabled, key="fix_headers_plugin"):
                    auth = make_auth(wp_user, wp_pw)
                    with st.spinner("Installing & activating plugin..."):
                        ok, msg = wp_install_plugin("really-simple-ssl", auth, domain)
                    if ok:
                        st.session_state["_plugin_toast_headers"] = msg
                    else:
                        st.error(msg)
                if disabled and dry_run:
                    st.caption("Turn off Sandbox mode to install")
                if st.session_state.get("_plugin_toast_headers"):
                    st.info(f"✅ {st.session_state['_plugin_toast_headers']} Finish the 1-minute onboarding in "
                            "WP Admin → Really Simple Security to actually enable the headers, then click Re-check below.")
                    if st.button("↻ Re-check security now", key="recheck_headers"):
                        with st.spinner("Re-checking..."):
                            st.session_state.security_results = run_security_check(domain)
                        st.session_state["_plugin_toast_headers"] = None
                        st.rerun()

            st.markdown("<div class='post-table'>", unsafe_allow_html=True)
            for res in sec_results:
                render_issue_row(res, "fix_sec")
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("Run a security scan to check headers, XML-RPC exposure, directory listing, and version disclosure. No WordPress login needed.")

    # ── PERFORMANCE ──────────────────────────────────────────
    with perf_tab:
        st.caption("Real Core Web Vitals from Google PageSpeed Insights — mobile, since that's what Google ranks on.")
        if st.button("⚡ Run performance scan", type="primary", disabled=not domain, key="run_perf"):
            with st.spinner("Checking Core Web Vitals (this can take ~20 seconds)..."):
                st.session_state.cwv_results = check_core_web_vitals(domain, pagespeed_key)
            st.rerun()

        cwv = st.session_state.cwv_results
        if cwv:
            if cwv.get("error"):
                st.error(f"Couldn't fetch Core Web Vitals: {cwv['error']}")
                st.caption("This usually means the free PageSpeed API quota was hit — add your own free API key in the sidebar under Reporting & Audit, or try again in a minute.")
            else:
                score = cwv.get("overall_score")
                score_color = "#1D9E75" if (score or 0)>=80 else ("#d4a012" if (score or 0)>=50 else "#D85A30")
                st.markdown(f"""
                <div class="stats-grid" style="grid-template-columns:repeat(1,1fr);max-width:260px">
                  <div class="stat-card teal">
                    <div class="stat-icon teal">⚡</div><div class="stat-label">Performance score</div>
                    <div class="stat-val" style="color:{score_color}">{f"{score}%" if score is not None else "—"}</div>
                    <div class="stat-delta good">Google PageSpeed, mobile</div>
                  </div>
                </div>
                """, unsafe_allow_html=True)
                st.markdown("<div class='post-table'>", unsafe_allow_html=True)
                for res in cwv.get("metrics", []):
                    render_issue_row(res, "fix_perf")
                st.markdown("</div>", unsafe_allow_html=True)

                metrics = cwv.get("metrics", [])
                slow = [m for m in metrics if m["id"] in ("lcp","fcp") and m["status"] != "pass"]
                shifty = next((m for m in metrics if m["id"]=="cls" and m["status"] != "pass"), None)

                if slow:
                    disabled = not (domain and wp_user and wp_pw) or dry_run
                    st.markdown("""
                    <div class='hero-banner'>
                      <span style='font-size:18px'>🐢</span>
                      <span style='font-size:12.5px;color:var(--text-secondary)'>
                        <b style='color:var(--text-primary)'>Slow loading detected.</b>
                        A caching plugin is the single biggest lever here — it turns dynamically-built pages into fast static files.
                      </span>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button("⚡ Install caching plugin (WP Super Cache)", type="primary",
                                 disabled=disabled, key="fix_perf_cache"):
                        auth = make_auth(wp_user, wp_pw)
                        with st.spinner("Installing & activating WP Super Cache..."):
                            ok, msg = wp_install_plugin("wp-super-cache", auth, domain)
                        if ok:
                            st.session_state["_plugin_toast_cache"] = msg
                        else:
                            st.error(msg)
                    if disabled and dry_run:
                        st.caption("Turn off Sandbox mode to install")
                    if st.session_state.get("_plugin_toast_cache"):
                        st.info(f"✅ {st.session_state['_plugin_toast_cache']} Finish setup: WP Admin → Settings → "
                                "WP Super Cache → 'Easy' tab → check 'Caching On' → Update Status — that click can't "
                                "be automated via the REST API. Once done, re-check below (PageSpeed can also take "
                                "a minute to reflect the change, so if it looks unchanged, wait a moment and try again).")
                        if st.button("↻ Re-check performance now", key="recheck_perf"):
                            with st.spinner("Re-checking Core Web Vitals..."):
                                st.session_state.cwv_results = check_core_web_vitals(domain, pagespeed_key)
                            st.session_state["_plugin_toast_cache"] = None
                            st.rerun()

                if shifty:
                    disabled2 = not (domain and wp_user and wp_pw) or not st.session_state.posts
                    st.markdown("""
                    <div class='hero-banner'>
                      <span style='font-size:18px'>📐</span>
                      <span style='font-size:12.5px;color:var(--text-secondary)'>
                        <b style='color:var(--text-primary)'>Layout shift detected.</b>
                        Usually caused by images without a set width/height, so the page jumps as they load.
                        This scans your loaded posts, reads each image's real size, and writes it into the HTML.
                      </span>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button("⚡ Fix missing image dimensions across loaded posts", type="primary",
                                 disabled=disabled2, key="fix_perf_cls"):
                        auth = make_auth(wp_user, wp_pw)
                        with st.spinner(f"Scanning images in {len(st.session_state.posts)} post(s)..."):
                            dim_results = fix_image_dimensions_now(st.session_state.posts, auth, domain, is_dry_run=dry_run)
                        ok_n = sum(1 for r in dim_results if r["status"]=="ok")
                        err_n = len(dim_results) - ok_n
                        if dry_run:
                            st.info(f"🟡 Sandbox preview — {ok_n} post(s) checked. Turn off Sandbox mode to push for real.")
                            with st.expander("View results"):
                                for r in dim_results:
                                    st.caption(f"{'✅' if r['status']=='ok' else '❌'} {r['title']} — {r['detail']}")
                        else:
                            st.session_state["_fix_toast"] = {
                                "label": "Fix missing image dimensions", "ok": ok_n, "err": err_n, "details": dim_results}
                            st.session_state["_show_cls_recheck"] = True
                            st.rerun()
                    if not st.session_state.posts:
                        st.caption("Load posts first in 📡 Scan & select.")
                    if st.session_state.get("_show_cls_recheck"):
                        st.caption("Note: this only fixed posts that were loaded — if your homepage itself has the "
                                   "layout-shifting images (not a blog post), this won't touch it. PageSpeed can also "
                                   "take a minute to reflect the change.")
                        if st.button("↻ Re-check performance now", key="recheck_perf_cls"):
                            with st.spinner("Re-checking Core Web Vitals..."):
                                st.session_state.cwv_results = check_core_web_vitals(domain, pagespeed_key)
                            st.session_state["_show_cls_recheck"] = False
                            st.rerun()
        else:
            st.info("Run a performance scan to check Largest Contentful Paint, Cumulative Layout Shift, Total Blocking Time, and First Contentful Paint.")

    # ── SEO CRAWL ────────────────────────────────────────────
    with crawl_tab:
        st.caption(f"Crawls up to **{crawl_max_pages}** live post URLs (adjust in the sidebar under Reporting &amp; Audit).")
        if st.button("🔍 Run site-wide SEO crawl", type="primary",
                     disabled=not st.session_state.posts, key="run_crawl"):
            with st.spinner(f"Crawling up to {crawl_max_pages} pages..."):
                try: st.session_state.crawl_results = crawl_site_seo(st.session_state.posts, crawl_max_pages)
                except Exception as e: st.error(f"Crawl failed: {e}")
            st.rerun()

        if not st.session_state.posts:
            st.info("💡 Load posts first in the 📡 Scan & select tab — the crawl works off your loaded post URLs.")

        crawl = st.session_state.crawl_results
        if crawl:
            pages, issues = crawl["pages"], crawl["issues"]
            ok_n = sum(1 for p in pages if p["ok"])
            st.markdown(f"""
            <div class="stats-grid" style="grid-template-columns:repeat(3,1fr)">
              <div class="stat-card teal"><div class="stat-icon teal">📄</div><div class="stat-label">Pages crawled</div>
                <div class="stat-val">{len(pages)}</div><div class="stat-delta good">{ok_n} reachable</div></div>
              <div class="stat-card coral"><div class="stat-icon coral">🚫</div><div class="stat-label">Broken pages</div>
                <div class="stat-val">{len(pages)-ok_n}</div><div class="stat-delta warn">need fixing</div></div>
              <div class="stat-card amber"><div class="stat-icon amber">🎯</div><div class="stat-label">Crawl score</div>
                <div class="stat-val">{_issue_score(issues)}%</div><div class="stat-delta info">of {len(issues)} checks</div></div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("<div class='post-table'>", unsafe_allow_html=True)
            for res in issues:
                render_crawl_row(res, "fix_crawl")
            st.markdown("</div>", unsafe_allow_html=True)

    # ── CONTENT QUALITY ──────────────────────────────────────
    with cq_tab:
        if st.button("📝 Run content quality analysis", type="primary",
                     disabled=not st.session_state.posts, key="run_cq"):
            with st.spinner("Scoring readability, checking for near-duplicates and stale posts..."):
                st.session_state.content_quality_results = analyze_content_quality_at_scale(
                    st.session_state.posts, stale_days)
                st.session_state.health_content = analyze_content_health(st.session_state.posts, gate_min_words)
            st.rerun()

        if not st.session_state.posts:
            st.info("💡 Load posts first in the 📡 Scan & select tab.")

        cq = st.session_state.content_quality_results
        hc = st.session_state.health_content
        if hc:
            st.markdown("<div class='post-table'>", unsafe_allow_html=True)
            for res in hc:
                render_issue_row(res, "fix_hc")
            st.markdown("</div>", unsafe_allow_html=True)
        if cq:
            st.markdown("<div class='post-table'>", unsafe_allow_html=True)
            for res in cq:
                if res["id"] == "cq_dup":
                    render_issue_row(res, "fix_cq")
                    pairs = res.get("pairs")
                    if pairs:
                        with st.expander(f"View similar pairs ({len(pairs)})"):
                            for a, b, sim in pairs:
                                st.caption(f"**{sim}% similar** — {a}  ↔  {b}")
                else:
                    render_issue_row(res, "fix_cq")
            st.markdown("</div>", unsafe_allow_html=True)

    # ── REPORTS ──────────────────────────────────────────────
    with rep_tab:
        st.markdown("""<div class="section-head"><h3>📄 Client-ready report</h3><span class="hint">Branded PDF · CSV export · score history</span></div>""",
                    unsafe_allow_html=True)
        if not agency_name:
            st.caption("💡 Set your agency/brand name in the sidebar under Reporting & Audit to brand the PDF.")

        has_any = any([st.session_state.health_results, st.session_state.security_results,
                       st.session_state.crawl_results, st.session_state.content_quality_results,
                       st.session_state.cwv_results])
        if has_any:
            scores = {
                "Technical": _issue_score(st.session_state.health_results),
                "Security": _issue_score(st.session_state.security_results),
                "SEO Crawl": _issue_score(st.session_state.crawl_results["issues"]) if st.session_state.crawl_results else None,
                "Content Quality": _issue_score(st.session_state.content_quality_results),
                "Performance": st.session_state.cwv_results.get("overall_score") if st.session_state.cwv_results and not st.session_state.cwv_results.get("error") else None,
            }
            groups = [
                ("Technical & Performance", st.session_state.health_results or []),
                ("Security", st.session_state.security_results or []),
                ("Site-wide SEO Crawl", (st.session_state.crawl_results or {}).get("issues", [])),
                ("Content Quality", st.session_state.content_quality_results or []),
                ("Content Health", st.session_state.health_content or []),
            ]
            if st.button("📥 Generate PDF report", type="primary", use_container_width=True):
                try:
                    pdf_bytes = generate_pdf_report(domain, agency_name, scores, groups)
                    st.download_button("⬇️ Download PDF", data=pdf_bytes,
                        file_name=f"{domain or 'site'}_health_report_{datetime.now().strftime('%Y%m%d')}.pdf",
                        mime="application/pdf", use_container_width=True)
                except Exception as e:
                    st.error(f"Couldn't build PDF: {e}. Make sure 'fpdf2' is installed (pip install fpdf2).")

            all_rows = []
            for gname, gissues in groups:
                for r in gissues:
                    all_rows.append({"category": gname, "check": r.get("label",""),
                                      "status": r.get("status",""), "detail": r.get("detail",""),
                                      "recommendation": r.get("recommendation","")})
            if all_rows:
                buf = StringIO()
                w = csv.DictWriter(buf, fieldnames=["category","check","status","detail","recommendation"])
                w.writeheader(); w.writerows(all_rows)
                st.download_button("📥 Export all issues as CSV", data=buf.getvalue(),
                    file_name=f"{domain or 'site'}_audit_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv", use_container_width=True)
        else:
            st.info("Run at least one scan (Technical, Security, SEO Crawl, or Content Quality) to generate a report.")

        _hist = [h for h in load_health_history() if h.get("domain")==domain] if domain else []
        if _hist:
            st.markdown("""<div class="section-head"><h3>🕓 Scan history</h3></div>""", unsafe_allow_html=True)
            hist_df = pd.DataFrame(_hist)[["timestamp","technical","security","seo_crawl","content_quality","performance"]]
            st.dataframe(hist_df, use_container_width=True, hide_index=True)



# ════════════════════════════════════════════════════════════
#  SCAN & SELECT TAB
# ════════════════════════════════════════════════════════════
elif active == "scan":
    st.markdown("<div style='padding:20px 28px 0'>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns([3,1,1])
    with c1:
        if st.button("📡 Scan WordPress site", type="primary", use_container_width=True):
            if not (domain and wp_user and wp_pw):
                st.error("Fill in domain, username and app password in the sidebar.")
            else:
                with st.spinner("Connecting to WordPress REST API..."):
                    try:
                        auth  = make_auth(wp_user, wp_pw)
                        posts = fetch_all_posts(auth, domain, post_status, int(max_posts_in))
                        st.session_state.posts    = posts
                        st.session_state.selected = [p["id"] for p in posts]
                        st.success(f"✅ Found {len(posts)} posts on {domain}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Connection failed: {e}")
    with c2:
        if st.button("🗑️ Clear resume", use_container_width=True):
            reset_progress(); st.success("Done.")
    with c3:
        resume_info = load_progress()
        done_count  = len(resume_info.get("processed", []))
        st.metric("Resumable", f"{done_count} posts")

    st.markdown("</div>", unsafe_allow_html=True)

    posts_to_show = st.session_state.posts
    if posts_to_show:
        no_img_posts  = [p for p in posts_to_show if not p.get("featured_media")]
        has_img_posts = [p for p in posts_to_show if p.get("featured_media")]

        st.markdown(f"""
        <div class='section-head'>
          <h3>Select posts</h3>
          <span class='hint'>🖼️ {len(has_img_posts)} with image · 🚫 {len(no_img_posts)} without</span>
        </div>
        """, unsafe_allow_html=True)

        ca, cb, cc, cd = st.columns([1,1,2,2])
        with ca:
            if st.button("✅ All", use_container_width=True):
                st.session_state.selected = [p["id"] for p in posts_to_show]; st.rerun()
        with cb:
            if st.button("❌ None", use_container_width=True):
                st.session_state.selected = []; st.rerun()
        with cc:
            if st.button("🚫 Only without image", use_container_width=True):
                st.session_state.selected = [p["id"] for p in no_img_posts]; st.rerun()
        with cd:
            show_no_img = st.toggle("Show only posts without image", value=False)

        search   = st.text_input("🔎 Search posts", placeholder="Filter by title...")
        pool     = no_img_posts if show_no_img else posts_to_show
        filtered = [p for p in pool if search.lower() in p["title"]["rendered"].lower()] if search else pool

        st.markdown("<div class='post-table'>", unsafe_allow_html=True)
        for post in filtered:
            pid     = post["id"]
            title   = post["title"]["rendered"]
            stat    = post.get("status","?")
            has_img = bool(post.get("featured_media"))
            slug    = post.get("slug","")
            is_date = slug[:4].isdigit() and "-" in slug[:8]
            checked = pid in st.session_state.selected

            thumb_cls = "has" if has_img else ""
            thumb_ico = "🖼️" if has_img else "🚫"
            img_pill  = f"<span class='pill {'pub' if has_img else 'noimg'}'>{'has image' if has_img else 'no image'}</span>"
            stat_pill = f"<span class='pill {'pub' if stat=='publish' else 'draft'}'>{stat}</span>"
            date_warn = " <span class='pill skip'>date slug</span>" if is_date else ""

            st.markdown(f"""
            <div class='post-row-ui'>
              <div class='post-thumb {thumb_cls}'>{thumb_ico}</div>
              <div class='post-info'>
                <div class='post-title-ui'>{title}</div>
                <div class='post-meta-ui'>{slug}</div>
              </div>
              {stat_pill}{img_pill}{date_warn}
            </div>
            """, unsafe_allow_html=True)

            new_val = st.checkbox("Select", value=checked, key=f"chk_{pid}", label_visibility="collapsed")
            if new_val and pid not in st.session_state.selected:
                st.session_state.selected.append(pid)
            elif not new_val and pid in st.session_state.selected:
                st.session_state.selected.remove(pid)

        st.markdown("</div>", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════
#  OPTIMIZE TAB
# ════════════════════════════════════════════════════════════
elif active == "optimize":
    render_stats()
    selected_count = len(st.session_state.selected)

    st.markdown(f"""
    <div class='section-head'>
      <h3>🔧 Optimize selected posts</h3>
      <span class='hint'>{selected_count} posts selected</span>
    </div>
    """, unsafe_allow_html=True)

    with st.container():
        st.markdown("<div style='padding:0 28px'>", unsafe_allow_html=True)
        if st.session_state.get("prefill_fix_instructions"):
            st.caption("💡 Instructions pre-filled from Site Health — edit as needed.")
        fix_instructions = st.text_area(
            "Content fix instructions (leave blank to skip rewriting):",
            value=st.session_state.get("prefill_fix_instructions",""),
            placeholder="• Add a strong CTA at the end of every post\n• Fix broken internal links\n• Improve readability",
            height=110
        )
        st.session_state.prefill_fix_instructions = ""
        st.markdown("</div>", unsafe_allow_html=True)

    if dry_run:
        st.warning("🟡 Sandbox mode — nothing will be written to WordPress.")
    else:
        st.error("🔴 Live mode — content and images will be pushed directly to WordPress.")

    st.markdown("<div style='padding:0 28px 0'>", unsafe_allow_html=True)
    run_btn = st.button(
        f"{'🔍 Preview' if dry_run else '⚡ Run'} optimizer on {selected_count} posts",
        type="primary", use_container_width=True,
        disabled=(selected_count == 0 or not ai_key)
    )
    st.markdown("</div>", unsafe_allow_html=True)

    if run_btn:
        auth = make_auth(wp_user, wp_pw)
        prog_state = load_progress() if resume_mode else {"processed":[],"results":[]}
        already    = set(prog_state.get("processed",[]))
        to_process = [p for p in st.session_state.posts
                      if p["id"] in st.session_state.selected and p["id"] not in already]

        if not to_process:
            st.info("All selected posts already processed. Clear resume to rerun.")
            st.stop()

        progress_bar = st.progress(0)
        status_txt   = st.empty()
        lock         = threading.Lock()
        counter      = [0]

        st.markdown("<div class='post-table'>", unsafe_allow_html=True)
        slots = {p["id"]: st.empty() for p in to_process}
        st.markdown("</div>", unsafe_allow_html=True)

        def process_one(post):
            pid   = post["id"]
            title = post["title"]["rendered"]
            ohtml = post["content"]["rendered"]
            oexc  = post.get("excerpt",{}).get("rendered","")
            slug  = post.get("slug","")
            link  = post.get("link","")
            date  = post.get("date", datetime.utcnow().isoformat())
            stat  = post.get("status","publish")

            res = {"id":pid,"title":title,"status":"ok","word_count":0,
                   "media_id":None,"meta_description":"","focus_keyword":"",
                   "image_prompt":"","alt_text":"","gate_pass":True,"error":""}
            worker_offset = hash(str(pid)) % workers
            time.sleep(worker_offset * 1.5)

            try:
                fixed_html = ohtml
                if fix_instructions.strip():
                    sys_p = ("You are a strict WordPress HTML editor. "
                             "Return ONLY fixed HTML — no markdown, no commentary.")
                    p = f"Title: {title}\nInstructions: {fix_instructions}\nHTML:\n{ohtml[:12000]}"
                    fixed_html = run_ai(p, provider, ai_key, ai_model, system=sys_p,
                                       enable_fallback=enable_fallback, fallback_keys=fallback_keys
                                       ).replace("```html","").replace("```","").strip()

                wc, gate_pass = quality_gate(fixed_html, gate_min_words)
                res["word_count"] = wc; res["gate_pass"] = gate_pass
                if enable_gate and not gate_pass and gate_auto_skip:
                    res["status"] = "gate_fail"; return res

                meta_desc, focus_kw, new_exc = "", "", oexc
                if seo_meta_desc:
                    plain = BeautifulSoup(fixed_html,"html.parser").get_text()
                    seo   = generate_seo_meta(title, plain, provider, ai_key, ai_model,
                                              enable_fallback, fallback_keys)
                    meta_desc = seo.get("meta_description","")
                    focus_kw  = seo.get("focus_keyword","")
                    new_exc   = seo.get("excerpt", oexc)
                    res["meta_description"] = meta_desc
                    res["focus_keyword"]    = focus_kw

                if seo_schema:
                    tag = ('<script type="application/ld+json">'
                           + generate_schema_jsonld(title, link, date, meta_desc or new_exc)
                           + '</script>')
                    fixed_html = tag + "\n" + fixed_html

                media_id, img_bytes, seo_alt = None, None, ""
                if generate_images:
                    raw = run_ai(
                        f"Write a 2-sentence photorealistic image prompt for '{title}'. Raw text only.",
                        provider, ai_key, ai_model, 0.1,
                        enable_fallback=enable_fallback, fallback_keys=fallback_keys
                    )
                    img_prompt = " ".join(raw.replace("*","").replace('"','').split())[:800]
                    seo_alt    = run_ai(
                        f"SEO image alt text under 120 chars for '{title}'. No quotes.",
                        provider, ai_key, ai_model, 0.1,
                        enable_fallback=enable_fallback, fallback_keys=fallback_keys
                    ).replace('"','')
                    res["image_prompt"] = img_prompt; res["alt_text"] = seo_alt
                    for attempt in range(3):
                        try:
                            _use_dalle = image_provider == "DALL-E 3" and bool(dalle_key or ai_key)
                            img_bytes = gen_image_dalle(img_prompt, dalle_key or ai_key, dalle_style) if _use_dalle else gen_image_pollinations(img_prompt)
                            break
                        except Exception as e:
                            if attempt == 2: res["error"] += f"Image: {e}. "
                            else: time.sleep(3)

                if dry_run:
                    res["status"] = "preview"; return res

                if img_bytes:
                    try: media_id = upload_wp_image(img_bytes, title, seo_alt, auth, domain, optimize_seo_img)
                    except Exception as e: res["error"] += f"Upload: {e}. "

                new_status = stat if update_status == "keep original" else update_status
                payload    = {"content":fixed_html,"status":new_status,"excerpt":new_exc}
                if media_id: payload["featured_media"] = media_id
                if seo_fix_slug and slug[:4].isdigit():
                    payload["slug"] = "-".join(title.lower().replace("'","").split()[:6])

                if not post.get("categories") or post.get("categories") == [1]:
                    wp_cats = fetch_wp_categories(auth, domain)
                    if wp_cats:
                        plain_txt = BeautifulSoup(fixed_html,"html.parser").get_text()
                        auto_cat  = ai_pick_category(title, plain_txt, wp_cats,
                                                     provider, ai_key, ai_model,
                                                     enable_fallback, fallback_keys)
                        if auto_cat:
                            payload["categories"] = [auto_cat]

                r = wp_update_post(pid, payload, auth, domain)
                if r and r.status_code == 200:
                    res["status"] = "ok"; res["media_id"] = media_id
                    if seo_meta_desc and meta_desc:
                        update_yoast_meta(pid, meta_desc, focus_kw, auth, domain)
                else:
                    res["status"] = "error"
                    res["error"] += f"WP API error {getattr(r,'status_code','no response')}."
            except Exception as e:
                res["status"] = "error"; res["error"] = friendly_error(e)
            return res

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(process_one, p): p for p in to_process}
            for future in as_completed(futures):
                res  = future.result()
                post = futures[future]
                pid  = post["id"]

                with lock:
                    prog_state["processed"].append(pid)
                    prog_state["results"].append(res)
                    st.session_state.run_log.append(res)
                    save_progress(prog_state)
                    counter[0] += 1
                    progress_bar.progress(counter[0] / len(to_process))
                    status_txt.caption(f"Processing {counter[0]}/{len(to_process)}...")

                s = res["status"]
                pill_cls = "done" if s=="ok" else ("err" if s=="error" else ("skip" if s=="gate_fail" else "running"))
                pill_lbl = "✓ done" if s=="ok" else ("✗ failed" if s=="error" else ("⛔ gated" if s=="gate_fail" else "🟡 preview"))
                slots[pid].markdown(f"""
                <div class='post-row-ui'>
                  <div class='post-thumb {"has" if res.get("media_id") else ""}'>{"🖼️" if res.get("media_id") else "📄"}</div>
                  <div class='post-info'>
                    <div class='post-title-ui'>{res["title"]}</div>
                    <div class='post-meta-ui'>{res.get("word_count",0)} words{" · " + res.get("focus_keyword","") if res.get("focus_keyword") else ""}</div>
                  </div>
                  <span class='pill {pill_cls}'>{pill_lbl}</span>
                </div>
                """, unsafe_allow_html=True)

        ok_n   = sum(1 for r in prog_state["results"] if r["status"]=="ok")
        err_n  = sum(1 for r in prog_state["results"] if r["status"]=="error")
        gate_n = sum(1 for r in prog_state["results"] if r["status"]=="gate_fail")
        prev_n = sum(1 for r in prog_state["results"] if r["status"]=="preview")
        st.success(f"🎉 Done! ✅ {ok_n} optimized · 🟡 {prev_n} previewed · ⛔ {gate_n} gated · ❌ {err_n} errors")


# ════════════════════════════════════════════════════════════
#  FIX IMAGES TAB
# ════════════════════════════════════════════════════════════
elif active == "images":
    posts   = st.session_state.posts
    no_img  = [p for p in posts if not p.get("featured_media")]
    render_stats()

    st.markdown(f"""
    <div class="section-head">
      <h3>🖼️ Posts without featured image</h3>
      <span class="hint">{len(no_img)} posts need an image</span>
    </div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns([3,1])
    with c1:
        fix_all_btn = st.button(
            f"⚡ Generate images for all {len(no_img)} posts",
            type="primary", use_container_width=True,
            disabled=(not no_img or not ai_key)
        )
    with c2:
        if st.button("☑️ Select all → Optimizer", use_container_width=True):
            st.session_state.selected = [p["id"] for p in no_img]
            st.session_state.active_tab = "optimize"; st.rerun()

    if dry_run:
        st.warning("🟡 Sandbox mode — images generated but not uploaded.")

    st.markdown("<div class='post-table'>", unsafe_allow_html=True)
    for p in no_img:
        st.markdown(f"""
        <div class='post-row-ui'>
          <div class='post-thumb'>🚫</div>
          <div class='post-info'>
            <div class='post-title-ui'>{p["title"]["rendered"]}</div>
            <div class='post-meta-ui'>{p.get("status","?")} · {p.get("slug","")}</div>
          </div>
          <span class='pill noimg'>no image</span>
        </div>
        """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if fix_all_btn:
        auth = make_auth(wp_user, wp_pw)
        prog = st.progress(0)
        for i, post in enumerate(no_img):
            pid   = post["id"]
            title = post["title"]["rendered"]
            st.write(f"**⏳ {title}**")
            try:
                raw = run_ai(f"2-sentence photorealistic image prompt for '{title}'. Raw text only.",
                             provider, ai_key, ai_model, 0.1,
                             enable_fallback=enable_fallback, fallback_keys=fallback_keys)
                img_prompt = " ".join(raw.replace("*","").replace('"','').split())[:800]
                seo_alt    = run_ai(f"SEO image alt text under 120 chars for '{title}'. No quotes.",
                                    provider, ai_key, ai_model, 0.1,
                                    enable_fallback=enable_fallback, fallback_keys=fallback_keys).replace('"','')
                img_bytes = None
                for attempt in range(3):
                    try:
                        _use_dalle = image_provider == "DALL-E 3" and bool(dalle_key or ai_key)
                        img_bytes = gen_image_dalle(img_prompt, dalle_key or ai_key, dalle_style) if _use_dalle else gen_image_pollinations(img_prompt)
                        st.image(img_bytes, caption=seo_alt, width=320)
                        break
                    except Exception as e:
                        if attempt == 2: st.warning(f"Image failed: {e}")
                        else: time.sleep(3)

                if img_bytes and not dry_run:
                    media_id = upload_wp_image(img_bytes, title, seo_alt, auth, domain, optimize_seo_img)
                    wp_update_post(pid, {"featured_media": media_id}, auth, domain)
                    st.markdown('<span class="run-badge ok">✓ Uploaded</span>', unsafe_allow_html=True)
                elif img_bytes:
                    st.markdown('<span class="run-badge skip">🟡 Preview only</span>', unsafe_allow_html=True)
            except Exception as e:
                st.markdown(f'<span class="run-badge err">✗ {e}</span>', unsafe_allow_html=True)
            prog.progress((i+1)/len(no_img))
            time.sleep(0.5)
        st.success("✅ Image generation complete!")


# ════════════════════════════════════════════════════════════
#  CREATE POSTS TAB  —  with Smart 24h Scheduling
# ════════════════════════════════════════════════════════════
elif active == "create":
    st.markdown("""
    <div class='section-head'>
      <h3>✨ Create new posts with AI</h3>
      <span class='hint'>Full content · SEO · image · schema · smart scheduling</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='padding:0 28px'>", unsafe_allow_html=True)
    c1, c2 = st.columns([3,2])
    with c1:
        topics_raw = st.text_area("Topics — one per line",
            placeholder="10 easy vegan breakfast ideas\nHow to make oat milk at home\nBest plant-based protein sources",
            height=160)
        fix_lang = st.selectbox("Language", ["English","French","Spanish","Arabic","German","Italian","Portuguese"])
        fix_tone = st.selectbox("Tone", ["Informative & SEO-optimized","Conversational & friendly",
                                         "Professional & authoritative","Listicle / step-by-step","Story-driven"])
    with c2:
        fix_words     = st.select_slider("Word count target",
                                         options=[300,500,800,1200,1800,2500], value=800)
        pub_status    = st.radio("Publish as", ["draft","publish","private"], index=0,
                                 help="'draft' is safest — review before publishing.")
        auto_category = st.toggle("🤖 AI picks category automatically", value=True)
        cat_id = ""
        if not auto_category:
            cat_id = st.text_input("Category ID (manual)", placeholder="e.g. 5")
        tag_ids       = st.text_input("Tag IDs (optional)", placeholder="e.g. 12,34,56")
        create_img    = st.toggle("Generate featured image", value=True)
        create_seo    = st.toggle("SEO meta + Yoast/RankMath", value=True)
        create_schema = st.toggle("Schema.org JSON-LD", value=True)
        create_dry    = st.toggle("Sandbox — preview only", value=True)
    st.markdown("</div>", unsafe_allow_html=True)

    topics_preview = [t.strip() for t in (topics_raw or "").strip().splitlines() if t.strip()]
    n_topics = len(topics_preview)

    if enable_schedule and n_topics > 0:
        _slots_prev = calculate_post_schedule(n_topics, posts_per_day, schedule_start_h, start_from_now)
        _now_utc    = datetime.utcnow()
        _future_c   = sum(1 for s in _slots_prev if s > _now_utc)
        _immed_c    = n_topics - _future_c
        _last_slot  = _slots_prev[-1].strftime("%d %b %H:%M UTC") if _slots_prev else "—"
        st.markdown(f"""
        <div style='margin:0 24px 14px;padding:14px 18px;
            background:rgba(55,138,221,0.07);border:1px solid rgba(55,138,221,0.2);
            border-radius:12px'>
          <div style='display:flex;align-items:center;gap:10px;margin-bottom:10px'>
            <span style='font-size:20px'>⏰</span>
            <span style='font-size:13.5px;font-weight:600;color:#378ADD'>
              Smart scheduling: {n_topics} posts · 1 every {_interval_min} min
            </span>
            <span style='margin-left:auto;font-size:12px;font-weight:600;
                background:rgba(55,138,221,0.15);color:#378ADD;
                border:1px solid rgba(55,138,221,0.3);border-radius:999px;
                padding:2px 10px'>
              last post: {_last_slot}
            </span>
          </div>
          <div style='display:flex;gap:20px;font-size:12px'>
            <span style='color:#378ADD'>🕐 {_future_c} will be scheduled (future)</span>
            <span style='color:#1D9E75'>⚡ {_immed_c} published immediately (past slots)</span>
            <span style='color:rgba(var(--muted-rgb),0.5)'>delay between calls: {delay_between_api}s</span>
          </div>
        </div>
        """, unsafe_allow_html=True)

        if n_topics > 0:
            rows_html = ""
            for i, slot in enumerate(_slots_prev[:8]):
                is_future = slot > _now_utc
                topic_lbl = topics_preview[i] if i < len(topics_preview) else f"Post {i+1}"
                rows_html += f"""
                <div class='sched-row'>
                  <div class='sched-idx'>{i+1}</div>
                  <span class='sched-time'>{slot.strftime("%d %b · %H:%M")} UTC</span>
                  <span class='sched-label'>{topic_lbl}</span>
                  <span class='sched-status {"future" if is_future else "now"}'>
                    {"🕐 future" if is_future else "⚡ now"}
                  </span>
                </div>"""
            if n_topics > 8:
                rows_html += f"""
                <div class='sched-row' style='color:rgba(var(--muted-rgb),0.4);font-size:12px;justify-content:center'>
                  … and {n_topics - 8} more posts up to {_last_slot}
                </div>"""
            st.markdown(f"""
            <div class='sched-card' style='margin:0 24px 14px'>
              <div class='sched-card-head'>
                <span class='sched-card-title'>📅 Publish schedule preview</span>
                <span class='sched-card-badge'>{n_topics} posts · {_interval_min} min apart</span>
              </div>
              {rows_html}
            </div>
            """, unsafe_allow_html=True)
    elif not enable_schedule and n_topics > 0:
        st.info(f"ℹ️ Scheduling is OFF — all {n_topics} posts will be published immediately as '{pub_status}'.")

    if create_dry:
        st.warning("🟡 Sandbox — posts will be previewed but not pushed to WordPress.")
    else:
        st.error("🔴 Live — posts will be created directly on your WordPress site.")

    st.markdown("<div style='padding:0 28px 20px'>", unsafe_allow_html=True)
    create_btn = st.button("✨ Generate & schedule posts now", type="primary", use_container_width=True,
                           disabled=(not topics_raw.strip() or not ai_key))
    st.markdown("</div>", unsafe_allow_html=True)

    if create_btn:
        auth   = make_auth(wp_user, wp_pw)
        topics = [t.strip() for t in topics_raw.strip().splitlines() if t.strip()]

        if enable_schedule:
            schedule_slots = calculate_post_schedule(len(topics), posts_per_day, schedule_start_h, start_from_now)
        else:
            schedule_slots = [None] * len(topics)

        prog = st.progress(0)
        created_ok, created_err = [], []
        now_utc = datetime.utcnow()

        for i, topic in enumerate(topics):
            scheduled_dt = schedule_slots[i]

            if enable_schedule and scheduled_dt and scheduled_dt > now_utc:
                wp_status = "future"
                date_iso  = scheduled_dt.strftime("%Y-%m-%dT%H:%M:%S")
                sched_label = scheduled_dt.strftime("%d %b · %H:%M UTC")
            elif enable_schedule and scheduled_dt:
                wp_status = pub_status
                date_iso  = scheduled_dt.strftime("%Y-%m-%dT%H:%M:%S")
                sched_label = "⚡ immediate (past slot)"
            else:
                wp_status = pub_status
                date_iso  = None
                sched_label = "immediate"

            st.markdown(f"""
            <div class='panel-box' style='margin:0 28px 12px'>
              <div class='panel-box-head'>
                <h4>{"⏰" if wp_status=="future" else "⚡"} {topic}</h4>
                <span class='hint'>{"🕐 " + sched_label if enable_schedule else "no schedule"}</span>
              </div>
            """, unsafe_allow_html=True)
            col1, col2 = st.columns([3,1])

            try:
                manual_cat = int(cat_id.strip()) if (not auto_category and cat_id.strip().isdigit()) else None
                tids = [int(t.strip()) for t in tag_ids.split(",") if t.strip().isdigit()] if tag_ids.strip() else None

                result = build_and_publish_post(
                    topic, domain, auth, language=fix_lang, tone=fix_tone, word_count=fix_words,
                    wp_status=wp_status, date_iso=date_iso, do_image=create_img, do_seo=create_seo,
                    do_schema=create_schema, auto_category=auto_category, manual_category_id=manual_cat,
                    tag_ids=tids, is_dry_run=create_dry, progress_cb=lambda msg: col1.info(msg))

                if result.get("category_name"):
                    col1.caption(f"🏷️ AI chose: **{result['category_name']}** (id {result['category_id']})")
                if result.get("image_bytes"):
                    col2.image(result["image_bytes"], caption=result.get("image_alt", ""))
                elif create_img and result.get("error"):
                    col1.warning(result["error"])

                if create_dry:
                    with col1:
                        badge = "sched" if wp_status == "future" else "skip"
                        label = f"🕐 Would schedule: {sched_label}" if wp_status == "future" else "🟡 Preview only"
                        st.markdown(f'<span class="run-badge {badge}">{label}</span>', unsafe_allow_html=True)
                        with st.expander("View generated content & schedule"):
                            if result["meta_desc"]: st.write(f"**Meta:** {result['meta_desc']}")
                            if result["focus_kw"]:  st.write(f"**KW:** {result['focus_kw']}")
                            if result["excerpt"]:   st.write(f"**Excerpt:** {result['excerpt']}")
                            st.write(f"**WP Status:** `{wp_status}`")
                            if date_iso:  st.write(f"**Scheduled date:** `{date_iso}` UTC")
                            st.code(result["content_html"][:1500]+"... (truncated)", language="html")
                    created_ok.append(topic)

                elif result["ok"]:
                    with col1:
                        if wp_status == "future":
                            st.markdown(f'<span class="run-badge sched">🕐 Scheduled: {sched_label}</span>',
                                        unsafe_allow_html=True)
                        else:
                            st.markdown('<span class="run-badge ok">✅ Published</span>', unsafe_allow_html=True)
                        st.caption(f"Post #{result['post_id']} · {result['link']}")
                    st.session_state.created_log.append({
                        "topic": topic, "id": result["post_id"], "link": result["link"],
                        "scheduled": date_iso if wp_status == "future" else ""
                    })
                    created_ok.append(topic)

                else:
                    with col1:
                        st.markdown(f'<span class="run-badge err">❌ {result["error"]}</span>', unsafe_allow_html=True)
                    created_err.append(topic)

            except Exception as e:
                with col1: st.error(f"Error: {e}")
                created_err.append(topic)

            st.markdown("</div>", unsafe_allow_html=True)
            prog.progress((i+1)/len(topics))

            if i < len(topics) - 1:
                with col1:
                    st.caption(f"⏸️ Waiting {delay_between_api}s before next post…")
                time.sleep(delay_between_api)

        sched_done = sum(1 for c in st.session_state.created_log[-len(topics):]
                         if c.get("scheduled"))
        st.success(
            f"✨ Done! "
            f"⏰ {sched_done} scheduled · "
            f"✅ {len(created_ok)-sched_done} published immediately · "
            f"❌ {len(created_err)} failed"
        )


# ════════════════════════════════════════════════════════════
#  SEO TAB
# ════════════════════════════════════════════════════════════
elif active == "seo":
    posts = st.session_state.posts
    render_stats()

    st.markdown("""
    <div class='section-head'>
      <h3>🔍 SEO batch optimizer</h3>
      <span class='hint'>Meta descriptions · Focus keywords · Yoast · RankMath</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='padding:0 28px 20px'>", unsafe_allow_html=True)
    seo_only_btn = st.button(
        f"🔍 Run SEO only on {len(st.session_state.selected)} selected posts",
        type="primary", use_container_width=True,
        disabled=(not st.session_state.selected or not ai_key)
    )
    st.markdown("</div>", unsafe_allow_html=True)

    if seo_only_btn:
        auth  = make_auth(wp_user, wp_pw)
        to_do = [p for p in posts if p["id"] in st.session_state.selected]
        prog  = st.progress(0)
        for i, post in enumerate(to_do):
            pid   = post["id"]
            title = post["title"]["rendered"]
            ohtml = post["content"]["rendered"]
            plain = BeautifulSoup(ohtml,"html.parser").get_text()
            try:
                seo = generate_seo_meta(title, plain, provider, ai_key, ai_model,
                                        enable_fallback, fallback_keys)
                meta_desc = seo.get("meta_description","")
                focus_kw  = seo.get("focus_keyword","")
                exc_text  = seo.get("excerpt","")
                if not dry_run:
                    wp_update_post(pid, {"excerpt":exc_text}, auth, domain)
                    update_yoast_meta(pid, meta_desc, focus_kw, auth, domain)
                st.markdown(f"""
                <div class='post-row-ui'>
                  <div class='post-thumb has'>✓</div>
                  <div class='post-info'>
                    <div class='post-title-ui'>{title}</div>
                    <div class='post-meta-ui'><b>KW:</b> {focus_kw} · <b>Meta:</b> {meta_desc[:80]}...</div>
                  </div>
                  <span class='pill {"done" if not dry_run else "running"}'>
                    {"✓ pushed" if not dry_run else "🟡 preview"}
                  </span>
                </div>
                """, unsafe_allow_html=True)
            except Exception as e:
                st.error(f"{title}: {e}")
            prog.progress((i+1)/len(to_do))
            time.sleep(0.5)
        st.success("✅ SEO optimization complete!")


# ════════════════════════════════════════════════════════════
#  THEME & DESIGN TAB
# ════════════════════════════════════════════════════════════
elif active == "design":
    posts = st.session_state.posts
    render_stats()

    st.markdown("""
    <div class='section-head'>
      <h3>🎨 Theme & Design</h3>
      <span class='hint'>Site identity · Colors & typography · Media library · Homepage layout</span>
    </div>
    """, unsafe_allow_html=True)

    if not (domain and wp_user and wp_pw):
        st.warning("⚠️ Connect your WordPress site in the sidebar first.")
    else:
        auth = make_auth(wp_user, wp_pw)
        if dry_run:
            st.info("🟡 Sandbox mode is ON — every change below previews only; nothing writes to WordPress until you turn Sandbox off in the sidebar.")

        cmd_tab, id_tab, color_tab, media_tab, layout_tab = st.tabs(
            ["🪄 AI Command", "🏷️ Site Identity", "🎨 Color & Typography", "🖼️ Media Library", "📰 Homepage Layout"]
        )

        # ════════════════════════════════════════════════════
        # 0. AI COMMAND — one prompt (+ optional image) fixes it
        # ════════════════════════════════════════════════════
        with cmd_tab:
            st.markdown(
                "<div class='hint' style='padding-bottom:10px'>Describe what you want changed — site title/tagline, "
                "logo, favicon, or color palette — attach an image if you have one, and I'll plan the exact steps "
                "before touching your site.</div>", unsafe_allow_html=True
            )

            cmd_upload = st.file_uploader("Attach an image (optional)", type=["png", "jpg", "jpeg", "webp"], key="design_cmd_uploader")
            if cmd_upload is not None:
                st.session_state.design_cmd_image = cmd_upload.read()
            if st.session_state.design_cmd_image:
                ic1, ic2 = st.columns([1, 4])
                with ic1:
                    st.image(st.session_state.design_cmd_image, width=100)
                with ic2:
                    st.caption("Attached — will be used by logo/favicon actions instead of AI-generating one.")
                    if st.button("✖ Remove image", key="design_cmd_remove_img"):
                        st.session_state.design_cmd_image = None
                        st.rerun()

            for msg in st.session_state.design_cmd_log:
                with st.chat_message("assistant" if msg["role"] == "assistant" else "user"):
                    st.markdown(msg["text"])

            dc1, dc2 = st.columns([5, 1])
            with dc1:
                design_prompt = st.text_input(
                    "Command", key="design_cmd_text", label_visibility="collapsed",
                    placeholder="e.g. Set my site title to 'Bloom & Co' and use this image as the logo"
                )
            with dc2:
                design_plan_clicked = st.button("Plan it →", key="design_cmd_plan_btn", use_container_width=True,
                                                disabled=not (design_prompt.strip() and ai_key))
            if not ai_key:
                st.caption("Add an AI API key in the sidebar to use this.")

            if design_plan_clicked and design_prompt.strip():
                st.session_state.design_cmd_log.append({"role": "user", "text": design_prompt.strip()})
                context_summary = (
                    f"connected to {domain}, sandbox={'on' if dry_run else 'off'}, "
                    f"{'an image is attached' if st.session_state.design_cmd_image else 'no image is attached'}."
                )
                with st.spinner("Planning..."):
                    plan = run_agent_planner(design_prompt.strip(), context_summary, tools=DESIGN_TOOLS)
                st.session_state.design_cmd_plan = plan["steps"]
                st.session_state.design_cmd_log.append({"role": "assistant", "text": plan["reply"]})
                st.rerun()

            if st.session_state.design_cmd_plan:
                st.markdown("<div class='panel-box' style='margin-top:10px'>", unsafe_allow_html=True)
                st.markdown("**Proposed steps** — review before I run anything:")
                keep = []
                for i, step in enumerate(st.session_state.design_cmd_plan):
                    args_str = f" _(args: {step['args']})_" if step["args"] else ""
                    checked = st.checkbox(f"**{step['tool']}** — {step.get('why','')}{args_str}",
                                          value=True, key=f"design_cmd_step_{i}")
                    if checked: keep.append(step)
                rc1, rc2 = st.columns(2)
                with rc1:
                    if st.button("▶️ Run selected steps", type="primary", use_container_width=True, key="design_cmd_run"):
                        auth = make_auth(wp_user, wp_pw)
                        for step in keep:
                            ok, msg = execute_agent_tool(step["tool"], step["args"], auth, domain, dry_run,
                                                         uploaded_image=st.session_state.design_cmd_image)
                            st.session_state.design_cmd_log.append({"role": "assistant", "text": ("✅ " if ok else "⚠️ ") + msg})
                        st.session_state.design_cmd_plan = []
                        st.session_state.design_wp_settings = None
                        st.session_state.design_global_styles = None
                        st.rerun()
                with rc2:
                    if st.button("✖️ Discard plan", use_container_width=True, key="design_cmd_discard"):
                        st.session_state.design_cmd_plan = []
                        st.session_state.design_cmd_log.append({"role": "assistant", "text": "Okay, discarded that plan."})
                        st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

            if st.session_state.design_cmd_log:
                if st.button("🔄 Clear conversation", key="design_cmd_clear"):
                    st.session_state.design_cmd_log = []
                    st.session_state.design_cmd_plan = []
                    st.session_state.design_cmd_image = None
                    st.rerun()

        # ════════════════════════════════════════════════════
        # 1. SITE IDENTITY
        # ════════════════════════════════════════════════════
        with id_tab:
            if st.session_state.design_wp_settings is None:
                with st.spinner("Loading site settings..."):
                    settings, serr = fetch_wp_settings(auth, domain)
                    st.session_state.design_wp_settings = settings or {}
                    if serr:
                        st.error(f"Couldn't load site settings: {serr}")

            settings = st.session_state.design_wp_settings or {}
            st.markdown("<div class='panel-box'>", unsafe_allow_html=True)
            st.markdown("""<div class='panel-box-head'><h4>📝 Site title & tagline</h4>
                <span class='hint'>/wp-json/wp/v2/settings</span></div>""", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                site_title = st.text_input("Site Title", value=settings.get("title", ""), key="design_site_title")
            with c2:
                tagline = st.text_input("Tagline", value=settings.get("description", ""), key="design_tagline")

            if st.button("💾 Save site title & tagline", disabled=not settings, key="save_identity"):
                if dry_run:
                    st.warning(f"🟡 Sandbox preview — would set title=\"{site_title}\", tagline=\"{tagline}\".")
                else:
                    with st.spinner("Saving to WordPress..."):
                        ok, msg = update_wp_settings({"title": site_title, "description": tagline}, auth, domain)
                    if ok:
                        st.session_state.design_wp_settings["title"] = site_title
                        st.session_state.design_wp_settings["description"] = tagline
                        st.success(f"✅ {msg}")
                    else:
                        st.error(f"❌ {msg}")
            st.markdown("</div>", unsafe_allow_html=True)

            # ---------- Logo ----------
            st.markdown("<div class='panel-box' style='margin-top:14px'>", unsafe_allow_html=True)
            st.markdown("""<div class='panel-box-head'><h4>🖼️ Site logo</h4>
                <span class='hint'>Upload or AI-generate, preview before applying</span></div>""", unsafe_allow_html=True)

            logo_mode = st.radio("Logo source", ["Upload a file", "Generate with AI"], horizontal=True, key="logo_mode")
            if logo_mode == "Upload a file":
                logo_file = st.file_uploader("Choose an image", type=["png", "jpg", "jpeg", "webp"], key="logo_upload")
                if logo_file:
                    st.session_state.design_logo_preview = logo_file.read()
            else:
                logo_prompt = st.text_input("Describe the logo you want",
                    placeholder="Minimalist blue mountain peak, flat vector, transparent background", key="logo_prompt")
                if st.button("🎨 Generate logo", disabled=not (logo_prompt and ai_key), key="gen_logo"):
                    with st.spinner("Generating logo with AI..."):
                        try:
                            _use_dalle = image_provider == "DALL-E 3" and bool(dalle_key or ai_key)
                            st.session_state.design_logo_preview = (
                                gen_image_dalle(logo_prompt, dalle_key or ai_key, dalle_style) if _use_dalle
                                else gen_image_pollinations(logo_prompt)
                            )
                        except Exception as e:
                            st.error(f"Logo generation failed: {friendly_error(e)}")

            if st.session_state.design_logo_preview:
                st.image(st.session_state.design_logo_preview, width=240, caption="Preview — not applied yet")
                if st.button("✅ Confirm & upload this logo", type="primary", key="confirm_logo"):
                    if dry_run:
                        st.warning("🟡 Sandbox preview — would upload this image to your media library and use it as the site logo.")
                        st.session_state.design_logo_preview = None
                    else:
                        with st.spinner("Uploading logo to your media library..."):
                            try:
                                media_id = upload_wp_image(st.session_state.design_logo_preview, "Site Logo", "Site logo", auth, domain, True)
                            except Exception as e:
                                media_id = None
                                st.error(f"Upload failed: {friendly_error(e)}")
                        if media_id:
                            st.success(f"✅ Uploaded to your media library (media ID {media_id}).")
                            st.info(
                                "WordPress doesn't expose the site logo (`custom_logo`) through the core REST API "
                                "the way it does the site icon below — that's a real platform limitation, not "
                                "something this app is skipping. Finish it in one click: **Appearance → Editor → "
                                "Styles → Site Identity** (or **Customize → Site Identity** on classic themes) and "
                                "pick the image you just uploaded — it'll be the most recent item in your Media Library."
                            )
                        st.session_state.design_logo_preview = None
            st.markdown("</div>", unsafe_allow_html=True)

            # ---------- Site icon / favicon ----------
            st.markdown("<div class='panel-box' style='margin-top:14px'>", unsafe_allow_html=True)
            st.markdown("""<div class='panel-box-head'><h4>🔖 Site icon (favicon)</h4>
                <span class='hint'>Auto-cropped to a 512×512 square</span></div>""", unsafe_allow_html=True)

            icon_mode = st.radio("Icon source", ["Upload a file", "Generate with AI"], horizontal=True, key="icon_mode")
            if icon_mode == "Upload a file":
                icon_file = st.file_uploader("Choose an image", type=["png", "jpg", "jpeg", "webp"], key="icon_upload")
                if icon_file:
                    try:
                        st.session_state.design_favicon_preview = crop_square(icon_file.read(), 512)
                    except Exception as e:
                        st.error(str(e))
            else:
                icon_prompt = st.text_input("Describe the icon",
                    placeholder="Simple flat mountain peak icon, single color, no text", key="icon_prompt")
                if st.button("🎨 Generate icon", disabled=not (icon_prompt and ai_key), key="gen_icon"):
                    with st.spinner("Generating icon with AI..."):
                        try:
                            _use_dalle = image_provider == "DALL-E 3" and bool(dalle_key or ai_key)
                            raw_bytes = (gen_image_dalle(icon_prompt, dalle_key or ai_key, dalle_style) if _use_dalle
                                        else gen_image_pollinations(icon_prompt))
                            st.session_state.design_favicon_preview = crop_square(raw_bytes, 512)
                        except Exception as e:
                            st.error(f"Icon generation failed: {friendly_error(e)}")

            if st.session_state.design_favicon_preview:
                st.image(st.session_state.design_favicon_preview, width=128, caption="512×512 preview")
                if st.button("✅ Confirm & set as site icon", type="primary", key="confirm_icon"):
                    if dry_run:
                        st.warning("🟡 Sandbox preview — would upload this image and set it as the site icon.")
                        st.session_state.design_favicon_preview = None
                    else:
                        with st.spinner("Uploading icon..."):
                            try:
                                media_id = upload_wp_image(st.session_state.design_favicon_preview, "Site Icon", "Site icon", auth, domain, True)
                            except Exception as e:
                                media_id = None
                                st.error(f"Upload failed: {friendly_error(e)}")
                        if media_id:
                            with st.spinner("Setting as site icon..."):
                                ok, msg = update_wp_settings({"site_icon": media_id}, auth, domain)
                            if ok:
                                st.success(f"✅ Site icon set (media ID {media_id}).")
                            else:
                                st.error(f"❌ {msg}")
                        st.session_state.design_favicon_preview = None
            st.markdown("</div>", unsafe_allow_html=True)

        # ════════════════════════════════════════════════════
        # 2. COLOR & TYPOGRAPHY
        # ════════════════════════════════════════════════════
        with color_tab:
            if st.session_state.design_theme_info is None:
                with st.spinner("Detecting your active theme..."):
                    theme_info, terr = fetch_active_theme_info(auth, domain)
                    st.session_state.design_theme_info = theme_info or {}
                    if terr:
                        st.error(f"Couldn't detect the active theme: {terr}")

            theme_info = st.session_state.design_theme_info or {}
            theme_name = (theme_info.get("name") or {}).get("rendered") or "Unknown"
            theme_slug = theme_info.get("stylesheet", "")

            if theme_slug and st.session_state.design_global_styles is None:
                with st.spinner("Reading current color palette from theme.json..."):
                    gstyles, gerr = fetch_global_styles(theme_slug, auth, domain)
                    st.session_state.design_global_styles = gstyles if gstyles else {}

            gstyles = st.session_state.design_global_styles or {}
            is_block_theme = bool(gstyles)

            if not theme_info:
                st.warning("Couldn't detect your active theme — this Application Password's user likely lacks `edit_theme_options`. You can still pick a palette and use the copy-paste snippet below.")
            else:
                st.markdown(f"**Active theme:** {theme_name}" +
                            (" · 🧩 Global Styles available (block theme)" if is_block_theme else " · Classic theme — no theme.json / Global Styles"))

            if is_block_theme:
                current_palette = ((gstyles.get("settings") or {}).get("color") or {}).get("palette") or []
                if current_palette:
                    st.markdown("**Current palette:**")
                    swatch_html = "".join(
                        f"<div style='display:inline-flex;flex-direction:column;align-items:center;margin-right:14px;'>"
                        f"<div style='width:36px;height:36px;border-radius:8px;background:{c.get('color','#ccc')};border:1px solid rgba(127,119,221,0.25)'></div>"
                        f"<span style='font-size:11px;color:rgba(var(--muted-rgb),0.7);margin-top:4px'>{c.get('name','')}</span></div>"
                        for c in current_palette[:8]
                    )
                    st.markdown(f"<div style='padding:6px 0 16px'>{swatch_html}</div>", unsafe_allow_html=True)
            elif theme_info:
                st.info("This classic theme has no theme.json, so there's no live palette to read. Pick a palette below to get a copy-paste snippet for your theme's own Customizer color options, or for when you switch to a block theme.")

            preset_name = st.selectbox("Preset palette", list(PALETTE_PRESETS.keys()) + ["Custom"], key="palette_preset")
            if preset_name == "Custom":
                base = st.session_state.design_palette_preview or {"primary": "#1F2937", "secondary": "#374151", "accent": "#3B82F6", "text": "#111827"}
                c1, c2, c3, c4 = st.columns(4)
                with c1: primary = st.color_picker("Primary", base["primary"], key="pp_primary")
                with c2: secondary = st.color_picker("Secondary", base["secondary"], key="pp_secondary")
                with c3: accent = st.color_picker("Accent", base["accent"], key="pp_accent")
                with c4: text_c = st.color_picker("Text", base["text"], key="pp_text")
                palette = {"primary": primary, "secondary": secondary, "accent": accent, "text": text_c}
            else:
                palette = PALETTE_PRESETS[preset_name]
                cols = st.columns(4)
                for col, (label, hexval) in zip(cols, palette.items()):
                    with col:
                        st.markdown(
                            f"<div style='text-align:center'><div style='width:100%;height:44px;border-radius:8px;"
                            f"background:{hexval};border:1px solid rgba(127,119,221,0.25)'></div>"
                            f"<span style='font-size:11px;color:rgba(var(--muted-rgb),0.7)'>{label.title()}: {hexval}</span></div>",
                            unsafe_allow_html=True
                        )
            st.session_state.design_palette_preview = palette

            st.markdown("**Live preview:**")
            st.markdown(f"""
            <div style='border-radius:14px;overflow:hidden;border:1px solid rgba(127,119,221,0.2);margin:10px 0 18px'>
              <div style='background:{palette["primary"]};padding:16px 20px;'>
                <div style='color:{palette["accent"]};font-weight:700;font-size:16px'>Your Site Name</div>
                <div style='color:{palette["accent"]};opacity:0.8;font-size:12px'>Home · About · Blog · Contact</div>
              </div>
              <div style='background:#fff;padding:20px;'>
                <div style='color:{palette["text"]};font-size:14px;font-weight:600;margin-bottom:6px'>A sample headline in your new palette</div>
                <div style='color:{palette["text"]};opacity:0.75;font-size:13px;margin-bottom:12px'>Body content renders against a white content area on most block themes, regardless of the site-wide color scheme above.</div>
                <span style='display:inline-block;background:{palette["accent"]};color:{palette["primary"]};padding:8px 16px;border-radius:8px;font-size:13px;font-weight:600'>Sample Button</span>
              </div>
            </div>
            """, unsafe_allow_html=True)

            snippet = build_style_variation_snippet(palette)
            c1, c2 = st.columns(2)
            with c1:
                apply_disabled = not is_block_theme or dry_run
                if st.button("⚡ Try direct apply (experimental)", disabled=apply_disabled,
                             help="Only works on block themes with Global Styles exposed via REST, and only when Sandbox mode is off.",
                             key="apply_global_styles"):
                    with st.spinner("Writing to your site's Global Styles..."):
                        ok, msg = apply_global_styles_colors(palette, auth, domain, theme_info)
                    if ok:
                        st.success(f"✅ {msg}")
                        st.session_state.design_global_styles = None
                    else:
                        st.error(f"❌ {msg}")
                if dry_run and is_block_theme:
                    st.caption("🟡 Sandbox mode is on — turn it off in the sidebar to enable direct apply.")
            with c2:
                st.download_button("⬇️ Download style-variation.json", data=snippet,
                                   file_name="style-variation.json", mime="application/json",
                                   use_container_width=True, key="dl_snippet")

            with st.expander("📋 Copy-paste snippet & instructions (always safe, works on any theme)"):
                st.code(snippet, language="json")
                st.markdown("""
**Where to use this:**
1. Save it as `style-variation.json` inside your active theme's `/styles/` folder (e.g. `wp-content/themes/your-theme/styles/style-variation.json`), then reload the Site Editor — it appears as a selectable style under **Appearance → Editor → Styles → Browse styles**.
2. Or merge just the `settings.color.palette` array into your theme's existing `theme.json` under `settings.color.palette`, and the `styles.color` block under `styles.color`.
3. Classic (non-block) themes don't read theme.json at all — use this as a reference for your theme's own Customizer color options instead (**Appearance → Customize → Colors**).
                """)

        # ════════════════════════════════════════════════════
        # 3. PHOTO / IMAGE LIBRARY MANAGER
        # ════════════════════════════════════════════════════
        with media_tab:
            no_img_posts = [p for p in posts if not p.get("featured_media")]
            if no_img_posts:
                st.markdown(f"<div class='hint' style='padding:0 0 10px'>⚠️ {len(no_img_posts)} loaded post(s) have no featured image</div>", unsafe_allow_html=True)
                for p in no_img_posts[:10]:
                    pid, title = p["id"], p["title"]["rendered"]
                    c1, c2 = st.columns([4, 1])
                    with c1:
                        st.markdown(
                            f"<div class='post-row-ui'><div class='post-thumb'>🚫</div>"
                            f"<div class='post-info'><div class='post-title-ui'>{title}</div></div>"
                            f"<span class='pill noimg'>no image</span></div>",
                            unsafe_allow_html=True
                        )
                    with c2:
                        if st.button("✨ Generate & Set", key=f"genimg_{pid}", disabled=not ai_key, use_container_width=True):
                            with st.spinner(f"Generating a featured image for \"{title}\"..."):
                                try:
                                    raw = run_ai(f"2-sentence photorealistic image prompt for a blog post titled '{title}'. Raw text only.",
                                                 provider, ai_key, ai_model, 0.1,
                                                 enable_fallback=enable_fallback, fallback_keys=fallback_keys)
                                    img_prompt = " ".join(raw.replace("*", "").replace('"', "").split())[:800]
                                    alt = generate_alt_text(title, provider, ai_key, ai_model, enable_fallback, fallback_keys)
                                    _use_dalle = image_provider == "DALL-E 3" and bool(dalle_key or ai_key)
                                    img_bytes = (gen_image_dalle(img_prompt, dalle_key or ai_key, dalle_style) if _use_dalle
                                                else gen_image_pollinations(img_prompt))
                                    if dry_run:
                                        st.image(img_bytes, width=200)
                                        st.warning("🟡 Sandbox preview — image generated but not uploaded.")
                                    else:
                                        media_id = upload_wp_image(img_bytes, title, alt, auth, domain, optimize_seo_img)
                                        wp_update_post(pid, {"featured_media": media_id}, auth, domain)
                                        p["featured_media"] = media_id
                                        st.success(f"✅ Featured image set for \"{title}\".")
                                except Exception as e:
                                    st.error(f"Failed: {friendly_error(e)}")
                st.markdown("<hr style='border-color:rgba(127,119,221,0.15);margin:18px 0'>", unsafe_allow_html=True)

            per_page = 12
            page = st.session_state.design_media_page
            pc1, pc2, pc3 = st.columns([1, 2, 1])
            with pc1:
                if st.button("◀ Previous", disabled=page <= 1, key="media_prev"):
                    st.session_state.design_media_page -= 1
                    st.session_state.design_media_cache = None
                    st.rerun()
            with pc2:
                st.markdown(f"<div style='text-align:center;padding-top:6px'>Page {page}</div>", unsafe_allow_html=True)
            with pc3:
                if st.button("Next ▶", key="media_next"):
                    st.session_state.design_media_page += 1
                    st.session_state.design_media_cache = None
                    st.rerun()

            if st.session_state.design_media_cache is None:
                with st.spinner(f"Loading media library page {page}..."):
                    media_items, total_pages, merr = fetch_media_library(auth, domain, page, per_page)
                    st.session_state.design_media_cache = (media_items, total_pages, merr)
            media_items, total_pages, merr = st.session_state.design_media_cache

            if merr:
                st.error(f"Couldn't load media library: {merr}")
            elif not media_items:
                st.info("No images found in your media library.")
            else:
                st.caption(f"Page {page} of {total_pages}")
                cols = st.columns(4)
                for i, item in enumerate(media_items):
                    with cols[i % 4]:
                        st.image(item.get("source_url", ""), use_container_width=True)
                        dims = item.get("media_details", {}) or {}
                        w, h = dims.get("width", "?"), dims.get("height", "?")
                        item_title = (item.get("title", {}) or {}).get("rendered", "(untitled)")
                        st.caption(f"{item_title[:28]}\n{w}×{h}")
                        used = find_posts_using_media(item, posts)
                        st.caption(("Used in: " + ", ".join(u["title"][:20] for u in used[:2])) if used else "Not used in any loaded post")

                        if not (item.get("alt_text") or "").strip():
                            if st.button("🔍 Alt text", key=f"alt_{item['id']}", disabled=not ai_key, use_container_width=True):
                                with st.spinner("Writing alt text..."):
                                    try:
                                        alt = generate_alt_text(item_title or "image", provider, ai_key, ai_model, enable_fallback, fallback_keys)
                                        if dry_run:
                                            st.warning(f"🟡 Preview: \"{alt}\"")
                                        else:
                                            ar = requests.post(f"https://{domain}/wp-json/wp/v2/media/{item['id']}",
                                                               headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"},
                                                               json={"alt_text": alt}, timeout=30)
                                            if ar.status_code == 200:
                                                st.success(f"✅ \"{alt}\"")
                                            else:
                                                st.error(f"HTTP {ar.status_code}: {ar.text[:200]}")
                                    except Exception as e:
                                        st.error(friendly_error(e))

                        with st.expander("Replace / re-compress"):
                            new_file = st.file_uploader("Upload replacement", type=["png", "jpg", "jpeg", "webp"], key=f"replace_{item['id']}")
                            rc1, rc2 = st.columns(2)
                            with rc1:
                                if st.button("🔁 Replace", key=f"doreplace_{item['id']}", disabled=not new_file, use_container_width=True):
                                    if dry_run:
                                        st.warning("🟡 Sandbox preview — would upload a replacement and repoint any posts using this image.")
                                    else:
                                        with st.spinner("Uploading replacement and repointing posts..."):
                                            try:
                                                new_id = upload_wp_image(new_file.read(), item_title or "image", item.get("alt_text", ""), auth, domain, True)
                                                nr = requests.get(f"https://{domain}/wp-json/wp/v2/media/{new_id}",
                                                                 headers={"Authorization": f"Basic {auth}"}, params={"_fields": "source_url"}, timeout=20)
                                                new_url = nr.json().get("source_url", "") if nr.status_code == 200 else ""
                                                repoint_results = repoint_media_references(item, new_id, new_url, posts, auth, domain, is_dry_run=False)
                                                st.success(f"✅ Replacement uploaded (media ID {new_id}). Updated {len(repoint_results)} post(s). The old image stays in your media library — remove it manually if you don't need it.")
                                            except Exception as e:
                                                st.error(friendly_error(e))
                            with rc2:
                                if st.button("📦 Re-compress", key=f"recompress_{item['id']}", use_container_width=True):
                                    with st.spinner("Checking size and re-compressing if needed..."):
                                        try:
                                            new_bytes = recompress_image(item)
                                            if new_bytes is None:
                                                st.info("Already within size budget — nothing to do.")
                                            elif dry_run:
                                                st.warning(f"🟡 Sandbox preview — would re-compress to ~{len(new_bytes)//1024} KB and replace.")
                                            else:
                                                new_id = upload_wp_image(new_bytes, item_title or "image", item.get("alt_text", ""), auth, domain, True)
                                                nr = requests.get(f"https://{domain}/wp-json/wp/v2/media/{new_id}",
                                                                 headers={"Authorization": f"Basic {auth}"}, params={"_fields": "source_url"}, timeout=20)
                                                new_url = nr.json().get("source_url", "") if nr.status_code == 200 else ""
                                                repoint_results = repoint_media_references(item, new_id, new_url, posts, auth, domain, is_dry_run=False)
                                                st.success(f"✅ Re-compressed to {len(new_bytes)//1024} KB (media ID {new_id}). Updated {len(repoint_results)} post(s).")
                                        except Exception as e:
                                            st.error(friendly_error(e))

        # ════════════════════════════════════════════════════
        # 4. HOMEPAGE / TICKER LAYOUT
        # ════════════════════════════════════════════════════
        with layout_tab:
            if st.session_state.design_patterns is None:
                with st.spinner("Checking your theme for ticker / breaking-news block patterns..."):
                    patterns, perr = fetch_block_patterns(auth, domain)
                    st.session_state.design_patterns = patterns
                    if perr:
                        st.error(f"Couldn't check block patterns: {perr}")
            patterns = st.session_state.design_patterns or []
            hits = find_ticker_patterns(patterns)

            if st.session_state.design_wp_settings is None:
                settings, serr = fetch_wp_settings(auth, domain)
                st.session_state.design_wp_settings = settings or {}
            page_id = get_homepage_page_id(st.session_state.design_wp_settings or {})

            for kind, label, icon in [("breaking", "Breaking News Ticker", "📰"), ("crypto", "Crypto Price Ticker", "💹")]:
                st.markdown("<div class='panel-box' style='margin-bottom:14px'>", unsafe_allow_html=True)
                pattern = hits[kind]
                if not pattern:
                    st.markdown(f"""<div class='panel-box-head'><h4>{icon} {label}</h4>
                        <span class='hint'>Not found on this site</span></div>""", unsafe_allow_html=True)
                    st.warning(
                        f"No block pattern for a {label.lower()} was found (checked every pattern registered by "
                        f"your theme and plugins via the REST API). This app won't fake a toggle for something "
                        f"that doesn't exist — install a ticker plugin, or add a custom block pattern with "
                        f"'{kind}' or 'ticker' in its slug/title, then reload this tab."
                    )
                elif not page_id:
                    st.markdown(f"""<div class='panel-box-head'><h4>{icon} {label}</h4>
                        <span class='hint'>Pattern found: {pattern.get('title','')}</span></div>""", unsafe_allow_html=True)
                    st.info("Your homepage currently shows your latest posts (not a static page) — this app can only insert a ticker into a static homepage. Set one under **Settings → Reading** in WP Admin first, then reload this tab.")
                else:
                    st.markdown(f"""<div class='panel-box-head'><h4>{icon} {label}</h4>
                        <span class='hint'>Pattern found: {pattern.get('title','')}</span></div>""", unsafe_allow_html=True)
                    known = st.session_state.design_ticker_state.get(kind)
                    cc1, cc2 = st.columns([3, 1])
                    with cc1:
                        if known is None:
                            st.caption("Status unknown — check before toggling.")
                        else:
                            pill_cls = "done" if known else "draft"
                            pill_lbl = "● enabled" if known else "○ disabled"
                            st.markdown(f"<span class='pill {pill_cls}'>{pill_lbl}</span>", unsafe_allow_html=True)
                    with cc2:
                        if st.button("🔄 Check status", key=f"check_{kind}", use_container_width=True):
                            with st.spinner("Reading your live homepage..."):
                                state, cerr = check_ticker_enabled(kind, page_id, auth, domain)
                            if cerr:
                                st.error(f"Couldn't check status: {cerr}")
                            else:
                                st.session_state.design_ticker_state[kind] = state
                                st.rerun()

                    if known is not None:
                        action_label = f"🔴 Disable {label}" if known else f"🟢 Enable {label}"
                        if st.button(action_label, key=f"apply_{kind}"):
                            with st.spinner("Updating your homepage..."):
                                ok, msg = toggle_homepage_pattern(kind, not known, pattern, page_id, auth, domain, is_dry_run=dry_run)
                            if ok:
                                st.success(f"✅ {msg}")
                                if not dry_run:
                                    st.session_state.design_ticker_state[kind] = not known
                            else:
                                st.error(f"❌ {msg}")
                st.markdown("</div>", unsafe_allow_html=True)
