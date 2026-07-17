# ⚡ WP AI Pro Ultra — Local Agency Edition

A local-only Streamlit app for agencies managing multiple WordPress sites: AI content generation, SEO tools, and a full technical/security/performance/content audit suite with real, working one-click fixes — fronted by a conversational Agent tab.

Runs 100% on your own PC at `http://localhost:8501`. No Colab, no ngrok, no cloud hosting, no subscriptions.

![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-1.35%2B-red?logo=streamlit)
![License](https://img.shields.io/badge/License-MIT-green)

---

## 🚀 Installation

**Windows:**
1. Download and unzip this project
2. Double-click `run_windows.bat` — it installs dependencies and launches the app with the *same* Python interpreter (avoids the classic "installed but ModuleNotFoundError" mismatch)

**Mac / Linux:**
```bash
git clone https://github.com/YOUR_USERNAME/wp-ai-pro-ultra.git
cd wp-ai-pro-ultra
chmod +x run_mac_linux.sh && ./run_mac_linux.sh
```

Or manually, from this folder, using one Python interpreter for both steps:
```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

The app opens automatically at **http://localhost:8501**.

Core dependencies (`streamlit`, `beautifulsoup4`, `pandas`, `Pillow`, `fpdf2`) are required. The AI provider SDKs (`anthropic`, `openai`, `google-generativeai`) are optional — if one isn't installed, only that provider is disabled with a clear message; the app still starts and Mistral (plain HTTP, no SDK needed) still works.

---

## ⚙️ Setup in the app

In the sidebar:
- **Domain, WP username, WP Application Password** — generate an App Password at WP Admin → Users → Profile → Application Passwords (works better than your real WP password, and can be revoked independently).
- **AI provider + model + API key** — Claude, OpenAI, Mistral, or Gemini, plus optional fallback keys for other providers.
- **Image provider** — Pollinations (free, no key) or DALL-E 3 (needs an OpenAI key).
- **PageSpeed API key** (optional) — raises the rate limit for Core Web Vitals checks; works keyless at low volume.
- **Agency/brand name** and **your name** — used in PDF reports and the Agent's greeting.
- **Sandbox / Live toggle** — Sandbox previews every write (post edits, plugin installs, image uploads); nothing touches your live site until you switch it off.

### Saved site profiles
Under **💾 Saved Sites** in the sidebar: fill in a site's details, give the profile a name, and save it. Next session, pick it from the dropdown and everything — credentials, AI keys, preferences — is restored instantly. No re-typing between client sites.

**Where it's stored:** plain-text local JSON files next to `app.py` — `wp_pro_profiles.json` (site profiles) and `wp_pro_settings.json` (cross-site preferences like your name). Convenient for your own machine, but they contain real passwords and API keys in plaintext — **don't share this folder, commit it to a repo, or sync it anywhere untrusted.** These files are already excluded via `.gitignore`.

---

## ✨ Features

### Content tools
- **Scan & Select** — fetch all posts (paginated), filter by status/missing image, search, bulk select.
- **Optimize Posts** — AI rewrite with custom instructions, minimum word-count quality gate, auto-category detection, resumable/crash-safe batch runs, concurrent workers.
- **Fix Images** — generate + upload featured images with SEO alt text for posts missing one (Pollinations free, or DALL-E 3).
- **Create Posts** — multi-topic batch creation with full SEO metadata, schema.org JSON-LD, and smart scheduling spread across a target posts/day rate over 24 hours. Sandbox previews before anything publishes.
- **SEO Tools** — meta description + focus keyword generation, pushed straight to Yoast/RankMath fields.

### 🩺 Site Health — audit suite with real fixes
Each check below is its own sub-tab with its own "Run" button, plus one "Run full audit" on the Overview tab that runs everything and saves a timestamped snapshot to local per-domain history:

- **Technical** — SSL validity/expiry, response time, page weight, GZIP/Brotli compression, title/meta length, viewport tag, single-H1 check, homepage image alt text, robots.txt, sitemap.xml.
- **Security** — HSTS, clickjacking protection, CSP, X-Content-Type-Options, Referrer-Policy, XML-RPC exposure, upload directory listing, WP version disclosure, username enumeration — all via plain HTTP, no WP-admin login needed.
- **Performance** — real Core Web Vitals (LCP, CLS, TBT, FCP) via the Google PageSpeed Insights API.
- **SEO Crawl** — crawls up to N live post URLs for duplicate titles/meta, missing meta/canonical/OG tags, broken pages, bad H1 counts, orphan pages.
- **Content Quality** — Flesch readability, near-duplicate detection, stale-content flagging, missing images, thin content — each with an immediate ⚡ Fix now.
- **Reports** — branded PDF export, CSV export, and the full scan-history table for the current domain.

**Real fixes, not fake buttons:** XML-RPC and missing security headers install & activate verified, actively-maintained plugins via the `wp/v2/plugins` REST endpoint (handles the "already installed" case, and fails cleanly with manual steps on hosts that require FTP for installs). Slow LCP/FCP installs a caching plugin. High CLS gets a genuine mechanical fix — posts are scanned for `<img>` tags missing `width`/`height`, real pixel sizes are fetched, and the attributes are written back via the REST API. Everything respects Sandbox mode. Things that genuinely need `.htaccess`, hosting-panel, or WP-admin-only access (robots.txt content, version-tag removal, directory-listing config, plugin/theme updates, database optimization, malware scanning, user-account audits) get a clear written recommendation instead of a fake button — see in-app explanations for why.

### 🤖 The Agent tab
Replaces the old static dashboard. On load: a typing indicator, then a time-of-day + name-based greeting, then an offer to run today's check. Say yes and it runs the full audit and summarizes the results in plain language with an action-chip menu (load posts, fix missing images, fix thin/stale content, improve SEO meta, speed up the site, harden security, create posts, get a PDF report, re-run the check). Every action reuses the exact same functions as their dedicated tabs — nothing duplicated — and respects Sandbox mode identically.

**Free-text tool-calling** — below the menu, type a request in your own words (e.g. "optimize my thin posts and generate images for anything missing one"). Your connected LLM plans a short sequence of steps drawn *only* from a fixed, whitelisted tool registry (load posts, fix images, rewrite thin/stale content, fix SEO meta, fix image dimensions, install caching/security plugins, generate a PDF report, create one post). The model never writes or executes code — it only proposes `{tool, args}` steps, which are validated against the registry and shown to you as a checklist before anything runs. Uncheck any step you don't want, then confirm. Plugin installs stay blocked while Sandbox is on, same as everywhere else in the app.

---

## 🔑 Tips

- Always start with **Sandbox ON** to preview before going live.
- Pollinations is free for image generation — no key required.
- Resume mode saves progress to a local JSON file — safe to close and reopen mid-batch.
- Workers = 2 is safe for most hosts; increase for a VPS.

---

## 📁 Project structure

```
wp-ai-pro-ultra/
├── app.py                ← Main Streamlit app (single file)
├── requirements.txt       ← Python dependencies
├── run_windows.bat        ← Windows one-click install + launch
├── run_mac_linux.sh       ← Mac/Linux one-click install + launch
└── README.md
```

Local state files (created on first use, gitignored, plaintext — own machine only):
`wp_pro_profiles.json` (saved site profiles + secrets), `wp_pro_settings.json` (cross-site preferences), `wp_pro_progress.json` (crash-safe batch resume state), `wp_pro_health_history.json` (per-domain score history).

---

## 🚫 Explicitly out of scope

This app never fakes automation for things it genuinely doesn't have access to: plugin/theme *updates*, database optimization, malware scanning, user-account audits, robots.txt content edits, WP version-tag removal, directory-listing configuration, or `.htaccess` edits. Where these come up in an audit, you get a specific written recommendation instead of a button.

---

## 📄 License

MIT — free to use, modify, and distribute.
