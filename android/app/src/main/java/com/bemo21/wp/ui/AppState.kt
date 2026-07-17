package com.bemo21.wp.ui

import android.content.Context
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import com.bemo21.wp.data.BemoCredentials
import com.bemo21.wp.data.store.CredentialStore

enum class Screen { ONBOARDING, DASHBOARD, CHAT, SETTINGS }

/** Holds the single source of truth for credentials + current screen, backed by encrypted local storage. */
class AppState(context: Context) {
    private val store = CredentialStore(context.applicationContext)

    var credentials by mutableStateOf(store.load())
        private set

    var screen by mutableStateOf(if (store.hasOnboarded()) Screen.DASHBOARD else Screen.ONBOARDING)

    fun update(creds: BemoCredentials) {
        credentials = creds
        store.save(creds)
    }

    fun completeOnboarding(creds: BemoCredentials) {
        update(creds)
        screen = Screen.DASHBOARD
    }

    fun resetAll() {
        store.clear()
        credentials = BemoCredentials()
        screen = Screen.ONBOARDING
    }
}
