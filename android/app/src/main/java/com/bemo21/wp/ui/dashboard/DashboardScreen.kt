package com.bemo21.wp.ui.dashboard

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.bemo21.wp.data.BemoCredentials
import com.bemo21.wp.data.WpPost
import com.bemo21.wp.data.network.WordPressApi
import com.bemo21.wp.ui.CardSpacing
import com.bemo21.wp.ui.EmptyState
import com.bemo21.wp.ui.GradientHero
import com.bemo21.wp.ui.PillTone
import com.bemo21.wp.ui.ScreenPadding
import com.bemo21.wp.ui.SectionHeader
import com.bemo21.wp.ui.StatCard
import com.bemo21.wp.ui.StatusPill
import kotlinx.coroutines.launch

@Composable
fun DashboardScreen(creds: BemoCredentials, onOpenChat: () -> Unit) {
    var loading by remember { mutableStateOf(true) }
    var posts by remember { mutableStateOf<List<WpPost>>(emptyList()) }
    var error by remember { mutableStateOf<String?>(null) }
    val scope = rememberCoroutineScope()

    fun refresh() {
        loading = true; error = null
        scope.launch {
            val api = WordPressApi(creds)
            api.fetchPosts("publish", 30).fold(
                onSuccess = { posts = it },
                onFailure = { error = it.message }
            )
            loading = false
        }
    }

    LaunchedEffect(creds.domain) { refresh() }

    val noImage = posts.count { !it.hasFeaturedImage }
    val thin = posts.count { it.wordCount < 200 }
    val greetingName = creds.yourName.ifBlank { creds.wpUsername }

    LazyColumn(
        modifier = Modifier.fillMaxSize().padding(ScreenPadding),
        verticalArrangement = Arrangement.spacedBy(CardSpacing),
        contentPadding = PaddingValues(bottom = 24.dp)
    ) {
        item {
            GradientHero(
                title = "Hey ${greetingName.ifBlank { "there" }} 👋",
                subtitle = "Bemo21 is watching over ${creds.domain}",
                statusLine = if (creds.sandboxMode) "🟡 Sandbox mode — previews only" else "🔴 Live mode — changes are real"
            )
        }

        item {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                StatusPill("🔗 Connected", PillTone.SUCCESS)
                StatusPill(creds.aiProvider.label, PillTone.NEUTRAL)
            }
        }

        if (loading) {
            item {
                Row(Modifier.fillMaxWidth().padding(24.dp), horizontalArrangement = Arrangement.Center) {
                    CircularProgressIndicator()
                }
            }
        } else if (error != null) {
            item { EmptyState("⚠️", error ?: "Something went wrong") }
        } else {
            item {
                SectionHeader("Your site at a glance")
                Row(horizontalArrangement = Arrangement.spacedBy(CardSpacing)) {
                    StatCard("📄", "Published posts", posts.size.toString(), modifier = Modifier.weight(1f))
                    StatCard("🚫", "Missing images", noImage.toString(), modifier = Modifier.weight(1f))
                }
            }
            item {
                Row(horizontalArrangement = Arrangement.spacedBy(CardSpacing)) {
                    StatCard("📝", "Thin content", thin.toString(), modifier = Modifier.weight(1f))
                    StatCard("✅", "Healthy posts", (posts.size - thin).coerceAtLeast(0).toString(), modifier = Modifier.weight(1f))
                }
            }
            item {
                Card(
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Column(Modifier.padding(16.dp)) {
                        Text("Need something done?", style = MaterialTheme.typography.titleMedium)
                        Text(
                            "Open Chat and just ask — \"write a post about summer sales\" or \"fix my missing meta descriptions\".",
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            modifier = Modifier.padding(top = 4.dp, bottom = 12.dp)
                        )
                        Button(onClick = onOpenChat, modifier = Modifier.fillMaxWidth()) { Text("💬 Open chat") }
                    }
                }
            }
            if (posts.isNotEmpty()) {
                item { SectionHeader("Recent posts") }
                items(posts.take(8)) { post ->
                    Card(modifier = Modifier.fillMaxWidth()) {
                        Column(Modifier.padding(14.dp)) {
                            Text(post.title, style = MaterialTheme.typography.titleMedium)
                            Text(
                                "${post.wordCount} words · ${if (post.hasFeaturedImage) "has image" else "no image"}",
                                style = MaterialTheme.typography.bodyMedium,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    }
                }
            } else {
                item { EmptyState("📭", "No published posts found yet.") }
            }
        }
    }
}
