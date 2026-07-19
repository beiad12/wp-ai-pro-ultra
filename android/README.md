# ⚡ Bemo21 — WordPress AI Assistant for Android

A standalone native Android app. It does **not** talk to your PC or the Streamlit desktop tool at all — once installed, it connects directly from your phone to your WordPress site's REST API and to your chosen AI provider's API, using your own Application Password and your own API key.

## What it is

- **Onboarding**: connect your WordPress site (domain, username, Application Password) and your AI provider (Claude / OpenAI / Mistral / Gemini + API key). Both are tested live before you can continue.
- **Dashboard**: a gradient hero card, live post stats (published count, missing images, thin content, missing meta), a one-tap site health check, and recent posts — all fetched live from your site. Tapping a post opens it directly.
- **Posts**: search and filter your posts (published/draft/private), each with at-a-glance badges for missing image / thin content / missing meta. Tap through to a post for per-post actions.
- **Tools** — dedicated, real screens instead of a chat detour:
  - ✨ **Create post** — a form (topic, target length, publish-now vs. draft), writes real HTML via your AI provider and an SEO meta description, then publishes through the WordPress REST API.
  - 🔍 **SEO batch fix** — scans every published post for a missing meta description and fixes them one by one with a live progress list.
  - 🖼️ **Fix missing images** — generates a featured image (free, keyless Pollinations) for every post missing one, uploads it to your media library, and attaches it.
  - 🩺 **Site health check** — SSL certificate validity, response time, page weight, compression, title/meta tag length, mobile viewport tag, H1 usage, homepage image alt text, robots.txt and sitemap.xml — checked live against your homepage, no WP-admin login required.
- **Settings**: edit credentials, toggle Sandbox mode, toggle background site-health sync, disconnect & reset.

All credentials are stored **only on the device**, encrypted at rest via AndroidX Security (`EncryptedSharedPreferences`, AES-256-GCM, backed by the Android Keystore). Nothing syncs to any cloud service Bemo21 controls — there isn't one.

## Design notes

- One navigation surface (bottom nav: Dashboard / Posts / Tools / Settings) — no shortcut buttons that duplicate a tab that's already one tap away. Tool screens open as full-screen overlays with a single back button.
- Every status (missing image, thin content, pass/warn/fail) is a colored pill, not a wall of text.
- Sandbox mode (on by default) previews every write across every tool identically — post creation, SEO fixes, image fixes — nothing goes live until you turn it off in Settings.

## Being honest about "runs in the background after reboot"

Modern Android (8+) does not allow apps to silently run unlimited background work forever, and Google Play policy blocks most uses of auto-starting a process on boot — that's a deliberate battery/privacy protection, not a bug to route around. The real, sanctioned way to do recurring background work is **WorkManager**, which is what the "Background site sync" toggle in Settings uses: it periodically checks your site is reachable and posts a notification only if it isn't. WorkManager's own scheduling is restored automatically after a reboot (its boot-rescheduling receiver ships inside the library) — you don't need to reopen the app for it to keep working. What it will **not** do is keep an invisible always-on process alive 24/7 outside that schedule; no legitimate Android app can promise that.

## Building it yourself

You need [Android Studio](https://developer.android.com/studio) (easiest — it bundles the SDK) **or** the command line:

```bash
# from the android/ folder
./gradlew assembleDebug
```

The debug APK lands at `app/build/outputs/apk/debug/app-debug.apk`. Install it on your phone:

```bash
adb install app/build/outputs/apk/debug/app-debug.apk
```

Or just open the `android/` folder in Android Studio, hit **Run**, and pick your device or an emulator.

### Requirements
- JDK 17
- Android SDK (compileSdk 34, build-tools 34.0.0) — Android Studio installs this for you; command-line users need `sdkmanager` with `platforms;android-34` and `build-tools;34.0.0`, and a `local.properties` file pointing `sdk.dir` at it.
- minSdk 26 (Android 8.0+)

## Project layout

```
android/
├── app/src/main/java/com/bemo21/wp/
│   ├── MainActivity.kt
│   ├── data/                  ← models, WordPress REST client, AI client, image generator, site health checker
│   ├── ui/
│   │   ├── onboarding/        ← WordPress + AI connection flow
│   │   ├── dashboard/         ← live stats & recent posts
│   │   ├── posts/             ← post list/search + per-post detail & actions
│   │   ├── tools/             ← Create post, SEO batch fix, Fix images, Site health
│   │   ├── settings/
│   │   └── theme/             ← Bemo21's Material3 theme (purple/indigo, matches the desktop app)
│   └── work/SiteSyncWorker.kt ← periodic background health check (WorkManager)
└── app/src/main/AndroidManifest.xml
```

## What's real vs. what's next

Every tool action is a genuine network call — post creation, listing, SEO meta writes, image generation/upload, and site health checks all go through the actual WordPress REST API and your actual AI provider. Nothing is faked. Scoped out of this pass, on purpose: the full crawl-based SEO audit, security header/plugin checks, and PDF reporting from the desktop app — natural next additions once this core toolset is confirmed working well on a real device.
