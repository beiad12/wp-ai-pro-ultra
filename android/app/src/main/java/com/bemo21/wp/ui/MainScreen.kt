package com.bemo21.wp.ui

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Chat
import androidx.compose.material.icons.filled.Dashboard
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import com.bemo21.wp.data.BemoCredentials
import com.bemo21.wp.ui.chat.ChatScreen
import com.bemo21.wp.ui.dashboard.DashboardScreen
import com.bemo21.wp.ui.settings.SettingsScreen
import com.bemo21.wp.work.SiteSyncWorker
import androidx.compose.ui.platform.LocalContext

@Composable
fun MainScreen(
    screen: Screen,
    creds: BemoCredentials,
    onScreenChange: (Screen) -> Unit,
    onSaveSettings: (BemoCredentials) -> Unit,
    onDisconnect: () -> Unit
) {
    val context = LocalContext.current
    Scaffold(
        bottomBar = {
            NavigationBar {
                NavigationBarItem(
                    selected = screen == Screen.DASHBOARD,
                    onClick = { onScreenChange(Screen.DASHBOARD) },
                    icon = { Icon(Icons.Filled.Dashboard, contentDescription = "Dashboard") },
                    label = { Text("Dashboard") }
                )
                NavigationBarItem(
                    selected = screen == Screen.CHAT,
                    onClick = { onScreenChange(Screen.CHAT) },
                    icon = { Icon(Icons.AutoMirrored.Filled.Chat, contentDescription = "Chat") },
                    label = { Text("Chat") }
                )
                NavigationBarItem(
                    selected = screen == Screen.SETTINGS,
                    onClick = { onScreenChange(Screen.SETTINGS) },
                    icon = { Icon(Icons.Filled.Settings, contentDescription = "Settings") },
                    label = { Text("Settings") }
                )
            }
        }
    ) { padding ->
        Box(modifier = Modifier.padding(padding)) {
            when (screen) {
                Screen.DASHBOARD -> DashboardScreen(creds, onOpenChat = { onScreenChange(Screen.CHAT) })
                Screen.CHAT -> ChatScreen(creds)
                Screen.SETTINGS -> SettingsScreen(
                    creds = creds,
                    onSave = { updated ->
                        onSaveSettings(updated)
                        if (updated.backgroundSyncEnabled) SiteSyncWorker.enable(context) else SiteSyncWorker.disable(context)
                    },
                    onDisconnect = {
                        SiteSyncWorker.disable(context)
                        onDisconnect()
                    }
                )
                Screen.ONBOARDING -> Unit
            }
        }
    }
}
