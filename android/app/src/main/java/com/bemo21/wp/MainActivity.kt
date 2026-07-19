package com.bemo21.wp

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import com.bemo21.wp.ui.MainScreen
import com.bemo21.wp.ui.Screen
import com.bemo21.wp.ui.AppState
import com.bemo21.wp.ui.onboarding.OnboardingScreen
import com.bemo21.wp.ui.theme.Bemo21Theme
import com.bemo21.wp.work.SiteSyncWorker

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            val appState = remember { AppState(applicationContext) }

            if (appState.credentials.backgroundSyncEnabled) {
                SiteSyncWorker.enable(applicationContext)
            }

            Bemo21Theme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    when (appState.screen) {
                        Screen.ONBOARDING -> OnboardingScreen(onComplete = { appState.completeOnboarding(it) })
                        else -> MainScreen(
                            screen = appState.screen,
                            overlay = appState.overlay,
                            creds = appState.credentials,
                            onScreenChange = { appState.screen = it; appState.overlay = null },
                            onOpenOverlay = { appState.overlay = it },
                            onSaveSettings = { appState.update(it) },
                            onDisconnect = { appState.resetAll() }
                        )
                    }
                }
            }
        }
    }
}
