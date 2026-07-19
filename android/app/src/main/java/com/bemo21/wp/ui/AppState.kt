package com.bemo21.wp.ui

import android.content.Context
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import com.bemo21.wp.data.BemoCredentials
import com.bemo21.wp.data.store.CredentialStore

enum class Screen { ONBOARDING, DASHBOARD, POSTS, TOOLS, SETTINGS }

/** Full-screen tool overlays, pushed on top of the bottom-nav screens with their own back button. */
sealed class Overlay {
    data object CreatePost : Overlay()
    data object SeoBatch : Overlay()
    data object FixImages : Overlay()
    data object SiteHealth : Overlay()
    data class PostDetail(val postId: Int) : Overlay()
}

/** Holds the single source of truth for credentials + navigation, backed by encrypted local storage. */
class AppState(context: Context) {
    private val store = CredentialStore(context.applicationContext)

    var credentials by mutableStateOf(store.load())
        private set

    var screen by mutableStateOf(if (store.hasOnboarded()) Screen.DASHBOARD else Screen.ONBOARDING)
    var overlay by mutableStateOf<Overlay?>(null)

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
        overlay = null
        screen = Screen.ONBOARDING
    }
}
