"""
WP AI Pro Ultra — Local Desktop Edition
Runs directly on your PC at http://localhost:8501
No ngrok. No Colab. Just double-click START.bat
"""

import streamlit as st
import requests, base64, json, time, urllib.parse, csv, os, threading
from io import StringIO
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

try:
    import google.generativeai as genai
    GEMINI_OK = True
except ImportError:
    GEMINI_OK = False

try:
    import anthropic as anthropic_sdk
    CLAUDE_OK = True
except ImportError:
    CLAUDE_OK = False

try:
    import openai as openai_sdk
    OPENAI_OK = True
except ImportError:
    OPENAI_OK = False

# ════════════════════════════════════════════════════════════
#  PAGE CONFIG
# ════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="WP AI Pro Ultra",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html,body,[class*="css"]{font-family:'Inter',sans-serif !important}
#MainMenu,footer,header{visibility:hidden}
.block-container{padding:0 !important;max-width:100% !important}
.stApp{background:#0f0c1e !important}
section[data-testid="stMain"]{background:#0f0c1e !important}

[data-testid="stSidebar"]{
    background:linear-gradient(180deg,#130d2e 0%,#0d0a20 100%) !important;
    border-right:1px solid rgba(127,119,221,0.15) !important;
    min-width:260px !important;
}
[data-testid="stSidebar"]>div{padding:0 !important}
[data-testid="stSidebar"] *{color:#a89ddc !important}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p{
    font-size:9.5px !important;font-weight:600 !important;letter-spacing:.12em !important;
    text-transform:uppercase !important;color:rgba(127,119,221,0.45) !important;
    margin:18px 0 6px !important;padding:0 4px;
}
[data-testid="stSidebar"] input{
    background:rgba(255,255,255,0.04) !important;border:1px solid rgba(127,119,221,0.2) !important;
    border-radius:10px !important;color:#e8e3ff !important;font-size:12.5px !important;
}
[data-testid="stSidebar"] input:focus{border-color:rgba(127,119,221,0.7) !important}
[data-testid="stSidebar"] [data-baseweb="select"]>div{
    background:rgba(255,255,255,0.04) !important;border:1px solid rgba(127,119,221,0.2) !important;
    border-radius:10px !important;color:#e8e3ff !important;font-size:12.5px !important;
}
[data-testid="stSidebar"] .stButton>button{
    width:100% !important;background:rgba(127,119,221,0.1) !important;
    border:1px solid rgba(127,119,221,0.25) !important;border-radius:10px !important;
    color:#c4b8f0 !important;font-size:12.5px !important;font-weight:500 !important;
    padding:7px 14px !important;transition:all .2s !important;margin-bottom:4px !important;
}
[data-testid="stSidebar"] .stButton>button:hover{
    background:rgba(127,119,221,0.22) !important;color:#fff !important;transform:translateX(2px) !important;
}
[data-testid="stSidebar"] hr{border-color:rgba(127,119,221,0.12) !important;margin:8px 0 !important}
[data-testid="stSidebar"] [data-testid="stToggle"] label{color:#c4b8f0 !important;font-size:12.5px !important}
[data-testid="stSidebar"] [data-testid="stToggle"] span[aria-checked="true"]{
    background:linear-gradient(135deg,#7F77DD,#534AB7) !important;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label{color:#c4b8f0 !important;font-size:12.5px !important}

.conn-pill{display:flex !important;align-items:center !important;gap:7px !important;
    padding:6px 10px !important;background:rgba(255,255,255,0.03) !important;
    border:1px solid rgba(127,119,221,0.12) !important;border-radius:8px !important;
    font-size:11.5px !important;color:#a89ddc !important;margin:3px 0 !important}
.conn-dot{width:7px !important;height:7px !important;border-radius:50% !important;
    background:#1D9E75 !important;flex-shrink:0 !important;
    box-shadow:0 0 6px rgba(29,158,117,0.5) !important}
.conn-dot.off{background:#444 !important;box-shadow:none !important}
.conn-dot.warn{background:#d4a012 !important;box-shadow:0 0 6px rgba(212,160,18,0.4) !important}

.stButton>button{font-family:'Inter',sans-serif !important;border-radius:12px !important;
    font-size:12.5px !important;font-weight:500 !important;transition:all .18s ease !important}
.stButton>button[kind="primary"]{
    background:linear-gradient(135deg,#7F77DD 0%,#534AB7 100%) !important;
    border:1px solid transparent !important;color:#fff !important;
    box-shadow:0 4px 14px rgba(127,119,221,0.35) !important;
}
.stButton>button[kind="primary"]:hover{
    background:linear-gradient(135deg,#9189e8 0%,#6358c9 100%) !important;
    box-shadow:0 6px 20px rgba(127,119,221,0.5) !important;transform:translateY(-1px) !important;
}
.stButton>button:not([kind="primary"]){
    background:rgba(255,255,255,0.04) !important;
    border:1px solid rgba(127,119,221,0.2) !important;color:#a89ddc !important;
}
.stButton>button:not([kind="primary"]):hover{
    background:rgba(127,119,221,0.12) !important;color:#d4cff5 !important;
}

.stTextArea textarea,.stTextInput input,textarea,input[type="text"],input[type="password"],input[type="number"]{
    background:rgba(20,15,45,0.85) !important;border:1px solid rgba(127,119,221,0.25) !important;
    border-radius:12px !important;color:#e8e3ff !important;caret-color:#a89ddc !important;
    font-size:13px !important;font-family:'Inter',sans-serif !important;
}
.stTextArea textarea:focus,.stTextInput input:focus{
    border-color:rgba(127,119,221,0.7) !important;
    box-shadow:0 0 0 3px rgba(127,119,221,0.15) !important;
}
.stTextArea textarea::placeholder,.stTextInput input::placeholder{color:rgba(168,157,220,0.35) !important}

[data-baseweb="select"]>div{
    background:rgba(255,255,255,0.04) !important;border:1px solid rgba(127,119,221,0.2) !important;
    border-radius:12px !important;color:#e8e3ff !important;font-size:13px !important;
}
[data-testid="stToggle"] label{color:#c4b8f0 !important;font-size:13px !important}
[data-testid="stToggle"] span[aria-checked="true"]{
    background:linear-gradient(135deg,#7F77DD,#534AB7) !important;
}
[data-testid="stRadio"] label{color:#c4b8f0 !important;font-size:13px !important}
.stProgress>div>div{
    background:linear-gradient(90deg,#7F77DD,#a89ddc) !important;
    border-radius:99px !important;box-shadow:0 0 10px rgba(127,119,221,0.4) !important;
}
.stProgress>div{background:rgba(127,119,221,0.1) !important;border-radius:99px !important;height:6px !important}
[data-testid="stDownloadButton"] button{
    background:rgba(29,158,117,0.12) !important;border:1px solid rgba(29,158,117,0.3) !important;
    border-radius:10px !important;color:#1D9E75 !important;font-weight:500 !important;
}
[data-testid="stMetric"]{
    background:rgba(255,255,255,0.03) !important;border:1px solid rgba(127,119,221,0.15) !important;
    border-radius:12px !important;padding:14px 16px !important;
}
[data-testid="stMetricLabel"]{color:#a89ddc !important;font-size:12px !important}
[data-testid="stMetricValue"]{color:#e8e3ff !important;font-size:24px !important;font-weight:600 !important}
hr{border-color:rgba(127,119,221,0.1) !important}
[data-testid="stExpander"]{
    background:rgba(255,255,255,0.03) !important;border:1px solid rgba(127,119,221,0.15) !important;
    border-radius:12px !important;
}
[data-testid="stExpander"] summary{color:#c4b8f0 !important;font-size:13px !important}

.stats-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;padding:20px 24px 0}
.stat-card{background:rgba(255,255,255,0.03);border:1px solid rgba(127,119,221,0.15);
    border-radius:16px;padding:20px;position:relative;overflow:hidden;transition:transform .2s,box-shadow .2s}
.stat-card:hover{transform:translateY(-2px);box-shadow:0 8px 28px rgba(0,0,0,0.3)}
.stat-card::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:var(--c)}
.stat-card.purple{--c:linear-gradient(90deg,#7F77DD,#534AB7)}
.stat-card.teal  {--c:linear-gradient(90deg,#1D9E75,#0F6E56)}
.stat-card.coral {--c:linear-gradient(90deg,#D85A30,#993C1D)}
.stat-card.blue  {--c:linear-gradient(90deg,#378ADD,#1a5da8)}
.stat-card.amber {--c:linear-gradient(90deg,#d4a012,#a07808)}
.stat-icon{width:40px;height:40px;border-radius:11px;display:flex;align-items:center;
    justify-content:center;font-size:19px;margin-bottom:14px}
.stat-icon.purple{background:rgba(127,119,221,0.15)}
.stat-icon.teal  {background:rgba(29,158,117,0.15)}
.stat-icon.coral {background:rgba(216,90,48,0.15)}
.stat-icon.blue  {background:rgba(55,138,221,0.15)}
.stat-icon.amber {background:rgba(212,160,18,0.15)}
.stat-label{font-size:11px;font-weight:500;color:rgba(168,157,220,0.6);text-transform:uppercase;
    letter-spacing:.08em;margin-bottom:6px}
.stat-val{font-size:30px;font-weight:700;color:#e8e3ff;line-height:1}
.stat-delta{font-size:11px;margin-top:6px}
.stat-delta.good{color:#1D9E75}
.stat-delta.warn{color:#D85A30}
.stat-delta.info{color:#d4a012}

.section-head{display:flex;align-items:center;gap:10px;padding:22px 24px 12px}
.section-head h3{font-size:15px;font-weight:600;color:#e8e3ff;flex:1;margin:0}
.section-head .hint{font-size:12px;color:rgba(168,157,220,0.5)}

.post-table{margin:0 24px 20px}
.post-row-ui{display:flex;align-items:center;gap:12px;padding:12px 16px;
    background:rgba(255,255,255,0.03);border:1px solid rgba(127,119,221,0.12);
    border-radius:12px;margin-bottom:6px;transition:all .15s}
.post-row-ui:hover{background:rgba(127,119,221,0.07);border-color:rgba(127,119,221,0.3);transform:translateX(2px)}
.post-thumb{width:40px;height:40px;border-radius:10px;background:rgba(127,119,221,0.1);
    display:flex;align-items:center;justify-content:center;font-size:17px;flex-shrink:0;
    border:1px solid rgba(127,119,221,0.15)}
.post-thumb.has{background:rgba(29,158,117,0.12);border-color:rgba(29,158,117,0.2)}
.post-info{flex:1;min-width:0}
.post-title-ui{font-size:13.5px;font-weight:500;color:#e8e3ff;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.post-meta-ui{font-size:11.5px;color:rgba(168,157,220,0.55);margin-top:3px}

.pill{display:inline-flex;align-items:center;gap:4px;padding:3px 10px;border-radius:999px;
    font-size:10.5px;font-weight:600;flex-shrink:0;letter-spacing:.02em}
.pill.pub  {background:rgba(29,158,117,0.15);color:#1D9E75;border:1px solid rgba(29,158,117,0.3)}
.pill.draft{background:rgba(127,119,221,0.15);color:#a89ddc;border:1px solid rgba(127,119,221,0.3)}
.pill.noimg{background:rgba(216,90,48,0.15);color:#D85A30;border:1px solid rgba(216,90,48,0.3)}
.pill.done {background:rgba(29,158,117,0.15);color:#1D9E75;border:1px solid rgba(29,158,117,0.3)}
.pill.running{background:rgba(127,119,221,0.2);color:#c4b8f0;border:1px solid rgba(127,119,221,0.4)}
.pill.err  {background:rgba(216,90,48,0.15);color:#D85A30;border:1px solid rgba(216,90,48,0.3)}
.pill.skip {background:rgba(234,179,8,0.15);color:#d4a012;border:1px solid rgba(234,179,8,0.3)}
.pill.sched{background:rgba(55,138,221,0.15);color:#378ADD;border:1px solid rgba(55,138,221,0.3)}

.panel-box{background:rgba(255,255,255,0.03);border:1px solid rgba(127,119,221,0.15);
    border-radius:16px;margin:0 24px 16px;overflow:hidden}
.panel-box-head{display:flex;align-items:center;gap:10px;padding:14px 18px;
    border-bottom:1px solid rgba(127,119,221,0.1);background:rgba(127,119,221,0.04)}
.panel-box-head h4{font-size:13.5px;font-weight:600;color:#e8e3ff;flex:1;margin:0}
.panel-box-head .hint{font-size:11px;color:rgba(168,157,220,0.5)}

.run-badge{display:inline-flex;align-items:center;gap:5px;padding:4px 12px;border-radius:999px;font-size:12px;font-weight:600}
.run-badge.ok  {background:rgba(29,158,117,0.15);color:#1D9E75;border:1px solid rgba(29,158,117,0.3)}
.run-badge.err {background:rgba(216,90,48,0.15);color:#D85A30;border:1px solid rgba(216,90,48,0.3)}
.run-badge.skip{background:rgba(127,119,221,0.15);color:#a89ddc;border:1px solid rgba(127,119,221,0.3)}
.run-badge.sched{background:rgba(55,138,221,0.15);color:#378ADD;border:1px solid rgba(55,138,221,0.3)}

.sched-card{background:rgba(55,138,221,0.06);border:1px solid rgba(55,138,221,0.2);
    border-radius:14px;margin:0 24px 16px;overflow:hidden}
.sched-card-head{display:flex;align-items:center;justify-content:space-between;
    padding:12px 18px;background:rgba(55,138,221,0.08);border-bottom:1px solid rgba(55,138,221,0.15)}
.sched-card-title{font-size:13px;font-weight:600;color:#378ADD}
.sched-card-badge{background:rgba(55,138,221,0.15);color:#378ADD;border:1px solid rgba(55,138,221,0.3);
    border-radius:999px;padding:2px 10px;font-size:11px;font-weight:600}
.sched-row{display:flex;align-items:center;gap:10px;padding:8px 18px;
    border-bottom:1px solid rgba(55,138,221,0.07);font-size:12.5px}
.sched-row:last-child{border-bottom:none}
.sched-idx{width:28px;height:28px;border-radius:8px;background:rgba(55,138,221,0.12);
    display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;color:#378ADD;flex-shrink:0}
.sched-time{color:#378ADD;font-weight:600;min-width:120px}
.sched-label{color:#c4b8f0;flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.sched-status{font-size:11px;font-weight:600;flex-shrink:0}
.sched-status.future{color:#378ADD}
.sched-status.now{color:#1D9E75}

.dash-progress-wrap{margin:16px 24px 0;background:rgba(255,255,255,0.025);
    border:1px solid rgba(127,119,221,0.15);border-radius:14px;padding:18px 22px}
.dash-progress-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:10px}
.dash-progress-label{font-size:13px;font-weight:500;color:#c4b8f0}
.dash-progress-pct{font-size:20px;font-weight:700;color:#7F77DD}
.dash-pbar-track{height:8px;background:rgba(127,119,221,0.1);border-radius:4px;overflow:hidden;margin-bottom:10px}
.dash-pbar-fill{height:100%;background:linear-gradient(90deg,#1D9E75,#7F77DD);border-radius:4px;
    box-shadow:0 0 12px rgba(29,158,117,0.3)}
.dash-progress-sub{display:flex;gap:12px;font-size:12px;font-weight:500}

.status-card,.alert-card,.summary-card,.getting-started{
    background:rgba(255,255,255,0.025);border:1px solid rgba(127,119,221,0.15);
    border-radius:14px;padding:16px 18px;margin-bottom:12px}
.status-card-head{font-size:12px;font-weight:600;color:rgba(168,157,220,0.6);
    text-transform:uppercase;letter-spacing:.08em;margin-bottom:12px}
.status-row{display:flex;align-items:center;gap:9px;padding:6px 0;border-bottom:1px solid rgba(127,119,221,0.07)}
.status-row:last-child{border-bottom:none}
.status-dot{width:8px;height:8px;border-radius:50%;flex-shrink:0}
.status-dot.on  {background:#1D9E75;box-shadow:0 0 6px rgba(29,158,117,0.5)}
.status-dot.off {background:rgba(168,157,220,0.2)}
.status-dot.warn{background:#d4a012;box-shadow:0 0 6px rgba(212,160,18,0.4)}
.status-label{font-size:12.5px;color:#c4b8f0}
.alert-card{border-color:rgba(216,90,48,0.25)}
.alert-card .status-card-head{color:#D85A30}
.alert-item{display:flex;align-items:center;gap:8px;padding:5px 0;font-size:12.5px;color:#c4b8f0;
    border-bottom:1px solid rgba(216,90,48,0.07)}
.alert-item:last-child{border-bottom:none}
.alert-dot{width:6px;height:6px;border-radius:50%;flex-shrink:0}
.alert-dot.red{background:#D85A30;box-shadow:0 0 5px rgba(216,90,48,0.4)}
.summary-row{display:flex;align-items:center;justify-content:space-between;padding:7px 0;
    font-size:13px;color:rgba(168,157,220,0.7);border-bottom:1px solid rgba(127,119,221,0.07)}
.summary-row:last-child{border-bottom:none}
.summary-row b{color:#e8e3ff;font-weight:600}
.gs-step{display:flex;align-items:flex-start;gap:10px;padding:7px 0;font-size:12.5px;color:#c4b8f0;
    border-bottom:1px solid rgba(127,119,221,0.07);line-height:1.5}
.gs-step:last-child{border-bottom:none}
.gs-num{width:20px;height:20px;border-radius:6px;background:rgba(127,119,221,0.2);
    border:1px solid rgba(127,119,221,0.3);display:flex;align-items:center;justify-content:center;
    font-size:11px;font-weight:700;color:#7F77DD;flex-shrink:0;margin-top:1px}
.empty-feed{text-align:center;padding:50px 20px}
.empty-icon{font-size:40px;margin-bottom:14px;opacity:.5}
.empty-title{font-size:15px;font-weight:600;color:#c4b8f0;margin-bottom:6px}
.empty-sub{font-size:12.5px;color:rgba(168,157,220,0.45);line-height:1.6}
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
#  CONSTANTS & HELPERS
# ════════════════════════════════════════════════════════════
PROGRESS_FILE  = "wp_pro_progress.json"
FALLBACK_ORDER = ["claude", "openai", "mistral", "gemini"]

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

def friendly_error(e):
    s = str(e)
    if "429" in s or "Too Many Requests" in s: return "Rate limited — retry later"
    if "401" in s or "Unauthorized" in s: return "API key invalid"
    if "403" in s or "Forbidden" in s: return "API key lacks permission"
    if "timeout" in s.lower(): return "Request timed out"
    if "503" in s or "502" in s: return "Provider unavailable"
    return s.split("\n")[0][:80]

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

def fetch_all_posts(auth, domain, statuses, max_count):
    all_posts, page = [], 1
    headers = {"Authorization": f"Basic {auth}"}
    while True:
        url = f"https://{domain}/wp-json/wp/v2/posts"
        params = {"status": ",".join(statuses), "per_page": 100, "page": page,
                  "_fields": "id,title,content,excerpt,status,slug,link,date,featured_media"}
        try:
            r = requests.get(url, headers=headers, params=params, timeout=30)
            if r.status_code == 400: break
            r.raise_for_status()
            batch = r.json()
            if not batch: break
            all_posts.extend(batch)
            if page >= int(r.headers.get("X-WP-TotalPages", 1)) or (max_count and len(all_posts) >= max_count): break
            page += 1; time.sleep(0.2)
        except Exception: break
    return all_posts[:max_count] if max_count else all_posts

def fetch_wp_categories(auth, domain):
    cats = {}
    try:
        r = requests.get(f"https://{domain}/wp-json/wp/v2/categories",
                         headers={"Authorization": f"Basic {auth}"},
                         params={"per_page": 100, "_fields": "id,name"}, timeout=20)
        r.raise_for_status()
        for c in r.json(): cats[c["name"]] = c["id"]
    except Exception: pass
    return cats

def run_ai_provider(prompt, prov, key, model, temperature=0.3, system=None):
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
        msgs = []
        if system: msgs.append({"role": "system", "content": system})
        msgs.append({"role": "user", "content": prompt})
        r = requests.post("https://api.mistral.ai/v1/chat/completions",
                          headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
                          json={"model": model, "messages": msgs, "temperature": temperature}, timeout=90)
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
            wait = 20*(attempt+1) if "429" in err_str or "rate limit" in err_str else (5*(attempt+1) if "503" in err_str or "timeout" in err_str else 2**attempt)
            if attempt < 4: time.sleep(wait)
            else: break
    if enable_fallback and fallback_keys:
        for fb_name in FALLBACK_ORDER:
            fb_key = (fallback_keys or {}).get(fb_name, "").strip()
            if not fb_key or fb_name.lower() == prov.lower(): continue
            fb_model = {"claude":"claude-sonnet-4-20250514","openai":"gpt-4o",
                        "mistral":"mistral-small-latest","gemini":"gemini-1.5-flash"}[fb_name]
            try: return run_ai_provider(prompt, fb_name.capitalize(), fb_key, fb_model, temperature, system)
            except Exception: continue
    raise last_err

def generate_seo_meta(title, content_text, prov, key, model, fb=False, fbk=None):
    raw = run_ai(
        f"Post title: {title}\nContent: {content_text[:500]}\n"
        "Return JSON with: meta_description (≤155 chars), focus_keyword (2-4 words), excerpt (1-2 sentences).",
        prov, key, model, 0.1,
        "You are an expert SEO copywriter. Return JSON only — no markdown.", fb, fbk
    )
    return json.loads(raw.replace("```json","").replace("```","").strip())

def generate_schema_jsonld(title, url, date_pub, desc):
    return json.dumps({"@context":"https://schema.org","@type":"Article",
                       "headline":title,"url":url,"datePublished":date_pub,"description":desc,
                       "publisher":{"@type":"Organization","name":"WordPress Site"}}, ensure_ascii=False)

def quality_gate(html_content, min_words):
    words = len(BeautifulSoup(html_content, "html.parser").get_text().split())
    return words, words >= min_words

def gen_image_dalle(prompt_text, openai_key, style):
    client   = openai_sdk.OpenAI(api_key=openai_key)
    resp     = client.images.generate(model="dall-e-3", prompt=prompt_text[:3000],
                                      size="1792x1024", style=style, n=1)
    img_resp = requests.get(resp.data[0].url, timeout=90)
    if "image" not in img_resp.headers.get("Content-Type",""): raise ValueError("Non-image returned")
    return img_resp.content

def gen_image_pollinations(prompt_text):
    safe = " ".join(prompt_text.split())[:800]
    url  = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(safe,safe='')}?width=1200&height=630&nologo=true&seed=42"
    r    = requests.get(url, timeout=90, headers={"User-Agent":"Mozilla/5.0"})
    r.raise_for_status()
    if "image" not in r.headers.get("Content-Type",""): raise ValueError("Non-image returned")
    return r.content

def upload_wp_image(img_bytes, title, alt_text, auth, domain, do_seo):
    media_url = f"https://{domain}/wp-json/wp/v2/media"
    safe_fn   = "".join(x for x in title if x.isalnum() or x in " -").replace(" ","-").lower()[:60]+"-featured.jpg"
    up_hdr    = {"Authorization":f"Basic {auth}","Content-Disposition":f'attachment; filename="{safe_fn}"',
                 "Content-Type":"image/jpeg"}
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
        try: requests.post(f"{media_url}/{media_id}", headers=ph,
                json={"alt_text":alt_text,"title":title,"caption":alt_text}, timeout=30)
        except Exception: pass
    return media_id

def wp_update_post(post_id, payload, auth, domain):
    url = f"https://{domain}/wp-json/wp/v2/posts/{post_id}"
    hdr = {"Authorization":f"Basic {auth}","Content-Type":"application/json"}
    for attempt in range(3):
        try:
            r = requests.post(url, headers=hdr, json=payload, timeout=45)
            r.raise_for_status(); return r
        except Exception:
            if attempt == 2: return None
            time.sleep(2**attempt)

def wp_create_post(payload, auth, domain):
    url = f"https://{domain}/wp-json/wp/v2/posts"
    hdr = {"Authorization":f"Basic {auth}","Content-Type":"application/json"}
    for attempt in range(3):
        try:
            r = requests.post(url, headers=hdr, json=payload, timeout=45)
            r.raise_for_status(); return r
        except Exception:
            if attempt == 2: return None
            time.sleep(2**attempt)

def update_yoast_meta(post_id, meta_desc, focus_kw, auth, domain):
    try:
        requests.post(f"https://{domain}/wp-json/wp/v2/posts/{post_id}",
                      headers={"Authorization":f"Basic {auth}","Content-Type":"application/json"},
                      json={"meta":{"_yoast_wpseo_metadesc":meta_desc,"_yoast_wpseo_focuskw":focus_kw,
                                    "rank_math_description":meta_desc,"rank_math_focus_keyword":focus_kw}},
                      timeout=30)
    except Exception: pass

def ai_pick_category(title, content_text, categories_dict, prov, key, model, fb=False, fbk=None):
    if not categories_dict: return None
    cat_list = "\n".join(f"- {name} (id:{cid})" for name, cid in categories_dict.items())
    try:
        raw  = run_ai(
            f"Post title: {title}\nExcerpt: {content_text[:300]}\n\nCategories:\n{cat_list}\n\n"
            "Pick best category. Return JSON: {\"category_id\": <int_or_null>, \"category_name\": \"<name>\"}",
            prov, key, model, 0.1,
            "You are a WordPress content classifier. Return JSON only.", fb, fbk
        )
        data = json.loads(raw.replace("```json","").replace("```","").strip())
        return data.get("category_id")
    except Exception: return None

# ════════════════════════════════════════════════════════════
#  SESSION STATE
# ════════════════════════════════════════════════════════════
for k, v in [("posts",[]),("selected",[]),("active_tab","dashboard"),
             ("run_log",[]),("created_log",[])]:
    if k not in st.session_state: st.session_state[k] = v

# ════════════════════════════════════════════════════════════
#  SIDEBAR
# ════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""
    <div style='padding:20px 16px 12px;border-bottom:1px solid rgba(127,119,221,0.1);margin-bottom:6px'>
      <div style='font-size:22px;margin-bottom:4px'>⚡</div>
      <div style='font-size:15px;font-weight:600;color:#fff'>WP AI Pro Ultra</div>
      <div style='font-size:11px;color:rgba(255,255,255,0.4)'>Local Desktop Edition</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("SITE")
    domain  = st.text_input("Domain", value="", label_visibility="collapsed", placeholder="yourdomain.com")
    wp_user = st.text_input("Username", label_visibility="collapsed", placeholder="WP username")
    wp_pw   = st.text_input("App Password", type="password", label_visibility="collapsed", placeholder="xxxx xxxx xxxx xxxx xxxx xxxx")

    st.markdown("AI ENGINE")
    provider = st.selectbox("Provider", ["Claude","OpenAI","Mistral","Gemini"], label_visibility="collapsed")
    ai_key   = st.text_input("API Key", type="password", label_visibility="collapsed", placeholder=f"{provider} API Key")
    ai_model_opts = {
        "Claude":  ["claude-sonnet-4-20250514","claude-opus-4-20250514","claude-haiku-4-5-20251001"],
        "OpenAI":  ["gpt-4o","gpt-4o-mini","gpt-4-turbo"],
        "Mistral": ["mistral-large-latest","mistral-small-latest"],
        "Gemini":  ["gemini-1.5-pro","gemini-1.5-flash","gemini-2.5-flash"],
    }
    ai_model        = st.selectbox("Model", ai_model_opts[provider], label_visibility="collapsed")
    enable_fallback = st.toggle("Auto-fallback chain", value=True)
    fallback_keys   = {}
    if enable_fallback:
        with st.expander("Fallback keys"):
            for fb in ["claude","openai","mistral","gemini"]:
                fallback_keys[fb] = st.text_input(f"{fb.capitalize()}", type="password",
                                   key=f"fb_{fb}", label_visibility="collapsed",
                                   placeholder=f"{fb.capitalize()} fallback key")

    st.markdown("IMAGES")
    generate_images  = st.toggle("Generate featured images", value=True)
    image_provider   = st.selectbox("Image source", ["Pollinations (free)","DALL-E 3"], label_visibility="collapsed")
    dalle_key, dalle_style = "", "vivid"
    if image_provider == "DALL-E 3":
        dalle_key   = st.text_input("OpenAI key for DALL-E", type="password", label_visibility="collapsed", placeholder="sk-...")
        dalle_style = st.selectbox("Style", ["vivid","natural"], label_visibility="collapsed")
    optimize_seo_img = st.toggle("SEO metadata on images", value=True)

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
    enable_schedule  = st.toggle("Smart 24h scheduling", value=True)
    posts_per_day    = st.number_input("Posts per day", min_value=1, max_value=500, value=50, step=10, label_visibility="collapsed")
    schedule_start_h = st.slider("Start hour (UTC)", 0, 23, 6, label_visibility="collapsed")
    start_from_now   = st.toggle("Start from now", value=False)
    delay_between_api = st.slider("Delay between calls (sec)", 1, 60, 5, label_visibility="collapsed")

    _interval_min = round(1440 / max(posts_per_day, 1), 1)
    if enable_schedule:
        st.caption(f"1 post every {_interval_min} min · start {schedule_start_h:02d}:00 UTC")

    st.markdown("RUN")
    post_status   = st.multiselect("Post status", ["publish","draft","private"], default=["publish"], label_visibility="collapsed")
    max_posts_in  = st.number_input("Max posts (0=all)", min_value=0, value=0, step=10, label_visibility="collapsed")
    workers       = st.slider("Parallel workers", 1, 8, 2, label_visibility="collapsed")
    update_status = st.selectbox("After fix", ["keep original","publish","draft"], label_visibility="collapsed")
    dry_run       = st.toggle("Sandbox mode (no writes)", value=True)
    resume_mode   = st.toggle("Resume from last run", value=True)

    st.markdown("---")
    posts_loaded = len(st.session_state.posts)
    no_img_count = sum(1 for p in st.session_state.posts if not p.get("featured_media"))
    st.markdown(f"""
    <div class='conn-pill'><div class='conn-dot {"" if (domain and wp_user and wp_pw) else "off"}'></div>
      {domain or "not connected"}</div>
    <div class='conn-pill'><div class='conn-dot {"" if ai_key else "off"}'></div>
      {provider} · {ai_model.split("-")[0]}</div>
    <div class='conn-pill'><div class='conn-dot {"" if posts_loaded else "off"}'></div>
      {posts_loaded} posts · {no_img_count} missing img</div>
    <div class='conn-pill'><div class='conn-dot {"warn" if enable_schedule else "off"}'></div>
      {"Scheduling ON · " + str(_interval_min) + " min" if enable_schedule else "Scheduling OFF"}</div>
    <div class='conn-pill'><div class='conn-dot {"warn" if dry_run else ""}'></div>
      {"Sandbox mode" if dry_run else "LIVE mode"}</div>
    """, unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
#  TAB NAVIGATION
# ════════════════════════════════════════════════════════════
TABS = [
    ("dashboard","📊 Dashboard"),
    ("scan",     "📡 Scan & Select"),
    ("optimize", "🔧 Optimize"),
    ("images",   "🖼️ Fix Images"),
    ("create",   "✨ Create Posts"),
    ("seo",      "🔍 SEO Tools"),
]
tab_cols = st.columns(len(TABS))
for col, (tid, tlabel) in zip(tab_cols, TABS):
    with col:
        if st.button(tlabel, key=f"tab_{tid}",
                     type="primary" if st.session_state.active_tab == tid else "secondary",
                     use_container_width=True):
            st.session_state.active_tab = tid; st.rerun()

active = st.session_state.active_tab
st.markdown("---")

def render_stats():
    posts    = st.session_state.posts
    total    = len(posts)
    no_img   = sum(1 for p in posts if not p.get("featured_media"))
    ok_count = sum(1 for r in st.session_state.run_log if r.get("status") == "ok")
    sched_c  = sum(1 for c in st.session_state.created_log if c.get("scheduled"))
    pct_img  = round((total - no_img) / total * 100) if total else 0
    st.markdown(f"""
    <div class='stats-grid'>
      <div class='stat-card purple'><div class='stat-icon purple'>📄</div>
        <div class='stat-label'>Total posts</div><div class='stat-val'>{total}</div>
        <div class='stat-delta good'>loaded</div></div>
      <div class='stat-card coral'><div class='stat-icon coral'>🚫</div>
        <div class='stat-label'>Missing images</div><div class='stat-val'>{no_img}</div>
        <div class='stat-delta {"warn" if no_img else "good"}'>{"needs attention" if no_img else "all covered ✓"}</div></div>
      <div class='stat-card teal'><div class='stat-icon teal'>✅</div>
        <div class='stat-label'>Image coverage</div><div class='stat-val'>{pct_img}%</div>
        <div class='stat-delta good'>{total - no_img} of {total}</div></div>
      <div class='stat-card blue'><div class='stat-icon blue'>🤖</div>
        <div class='stat-label'>AI optimized</div><div class='stat-val'>{ok_count}</div>
        <div class='stat-delta good'>this session</div></div>
    </div>
    """, unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
#  DASHBOARD
# ════════════════════════════════════════════════════════════
if active == "dashboard":
    posts    = st.session_state.posts
    run_log  = st.session_state.run_log
    total    = len(posts)
    no_img   = sum(1 for p in posts if not p.get("featured_media"))
    ok_count = sum(1 for r in run_log if r.get("status") == "ok")
    err_count= sum(1 for r in run_log if r.get("status") == "error")
    created  = len(st.session_state.created_log)
    sched_c  = sum(1 for c in st.session_state.created_log if c.get("scheduled"))
    pct_img  = round((total - no_img) / total * 100) if total else 0

    st.markdown(f"""
    <div class="stats-grid">
      <div class="stat-card purple"><div class="stat-icon purple">📄</div>
        <div class="stat-label">Total posts</div><div class="stat-val">{total}</div>
        <div class="stat-delta good">{"scan to refresh" if total else "scan your site to start"}</div></div>
      <div class="stat-card coral"><div class="stat-icon coral">🚫</div>
        <div class="stat-label">Missing images</div><div class="stat-val">{no_img}</div>
        <div class="stat-delta {"warn" if no_img else "good"}">{"⚠ needs attention" if no_img else "✓ all covered"}</div></div>
      <div class="stat-card teal"><div class="stat-icon teal">✅</div>
        <div class="stat-label">Image coverage</div><div class="stat-val">{pct_img}%</div>
        <div class="stat-delta good">{total-no_img} of {total} posts</div></div>
      <div class="stat-card amber"><div class="stat-icon amber">⏰</div>
        <div class="stat-label">Scheduled</div><div class="stat-val">{sched_c}</div>
        <div class="stat-delta info">{created-sched_c} published immediately</div></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="dash-progress-wrap">
      <div class="dash-progress-head">
        <span class="dash-progress-label">📊 Image coverage</span>
        <span class="dash-progress-pct">{pct_img}%</span>
      </div>
      <div class="dash-pbar-track"><div class="dash-pbar-fill" style="width:{pct_img}%"></div></div>
      <div class="dash-progress-sub">
        <span style="color:#1D9E75">✓ {total-no_img} with image</span>
        <span style="color:#D85A30">✗ {no_img} missing</span>
        <span style="color:rgba(168,157,220,0.5)">{total} total</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""<div class="section-head"><h3>⚡ Quick actions</h3></div>""", unsafe_allow_html=True)
    qa1, qa2, qa3, qa4 = st.columns(4)
    with qa1:
        if st.button("📡 Scan site", use_container_width=True):
            st.session_state.active_tab = "scan"; st.rerun()
    with qa2:
        if st.button("🖼️ Fix images", use_container_width=True, type="primary" if no_img else "secondary"):
            st.session_state.active_tab = "images"; st.rerun()
    with qa3:
        if st.button("✨ Create posts", use_container_width=True):
            st.session_state.active_tab = "create"; st.rerun()
    with qa4:
        if st.button("🔧 Optimize", use_container_width=True):
            st.session_state.active_tab = "optimize"; st.rerun()

    left_col, right_col = st.columns([3,2])
    with left_col:
        st.markdown("""<div class="section-head"><h3>📋 Activity feed</h3><span class="hint">Recent operations</span></div>""", unsafe_allow_html=True)
        if run_log or st.session_state.created_log:
            feed = []
            for r in run_log[-8:]:
                feed.append({"title":r["title"],"type":"optimize","status":r["status"],
                             "words":r.get("word_count",0),"has_img":bool(r.get("media_id")),
                             "kw":r.get("focus_keyword",""),"error":r.get("error",""),"scheduled":""})
            for c in st.session_state.created_log[-4:]:
                feed.append({"title":c["topic"],"type":"create","status":"ok","words":0,
                             "has_img":True,"kw":"","error":"","scheduled":c.get("scheduled","")})
            st.markdown("<div class='post-table'>", unsafe_allow_html=True)
            for item in reversed(feed[-12:]):
                s = item["status"]
                if item["type"] == "create":
                    icon = "⏰" if item["scheduled"] else "✨"
                    pill_cls = "sched" if item["scheduled"] else "done"
                    pill_lbl = "scheduled" if item["scheduled"] else "created"
                elif s == "ok": icon="🖼️" if item["has_img"] else "📄"; pill_cls="done"; pill_lbl="optimized"
                elif s == "error": icon="⚠️"; pill_cls="err"; pill_lbl=(item["error"][:22] or "failed")
                elif s == "gate_fail": icon="🛡️"; pill_cls="skip"; pill_lbl="gated"
                else: icon="👁️"; pill_cls="running"; pill_lbl="preview"
                meta_txt = f"{item['words']}w" if item['words'] else ""
                if item["scheduled"]: meta_txt += f" · 🕐 {item['scheduled']}"
                elif item["kw"] and s=="ok": meta_txt += f" · {item['kw']}"
                st.markdown(f"""
                <div class='post-row-ui'>
                  <div class='post-thumb {"has" if item["has_img"] and s in ("ok","") else ""}'>{icon}</div>
                  <div class='post-info'>
                    <div class='post-title-ui'>{item["title"]}</div>
                    <div class='post-meta-ui'>{meta_txt or "—"}</div>
                  </div>
                  <span class='pill {pill_cls}'>{pill_lbl}</span>
                </div>""", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            if run_log:
                buf = StringIO()
                w = csv.DictWriter(buf, fieldnames=run_log[0].keys())
                w.writeheader(); w.writerows(run_log)
                st.download_button("📥 Export CSV", data=buf.getvalue(),
                                   file_name=f"wp_pro_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                                   mime="text/csv", use_container_width=True)
        else:
            st.markdown("""<div class='empty-feed'><div class='empty-icon'>📭</div>
                <div class='empty-title'>No activity yet</div>
                <div class='empty-sub'>Run the optimizer or create posts.</div></div>""", unsafe_allow_html=True)

    with right_col:
        connected = bool(domain and wp_user and wp_pw)
        st.markdown(f"""
        <div class="status-card">
          <div class="status-card-head">🔌 Connection status</div>
          <div class="status-row"><div class="status-dot {"on" if connected else "off"}"></div>
            <span class="status-label">{domain if domain else "Not configured"}</span></div>
          <div class="status-row"><div class="status-dot {"on" if len(posts)>0 else "off"}"></div>
            <span class="status-label">{f"{total} posts loaded" if total else "Not scanned"}</span></div>
          <div class="status-row"><div class="status-dot {"on" if ai_key else "off"}"></div>
            <span class="status-label">{provider} · {ai_model.split("-")[0]}</span></div>
          <div class="status-row"><div class="status-dot {"warn" if dry_run else "on"}"></div>
            <span class="status-label">{"🟡 Sandbox mode" if dry_run else "🔴 Live mode"}</span></div>
        </div>
        """, unsafe_allow_html=True)
        if not total:
            st.markdown("""<div class="getting-started">
              <div class="status-card-head">🚀 Getting started</div>
              <div class="gs-step"><span class="gs-num">1</span><span>Enter your domain + WP credentials in the sidebar</span></div>
              <div class="gs-step"><span class="gs-num">2</span><span>Add at least one AI API key</span></div>
              <div class="gs-step"><span class="gs-num">3</span><span>Click <b>Scan & Select</b> to load your posts</span></div>
              <div class="gs-step"><span class="gs-num">4</span><span>Go to <b>Create Posts</b> and paste your topics</span></div>
              <div class="gs-step"><span class="gs-num">5</span><span>Turn off Sandbox when ready to go live ⚡</span></div>
            </div>""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
#  SCAN & SELECT
# ════════════════════════════════════════════════════════════
elif active == "scan":
    st.markdown("<div style='padding:20px 28px 0'>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([3,1,1])
    with c1:
        if st.button("📡 Scan WordPress site", type="primary", use_container_width=True):
            if not (domain and wp_user and wp_pw):
                st.error("Fill in domain, username and app password in the sidebar.")
            else:
                with st.spinner("Connecting..."):
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
        done_count = len(load_progress().get("processed", []))
        st.metric("Resumable", f"{done_count}")
    st.markdown("</div>", unsafe_allow_html=True)

    posts_to_show = st.session_state.posts
    if posts_to_show:
        no_img_posts  = [p for p in posts_to_show if not p.get("featured_media")]
        has_img_posts = [p for p in posts_to_show if p.get("featured_media")]
        st.markdown(f"""<div class='section-head'>
          <h3>Select posts</h3>
          <span class='hint'>🖼️ {len(has_img_posts)} with image · 🚫 {len(no_img_posts)} without</span>
        </div>""", unsafe_allow_html=True)
        ca, cb, cc, cd = st.columns([1,1,2,2])
        with ca:
            if st.button("✅ All", use_container_width=True):
                st.session_state.selected = [p["id"] for p in posts_to_show]; st.rerun()
        with cb:
            if st.button("❌ None", use_container_width=True):
                st.session_state.selected = []; st.rerun()
        with cc:
            if st.button("🚫 Without image only", use_container_width=True):
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
            checked = pid in st.session_state.selected
            st.markdown(f"""
            <div class='post-row-ui'>
              <div class='post-thumb {"has" if has_img else ""}'>{"🖼️" if has_img else "🚫"}</div>
              <div class='post-info'>
                <div class='post-title-ui'>{title}</div>
                <div class='post-meta-ui'>{slug}</div>
              </div>
              <span class='pill {"pub" if stat=="publish" else "draft"}'>{stat}</span>
              <span class='pill {"pub" if has_img else "noimg"}'>{"has image" if has_img else "no image"}</span>
            </div>""", unsafe_allow_html=True)
            new_val = st.checkbox("Select", value=checked, key=f"chk_{pid}", label_visibility="collapsed")
            if new_val and pid not in st.session_state.selected: st.session_state.selected.append(pid)
            elif not new_val and pid in st.session_state.selected: st.session_state.selected.remove(pid)
        st.markdown("</div>", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
#  OPTIMIZE
# ════════════════════════════════════════════════════════════
elif active == "optimize":
    render_stats()
    selected_count = len(st.session_state.selected)
    st.markdown(f"""<div class='section-head'>
      <h3>🔧 Optimize selected posts</h3>
      <span class='hint'>{selected_count} posts selected</span>
    </div>""", unsafe_allow_html=True)

    st.markdown("<div style='padding:0 28px'>", unsafe_allow_html=True)
    fix_instructions = st.text_area("Content fix instructions (blank = skip rewriting):",
        placeholder="Add a strong CTA at the end\nFix broken internal links\nImprove readability", height=100)
    st.markdown("</div>", unsafe_allow_html=True)

    if dry_run: st.warning("🟡 Sandbox — nothing will be written to WordPress.")
    else: st.error("🔴 Live mode — content will be pushed to WordPress.")

    st.markdown("<div style='padding:0 28px'>", unsafe_allow_html=True)
    run_btn = st.button(f"{'🔍 Preview' if dry_run else '⚡ Run'} optimizer on {selected_count} posts",
                        type="primary", use_container_width=True,
                        disabled=(selected_count == 0 or not ai_key))
    st.markdown("</div>", unsafe_allow_html=True)

    if run_btn:
        auth = make_auth(wp_user, wp_pw)
        prog_state = load_progress() if resume_mode else {"processed":[],"results":[]}
        already    = set(prog_state.get("processed",[]))
        to_process = [p for p in st.session_state.posts
                      if p["id"] in st.session_state.selected and p["id"] not in already]
        if not to_process:
            st.info("All selected posts already processed. Clear resume to rerun."); st.stop()

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
            res   = {"id":pid,"title":title,"status":"ok","word_count":0,
                     "media_id":None,"meta_description":"","focus_keyword":"",
                     "image_prompt":"","alt_text":"","gate_pass":True,"error":""}
            try:
                fixed_html = ohtml
                if fix_instructions.strip():
                    fixed_html = run_ai(
                        f"Title: {title}\nInstructions: {fix_instructions}\nHTML:\n{ohtml[:12000]}",
                        provider, ai_key, ai_model, system=(
                            "You are a WordPress HTML editor. Return ONLY fixed HTML — no markdown."),
                        enable_fallback=enable_fallback, fallback_keys=fallback_keys
                    ).replace("```html","").replace("```","").strip()

                wc, gate_pass = quality_gate(fixed_html, gate_min_words)
                res["word_count"] = wc; res["gate_pass"] = gate_pass
                if enable_gate and not gate_pass and gate_auto_skip:
                    res["status"] = "gate_fail"; return res

                meta_desc, focus_kw, new_exc = "", "", oexc
                if seo_meta_desc:
                    plain = BeautifulSoup(fixed_html,"html.parser").get_text()
                    seo   = generate_seo_meta(title, plain, provider, ai_key, ai_model, enable_fallback, fallback_keys)
                    meta_desc = seo.get("meta_description","")
                    focus_kw  = seo.get("focus_keyword","")
                    new_exc   = seo.get("excerpt", oexc)
                    res["meta_description"] = meta_desc; res["focus_keyword"] = focus_kw

                if seo_schema:
                    tag = '<script type="application/ld+json">' + generate_schema_jsonld(title, link, date, meta_desc) + '</script>'
                    fixed_html = tag + "\n" + fixed_html

                media_id, img_bytes, seo_alt = None, None, ""
                if generate_images:
                    raw       = run_ai(f"2-sentence photorealistic image prompt for '{title}'. Plain text.",
                                       provider, ai_key, ai_model, 0.1, enable_fallback=enable_fallback, fallback_keys=fallback_keys)
                    img_prompt = " ".join(raw.replace("*","").replace('"','').split())[:800]
                    seo_alt    = run_ai(f"SEO image alt text under 120 chars for '{title}'.",
                                       provider, ai_key, ai_model, 0.1, enable_fallback=enable_fallback, fallback_keys=fallback_keys).replace('"','')
                    res["image_prompt"] = img_prompt; res["alt_text"] = seo_alt
                    for attempt in range(3):
                        try:
                            img_bytes = gen_image_dalle(img_prompt, dalle_key or ai_key, dalle_style) if image_provider=="DALL-E 3" and (dalle_key or ai_key) else gen_image_pollinations(img_prompt)
                            break
                        except Exception as e:
                            if attempt == 2: res["error"] += f"Image: {e}. "
                            else: time.sleep(3)

                if dry_run: res["status"] = "preview"; return res

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
                        plain_txt  = BeautifulSoup(fixed_html,"html.parser").get_text()
                        auto_cat   = ai_pick_category(title, plain_txt, wp_cats, provider, ai_key, ai_model, enable_fallback, fallback_keys)
                        if auto_cat: payload["categories"] = [auto_cat]

                r = wp_update_post(pid, payload, auth, domain)
                if r and r.status_code == 200:
                    res["status"] = "ok"; res["media_id"] = media_id
                    if seo_meta_desc and meta_desc: update_yoast_meta(pid, meta_desc, focus_kw, auth, domain)
                else:
                    res["status"] = "error"
                    res["error"] += f"WP API {getattr(r,'status_code','no response')}."
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
                    <div class='post-meta-ui'>{res.get("word_count",0)} words{" · "+res.get("focus_keyword","") if res.get("focus_keyword") else ""}</div>
                  </div>
                  <span class='pill {pill_cls}'>{pill_lbl}</span>
                </div>""", unsafe_allow_html=True)

        ok_n   = sum(1 for r in prog_state["results"] if r["status"]=="ok")
        err_n  = sum(1 for r in prog_state["results"] if r["status"]=="error")
        gate_n = sum(1 for r in prog_state["results"] if r["status"]=="gate_fail")
        prev_n = sum(1 for r in prog_state["results"] if r["status"]=="preview")
        st.success(f"🎉 Done! ✅ {ok_n} optimized · 🟡 {prev_n} previewed · ⛔ {gate_n} gated · ❌ {err_n} errors")

# ════════════════════════════════════════════════════════════
#  FIX IMAGES
# ════════════════════════════════════════════════════════════
elif active == "images":
    posts  = st.session_state.posts
    no_img = [p for p in posts if not p.get("featured_media")]
    render_stats()
    st.markdown(f"""<div class="section-head">
      <h3>🖼️ Posts without featured image</h3>
      <span class="hint">{len(no_img)} posts need an image</span>
    </div>""", unsafe_allow_html=True)

    c1, c2 = st.columns([3,1])
    with c1:
        fix_all_btn = st.button(f"⚡ Generate images for all {len(no_img)} posts",
                                type="primary", use_container_width=True,
                                disabled=(not no_img or not ai_key))
    with c2:
        if st.button("☑️ Select all → Optimize", use_container_width=True):
            st.session_state.selected = [p["id"] for p in no_img]
            st.session_state.active_tab = "optimize"; st.rerun()

    if dry_run: st.warning("🟡 Sandbox — images generated but not uploaded.")

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
        </div>""", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if fix_all_btn:
        auth = make_auth(wp_user, wp_pw)
        prog = st.progress(0)
        for i, post in enumerate(no_img):
            pid   = post["id"]
            title = post["title"]["rendered"]
            st.write(f"**⏳ {title}**")
            try:
                raw       = run_ai(f"2-sentence photorealistic image prompt for '{title}'. Plain text.",
                                   provider, ai_key, ai_model, 0.1, enable_fallback=enable_fallback, fallback_keys=fallback_keys)
                img_prompt = " ".join(raw.replace("*","").replace('"','').split())[:800]
                seo_alt    = run_ai(f"SEO image alt under 120 chars for '{title}'. No quotes.",
                                    provider, ai_key, ai_model, 0.1, enable_fallback=enable_fallback, fallback_keys=fallback_keys).replace('"','')
                img_bytes  = None
                for attempt in range(3):
                    try:
                        img_bytes = gen_image_dalle(img_prompt, dalle_key or ai_key, dalle_style) if image_provider=="DALL-E 3" and (dalle_key or ai_key) else gen_image_pollinations(img_prompt)
                        st.image(img_bytes, caption=seo_alt, width=320); break
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
        st.success("✅ Done!")

# ════════════════════════════════════════════════════════════
#  CREATE POSTS
# ════════════════════════════════════════════════════════════
elif active == "create":
    st.markdown("""<div class='section-head'>
      <h3>✨ Create new posts</h3>
      <span class='hint'>Full content · SEO · image · schema · smart scheduling</span>
    </div>""", unsafe_allow_html=True)

    st.markdown("<div style='padding:0 28px'>", unsafe_allow_html=True)
    c1, c2 = st.columns([3,2])
    with c1:
        topics_raw = st.text_area("Topics — one per line",
            placeholder="10 easy vegan breakfast ideas\nHow to make oat milk at home\nBest plant-based protein sources",
            height=160)
        fix_lang = st.selectbox("Language", ["English","French","Spanish","Arabic","German","Italian","Portuguese"])
        fix_tone = st.selectbox("Tone", ["Informative & SEO-optimized","Conversational & friendly",
                                         "Professional & authoritative","Listicle / step-by-step"])
    with c2:
        fix_words     = st.select_slider("Word count", options=[300,500,800,1200,1800,2500], value=800)
        pub_status    = st.radio("Publish as", ["draft","publish","private"], index=0)
        auto_category = st.toggle("AI picks category", value=True)
        cat_id        = "" if auto_category else st.text_input("Category ID", placeholder="e.g. 5")
        tag_ids       = st.text_input("Tag IDs (optional)", placeholder="12,34,56")
        create_img    = st.toggle("Generate featured image", value=True)
        create_seo    = st.toggle("SEO meta + Yoast", value=True)
        create_schema = st.toggle("Schema.org JSON-LD", value=True)
        create_dry    = st.toggle("Sandbox preview only", value=True)
    st.markdown("</div>", unsafe_allow_html=True)

    topics_preview = [t.strip() for t in (topics_raw or "").strip().splitlines() if t.strip()]
    n_topics = len(topics_preview)

    if enable_schedule and n_topics > 0:
        _slots_prev = calculate_post_schedule(n_topics, posts_per_day, schedule_start_h, start_from_now)
        _now_utc    = datetime.utcnow()
        _future_c   = sum(1 for s in _slots_prev if s > _now_utc)
        _last_slot  = _slots_prev[-1].strftime("%d %b %H:%M UTC") if _slots_prev else "—"
        st.markdown(f"""
        <div style='margin:0 24px 14px;padding:14px 18px;
            background:rgba(55,138,221,0.07);border:1px solid rgba(55,138,221,0.2);border-radius:12px'>
          <div style='font-size:13.5px;font-weight:600;color:#378ADD;margin-bottom:8px'>
            ⏰ Smart scheduling: {n_topics} posts · 1 every {_interval_min} min · last: {_last_slot}
          </div>
          <div style='font-size:12px;color:rgba(168,157,220,0.7)'>
            🕐 {_future_c} scheduled (future) · ⚡ {n_topics-_future_c} immediate · ⏸ {delay_between_api}s delay between calls
          </div>
        </div>""", unsafe_allow_html=True)

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
                  <span class='sched-status {"future" if is_future else "now"}'>{"🕐 future" if is_future else "⚡ now"}</span>
                </div>"""
            if n_topics > 8:
                rows_html += f"<div class='sched-row' style='color:rgba(168,157,220,0.4);font-size:12px'>… and {n_topics-8} more up to {_last_slot}</div>"
            st.markdown(f"""<div class='sched-card' style='margin:0 24px 14px'>
              <div class='sched-card-head'>
                <span class='sched-card-title'>📅 Schedule preview</span>
                <span class='sched-card-badge'>{n_topics} posts · {_interval_min} min apart</span>
              </div>{rows_html}</div>""", unsafe_allow_html=True)

    if create_dry: st.warning("🟡 Sandbox — posts previewed but not pushed to WordPress.")
    else: st.error("🔴 Live — posts will be created on your WordPress site.")

    st.markdown("<div style='padding:0 28px 20px'>", unsafe_allow_html=True)
    create_btn = st.button("✨ Generate & schedule posts", type="primary", use_container_width=True,
                           disabled=(not topics_raw or not topics_raw.strip() or not ai_key))
    st.markdown("</div>", unsafe_allow_html=True)

    if create_btn:
        auth   = make_auth(wp_user, wp_pw)
        topics = [t.strip() for t in topics_raw.strip().splitlines() if t.strip()]
        schedule_slots = calculate_post_schedule(len(topics), posts_per_day, schedule_start_h, start_from_now) if enable_schedule else [None]*len(topics)
        prog = st.progress(0)
        created_ok, created_err = [], []
        now_utc = datetime.utcnow()

        for i, topic in enumerate(topics):
            scheduled_dt = schedule_slots[i]
            if enable_schedule and scheduled_dt and scheduled_dt > now_utc:
                wp_status = "future"; date_iso = scheduled_dt.strftime("%Y-%m-%dT%H:%M:%S")
                sched_label = scheduled_dt.strftime("%d %b · %H:%M UTC")
            elif enable_schedule and scheduled_dt:
                wp_status = pub_status; date_iso = scheduled_dt.strftime("%Y-%m-%dT%H:%M:%S")
                sched_label = "⚡ immediate"
            else:
                wp_status = pub_status; date_iso = None; sched_label = "immediate"

            st.markdown(f"""<div class='panel-box' style='margin:0 28px 12px'>
              <div class='panel-box-head'>
                <h4>{"⏰" if wp_status=="future" else "⚡"} {topic}</h4>
                <span class='hint'>{"🕐 " + sched_label if enable_schedule else ""}</span>
              </div>""", unsafe_allow_html=True)
            col1, col2 = st.columns([3,1])

            try:
                with col1: st.info("✍️ Writing content...")
                post_html = run_ai(
                    f"Blog post about: {topic}\nLanguage: {fix_lang}\nTone: {fix_tone}\n~{fix_words} words. Include intro, subheadings, tips, CTA.\nReturn HTML body only.",
                    provider, ai_key, ai_model, 0.6,
                    "You are an expert SEO content writer. Write well-structured HTML (h2,h3,p,ul,strong). No html/head/body tags. Raw HTML only.",
                    enable_fallback, fallback_keys
                ).replace("```html","").replace("```","").strip()

                meta_desc, focus_kw, exc_text = "", "", ""
                if create_seo:
                    with col1: st.info("🔍 SEO meta...")
                    plain = BeautifulSoup(post_html,"html.parser").get_text()
                    seo   = generate_seo_meta(topic, plain, provider, ai_key, ai_model, enable_fallback, fallback_keys)
                    meta_desc = seo.get("meta_description",""); focus_kw = seo.get("focus_keyword",""); exc_text = seo.get("excerpt","")

                if create_schema:
                    tag = '<script type="application/ld+json">' + generate_schema_jsonld(topic, f"https://{domain}/", date_iso or datetime.utcnow().isoformat(), meta_desc or exc_text) + '</script>'
                    post_html = tag + "\n" + post_html

                media_id, img_bytes, seo_alt = None, None, ""
                if create_img:
                    with col1: st.info("🎨 Generating image...")
                    raw       = run_ai(f"2-sentence photorealistic image prompt for '{topic}'. Plain text.", provider, ai_key, ai_model, 0.1, enable_fallback=enable_fallback, fallback_keys=fallback_keys)
                    ipr       = " ".join(raw.replace("*","").replace('"','').split())[:800]
                    seo_alt   = run_ai(f"SEO image alt under 120 chars for '{topic}'. No quotes.", provider, ai_key, ai_model, 0.1, enable_fallback=enable_fallback, fallback_keys=fallback_keys).replace('"','')
                    for attempt in range(3):
                        try:
                            img_bytes = gen_image_dalle(ipr, dalle_key or ai_key, dalle_style) if image_provider=="DALL-E 3" and (dalle_key or ai_key) else gen_image_pollinations(ipr)
                            with col2: st.image(img_bytes, caption=seo_alt); break
                        except Exception as ie:
                            if attempt == 2:
                                with col1: st.warning(f"Image: {ie}")
                            else: time.sleep(3)

                if create_dry:
                    with col1:
                        st.markdown(f'<span class="run-badge {"sched" if wp_status=="future" else "skip"}">{"🕐 Would schedule: "+sched_label if wp_status=="future" else "🟡 Preview only"}</span>', unsafe_allow_html=True)
                        with st.expander("View generated content"):
                            if meta_desc: st.write(f"**Meta:** {meta_desc}")
                            if focus_kw:  st.write(f"**KW:** {focus_kw}")
                            st.write(f"**WP Status:** `{wp_status}`")
                            if date_iso: st.write(f"**Date:** `{date_iso}` UTC")
                            st.code(post_html[:1500]+"...", language="html")
                    created_ok.append(topic)
                else:
                    if img_bytes:
                        try: media_id = upload_wp_image(img_bytes, topic, seo_alt, auth, domain, optimize_seo_img)
                        except Exception as ue:
                            with col1: st.warning(f"Upload failed: {ue}")

                    pl = {"title":topic,"content":post_html,"status":wp_status,"excerpt":exc_text}
                    if media_id: pl["featured_media"] = media_id
                    if date_iso: pl["date"] = date_iso

                    resolved_cat = None
                    if auto_category:
                        wp_cats = fetch_wp_categories(auth, domain)
                        if wp_cats:
                            plain_txt    = BeautifulSoup(post_html,"html.parser").get_text()
                            resolved_cat = ai_pick_category(topic, plain_txt, wp_cats, provider, ai_key, ai_model, enable_fallback, fallback_keys)
                            if resolved_cat:
                                cat_name = next((n for n,cid in wp_cats.items() if cid==resolved_cat), "?")
                                with col1: st.caption(f"🏷️ Category: **{cat_name}**")
                    elif cat_id and cat_id.strip().isdigit():
                        resolved_cat = int(cat_id.strip())
                    if resolved_cat: pl["categories"] = [resolved_cat]
                    if tag_ids.strip():
                        tids = [int(t.strip()) for t in tag_ids.split(",") if t.strip().isdigit()]
                        if tids: pl["tags"] = tids

                    r = wp_create_post(pl, auth, domain)
                    if r and r.status_code == 201:
                        new_id = r.json().get("id"); new_link = r.json().get("link","")
                        with col1:
                            st.markdown(f'<span class="run-badge {"sched" if wp_status=="future" else "ok"}">{"🕐 Scheduled: "+sched_label if wp_status=="future" else "✅ Published"}</span>', unsafe_allow_html=True)
                            st.caption(f"Post #{new_id} · {new_link}")
                        if create_seo and meta_desc: update_yoast_meta(new_id, meta_desc, focus_kw, auth, domain)
                        st.session_state.created_log.append({"topic":topic,"id":new_id,"link":new_link,"scheduled":date_iso if wp_status=="future" else ""})
                        created_ok.append(topic)
                    else:
                        code = r.status_code if r else "no response"
                        with col1: st.markdown(f'<span class="run-badge err">❌ HTTP {code}</span>', unsafe_allow_html=True)
                        created_err.append(topic)
            except Exception as e:
                with col1: st.error(f"Error: {e}")
                created_err.append(topic)

            st.markdown("</div>", unsafe_allow_html=True)
            prog.progress((i+1)/len(topics))
            if i < len(topics)-1: time.sleep(delay_between_api)

        sched_done = sum(1 for c in st.session_state.created_log[-len(topics):] if c.get("scheduled"))
        st.success(f"✨ Done! ⏰ {sched_done} scheduled · ✅ {len(created_ok)-sched_done} immediate · ❌ {len(created_err)} failed")

# ════════════════════════════════════════════════════════════
#  SEO TOOLS
# ════════════════════════════════════════════════════════════
elif active == "seo":
    posts = st.session_state.posts
    render_stats()
    st.markdown("""<div class='section-head'>
      <h3>🔍 SEO batch optimizer</h3>
      <span class='hint'>Meta descriptions · Focus keywords · Yoast · RankMath</span>
    </div>""", unsafe_allow_html=True)

    st.markdown("<div style='padding:0 28px 20px'>", unsafe_allow_html=True)
    seo_only_btn = st.button(f"🔍 Run SEO on {len(st.session_state.selected)} selected posts",
                             type="primary", use_container_width=True,
                             disabled=(not st.session_state.selected or not ai_key))
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
                seo       = generate_seo_meta(title, plain, provider, ai_key, ai_model, enable_fallback, fallback_keys)
                meta_desc = seo.get("meta_description",""); focus_kw = seo.get("focus_keyword",""); exc_text = seo.get("excerpt","")
                if not dry_run:
                    wp_update_post(pid, {"excerpt":exc_text}, auth, domain)
                    update_yoast_meta(pid, meta_desc, focus_kw, auth, domain)
                st.markdown(f"""
                <div class='post-row-ui'>
                  <div class='post-thumb has'>✓</div>
                  <div class='post-info'>
                    <div class='post-title-ui'>{title}</div>
                    <div class='post-meta-ui'><b>KW:</b> {focus_kw} · <b>Meta:</b> {meta_desc[:80]}…</div>
                  </div>
                  <span class='pill {"done" if not dry_run else "running"}'>{"✓ pushed" if not dry_run else "🟡 preview"}</span>
                </div>""", unsafe_allow_html=True)
            except Exception as e:
                st.error(f"{title}: {e}")
            prog.progress((i+1)/len(to_do))
            time.sleep(0.5)
        st.success("✅ SEO done!")
