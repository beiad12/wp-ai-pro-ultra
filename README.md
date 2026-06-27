# ⚡ WP AI Pro Ultra — Local Desktop Edition

> A powerful AI content studio for WordPress. Runs 100% locally on your PC — no Colab, no ngrok, no subscriptions.

![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-1.35%2B-red?logo=streamlit)
![License](https://img.shields.io/badge/License-MIT-green)
![Version](https://img.shields.io/badge/Version-1.0.0-orange)

---

## ✨ What it does

| Feature | Details |
|---|---|
| 🤖 **AI content writing** | Generate full blog posts from topics — with intros, subheadings, CTAs |
| 🖼️ **Featured images** | Auto-generate & upload images via Pollinations (free) or DALL-E 3 |
| 🔍 **SEO optimization** | Meta descriptions, focus keywords, Yoast/RankMath integration |
| 📅 **Smart scheduling** | Spread up to 500 posts/day evenly across 24 hours automatically |
| 🔧 **Post optimizer** | Fix, rewrite, and improve existing WordPress posts in bulk |
| 📊 **Schema.org JSON-LD** | Auto-inject structured data for better Google rankings |
| 🏷️ **AI category picker** | Automatically assigns the right category to each post |
| ⚡ **Multi-provider AI** | Claude, OpenAI, Gemini, Mistral — with auto-fallback chain |
| 🛡️ **Quality gate** | Skip posts that don't meet minimum word count |
| 💾 **Resume mode** | Crash recovery — pick up exactly where you left off |
| 📥 **CSV export** | Download full results log for every run |

---

## 🚀 Installation — Windows

**Step 1:** Download and unzip this project

**Step 2:** Double-click `install.bat`

**Step 3:** Double-click `START.bat`

The app opens automatically at **http://localhost:8501** 🎉

---

## 🚀 Installation — Mac / Linux

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/wp-ai-pro-ultra.git
cd wp-ai-pro-ultra

# 2. Install & launch (one command)
chmod +x start.sh && ./start.sh
```

The app opens at **http://localhost:8501**

---

## ⚙️ Setup in the app

### 1. Connect your WordPress site
- **Domain:** `yourdomain.com` (no https://)
- **Username:** your WP admin username
- **App Password:** Generate at **WP Admin → Users → Profile → Application Passwords**

### 2. Add an AI key (at least one)

| Provider | Free Tier | Get key |
|---|---|---|
| **Google Gemini** | ✅ Yes | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) |
| **Groq** | ✅ Yes (fast) | [console.groq.com/keys](https://console.groq.com/keys) |
| **OpenAI** | ❌ Paid | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) |
| **Anthropic Claude** | ❌ Paid | [console.anthropic.com](https://console.anthropic.com) |
| **Mistral** | ❌ Paid | [console.mistral.ai](https://console.mistral.ai) |

### 3. Go to Sandbox → OFF when ready to go live

---

## 📖 How to use

### Create 100 posts on a schedule
1. Go to **✨ Create Posts**
2. Paste 100 topics (one per line)
3. Set **Posts per day = 50** → 1 post every 29 minutes
4. Enable **Smart Scheduling**
5. Click **Generate & schedule posts**
6. WordPress automatically publishes them over time ✅

### Fix missing images
1. Go to **📡 Scan & Select** → scan your site
2. Click **🚫 Without image only**
3. Go to **🖼️ Fix Images** → click Generate

### Bulk SEO optimization
1. Scan your site
2. Select posts
3. Go to **🔍 SEO Tools** → Run SEO

---

## 🔑 Tips

- **Always start with Sandbox ON** — preview before going live
- **Pollinations is free** for image generation — no key needed
- **Resume mode** saves progress — safe to close and reopen
- **Workers = 2** is safe for most hosts; increase for VPS
- **App Passwords** work better than your main WP password

---

## 📁 Project structure

```
wp-ai-pro-ultra/
├── app.py              ← Main Streamlit app
├── requirements.txt    ← Python dependencies
├── install.bat         ← Windows one-click installer
├── START.bat           ← Windows launcher (opens browser automatically)
├── start.sh            ← Mac/Linux launcher
└── README.md
```

---

## 🤝 Contributing

Pull requests welcome! Ideas:
- [ ] Gutenberg block editor support
- [ ] WooCommerce product creator
- [ ] Bulk internal linking
- [ ] Multi-site dashboard
- [ ] Export to WordPress XML

---

## 📄 License

MIT — free to use, modify, and distribute.

---

## 🙏 Credits

- AI: Claude (Anthropic), GPT-4 (OpenAI), Gemini (Google), Mistral, Groq
- Images: Pollinations.ai, DALL-E 3
- UI: Streamlit
