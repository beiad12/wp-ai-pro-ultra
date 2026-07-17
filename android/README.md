# ⚡ Bemo21 — WordPress AI Assistant for Android

A standalone native Android app. It does **not** talk to your PC or the Streamlit desktop tool at all — once installed, it connects directly from your phone to your WordPress site's REST API and to your chosen AI provider's API, using your own Application Password and your own API key.

## What it is

- **Onboarding**: connect your WordPress site (domain, username, Application Password) and your AI provider (Claude / OpenAI / Mistral / Gemini + API key). Both are tested live before you can continue.
- **Dashboard**: a gradient hero card, connection status, post stats (published count, missing images, thin content), and recent posts — all fetched live from your site.
- **Chat**: type what you want in plain language ("write a post about home coffee brewing", "list my recent posts", "fix my missing meta descriptions"). Bemo21's connected AI plans a short list of steps from a fixed, whitelisted tool set (`list_posts`, `create_post`, `fix_seo_meta`) and shows them to you as a checklist — nothing runs until you tap **Run selected**. Sandbox mode (on by default) previews instead of writing.
- **Settings**: edit credentials, toggle Sandbox mode, toggle background site-health sync, disconnect & reset.

All credentials are stored **only on the device**, encrypted at rest via AndroidX Security (`EncryptedSharedPreferences`, AES-256-GCM, backed by the Android Keystore). Nothing syncs to any cloud service Bemo21 controls — there isn't one.

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
│   ├── data/                  ← models, WordPress REST client, AI client, whitelisted tool registry
│   ├── ui/
│   │   ├── onboarding/        ← WordPress + AI connection flow
│   │   ├── dashboard/         ← stats & recent posts
│   │   ├── chat/              ← the conversational assistant
│   │   ├── settings/
│   │   └── theme/             ← Bemo21's Material3 theme (purple/indigo, matches the desktop app)
│   └── work/SiteSyncWorker.kt ← periodic background health check (WorkManager)
└── app/src/main/AndroidManifest.xml
```

## What's real vs. what's next

Every action in Chat is a genuine network call — post creation, listing, and SEO meta writes go through the actual WordPress REST API, and content generation calls your actual AI provider. Nothing is faked. What's scoped out of this first version (and honestly so, not silently skipped): featured-image generation/upload, the full Site Health audit suite (technical/security/performance/SEO crawl), and PDF reporting — all of which exist in the desktop app and are natural next additions here once this core flow is confirmed working well on a real device.
