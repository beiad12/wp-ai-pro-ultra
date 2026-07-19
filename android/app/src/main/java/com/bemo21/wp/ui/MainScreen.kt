package com.bemo21.wp.ui

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Article
import androidx.compose.material.icons.filled.Build
import androidx.compose.material.icons.filled.Dashboard
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import com.bemo21.wp.data.BemoCredentials
import com.bemo21.wp.ui.dashboard.DashboardScreen
import com.bemo21.wp.ui.posts.PostDetailScreen
import com.bemo21.wp.ui.posts.PostsScreen
import com.bemo21.wp.ui.settings.SettingsScreen
import com.bemo21.wp.ui.tools.CreatePostScreen
import com.bemo21.wp.ui.tools.FixImagesScreen
import com.bemo21.wp.ui.tools.SeoBatchScreen
import com.bemo21.wp.ui.tools.SiteHealthScreen
import com.bemo21.wp.ui.tools.ToolsScreen
import com.bemo21.wp.work.SiteSyncWorker

@Composable
fun MainScreen(
    screen: Screen,
    overlay: Overlay?,
    creds: BemoCredentials,
    onScreenChange: (Screen) -> Unit,
    onOpenOverlay: (Overlay?) -> Unit,
    onSaveSettings: (BemoCredentials) -> Unit,
    onDisconnect: () -> Unit
) {
    if (overlay != null) {
        when (overlay) {
            Overlay.CreatePost -> CreatePostScreen(creds, onBack = { onOpenOverlay(null) })
            Overlay.SeoBatch -> SeoBatchScreen(creds, onBack = { onOpenOverlay(null) })
            Overlay.FixImages -> FixImagesScreen(creds, onBack = { onOpenOverlay(null) })
            Overlay.SiteHealth -> SiteHealthScreen(creds, onBack = { onOpenOverlay(null) })
            is Overlay.PostDetail -> PostDetailScreen(overlay.postId, creds, onBack = { onOpenOverlay(null) })
        }
        return
    }

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
                    selected = screen == Screen.POSTS,
                    onClick = { onScreenChange(Screen.POSTS) },
                    icon = { Icon(Icons.AutoMirrored.Filled.Article, contentDescription = "Posts") },
                    label = { Text("Posts") }
                )
                NavigationBarItem(
                    selected = screen == Screen.TOOLS,
                    onClick = { onScreenChange(Screen.TOOLS) },
                    icon = { Icon(Icons.Filled.Build, contentDescription = "Tools") },
                    label = { Text("Tools") }
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
                Screen.DASHBOARD -> DashboardScreen(
                    creds = creds,
                    onOpenSiteHealth = { onOpenOverlay(Overlay.SiteHealth) },
                    onOpenPost = { onOpenOverlay(Overlay.PostDetail(it)) }
                )
                Screen.POSTS -> PostsScreen(creds, onOpenPost = { onOpenOverlay(Overlay.PostDetail(it)) })
                Screen.TOOLS -> ToolsScreen(onOpen = { onOpenOverlay(it) })
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
