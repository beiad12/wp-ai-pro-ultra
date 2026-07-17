package com.bemo21.wp.data.store

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import com.bemo21.wp.data.AiProvider
import com.bemo21.wp.data.BemoCredentials

/**
 * All WordPress/AI credentials live only in this device's encrypted local
 * storage (AndroidX Security / Keystore-backed AES256-GCM) — nothing is
 * synced anywhere, and the app never talks to any machine except the
 * user's own WordPress site and their chosen AI provider.
 */
class CredentialStore(context: Context) {
    private val prefs: SharedPreferences by lazy {
        val masterKey = MasterKey.Builder(context)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
            .build()
        EncryptedSharedPreferences.create(
            context,
            "bemo21_secure_prefs",
            masterKey,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
        )
    }

    fun load(): BemoCredentials = BemoCredentials(
        domain = prefs.getString(KEY_DOMAIN, "") ?: "",
        wpUsername = prefs.getString(KEY_WP_USER, "") ?: "",
        wpAppPassword = prefs.getString(KEY_WP_PASS, "") ?: "",
        aiProvider = AiProvider.fromLabel(prefs.getString(KEY_AI_PROVIDER, AiProvider.CLAUDE.label) ?: AiProvider.CLAUDE.label),
        aiModel = prefs.getString(KEY_AI_MODEL, AiProvider.CLAUDE.defaultModel) ?: AiProvider.CLAUDE.defaultModel,
        aiApiKey = prefs.getString(KEY_AI_KEY, "") ?: "",
        agencyName = prefs.getString(KEY_AGENCY, "") ?: "",
        yourName = prefs.getString(KEY_NAME, "") ?: "",
        sandboxMode = prefs.getBoolean(KEY_SANDBOX, true),
        backgroundSyncEnabled = prefs.getBoolean(KEY_BG_SYNC, false)
    )

    fun save(creds: BemoCredentials) {
        prefs.edit()
            .putString(KEY_DOMAIN, creds.domain)
            .putString(KEY_WP_USER, creds.wpUsername)
            .putString(KEY_WP_PASS, creds.wpAppPassword)
            .putString(KEY_AI_PROVIDER, creds.aiProvider.label)
            .putString(KEY_AI_MODEL, creds.aiModel)
            .putString(KEY_AI_KEY, creds.aiApiKey)
            .putString(KEY_AGENCY, creds.agencyName)
            .putString(KEY_NAME, creds.yourName)
            .putBoolean(KEY_SANDBOX, creds.sandboxMode)
            .putBoolean(KEY_BG_SYNC, creds.backgroundSyncEnabled)
            .apply()
    }

    fun clear() = prefs.edit().clear().apply()

    fun hasOnboarded(): Boolean = load().isWpComplete

    companion object {
        private const val KEY_DOMAIN = "domain"
        private const val KEY_WP_USER = "wp_user"
        private const val KEY_WP_PASS = "wp_pass"
        private const val KEY_AI_PROVIDER = "ai_provider"
        private const val KEY_AI_MODEL = "ai_model"
        private const val KEY_AI_KEY = "ai_key"
        private const val KEY_AGENCY = "agency"
        private const val KEY_NAME = "your_name"
        private const val KEY_SANDBOX = "sandbox"
        private const val KEY_BG_SYNC = "bg_sync"
    }
}
