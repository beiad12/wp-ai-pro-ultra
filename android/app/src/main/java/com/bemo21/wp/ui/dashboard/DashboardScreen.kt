package com.bemo21.wp.ui.dashboard

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.bemo21.wp.data.BemoCredentials
import com.bemo21.wp.data.WpPost
import com.bemo21.wp.data.network.WordPressApi
import com.bemo21.wp.ui.CardSpacing
import com.bemo21.wp.ui.EmptyState
import com.bemo21.wp.ui.GradientHero
import com.bemo21.wp.ui.LoadingBlock
import com.bemo21.wp.ui.PillTone
import com.bemo21.wp.ui.ScreenPadding
import com.bemo21.wp.ui.SectionHeader
import com.bemo21.wp.ui.StatCard
import com.bemo21.wp.ui.StatusPill
import kotlinx.coroutines.launch

@Composable
fun DashboardScreen(
    creds: BemoCredentials,
    onOpenSiteHealth: () -> Unit,
    onOpenPost: (Int) -> Unit
) {
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
    val thin = posts.count { it.isThin }
    val noMeta = posts.count { it.excerpt.isBlank() }
    val greetingName = creds.yourName.ifBlank { creds.wpUsername }

    LazyColumn(
        modifier = Modifier.fillMaxSize().padding(ScreenPadding),
        verticalArrangement = Arrangement.spacedBy(CardSpacing),
        contentPadding = PaddingValues(bottom = 24.dp)
    ) {
        item {
            GradientHero(
                title = "Hey ${greetingName.ifBlank { "there" }} 👋",
                subtitle = creds.domain,
                statusLine = if (creds.sandboxMode) "🟡 Sandbox mode — previews only" else "🔴 Live mode — changes are real"
            )
        }

        item {
            Card(
                modifier = Modifier.fillMaxWidth().clickable(onClick = onOpenSiteHealth),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
                shape = RoundedCornerShape(16.dp)
            ) {
                Row(Modifier.fillMaxWidth().padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
                    Text("🩺", style = MaterialTheme.typography.titleLarge)
                    Column(Modifier.padding(start = 12.dp)) {
                        Text("Run a site health check", style = MaterialTheme.typography.titleMedium)
                        Text(
                            "SSL, speed, mobile-friendliness & more",
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            }
        }

        when {
            loading -> item { LoadingBlock("Loading your site...") }
            error != null -> item { EmptyState("⚠️", error ?: "Something went wrong") }
            else -> {
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
                        StatCard("🔍", "Missing meta", noMeta.toString(), modifier = Modifier.weight(1f))
                    }
                }
                if (posts.isNotEmpty()) {
                    item { SectionHeader("Recent posts") }
                    items(posts.take(6), key = { it.id }) { post -> RecentPostRow(post, onClick = { onOpenPost(post.id) }) }
                } else {
                    item { EmptyState("📭", "No published posts found yet.") }
                }
            }
        }
    }
}

@Composable
private fun RecentPostRow(post: WpPost, onClick: () -> Unit) {
    Card(modifier = Modifier.fillMaxWidth().clickable(onClick = onClick)) {
        Column(Modifier.padding(14.dp)) {
            Text(post.title.ifBlank { "(untitled)" }, style = MaterialTheme.typography.titleMedium)
            Row(modifier = Modifier.padding(top = 6.dp), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                Text(
                    "${post.wordCount} words",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                if (!post.hasFeaturedImage) StatusPill("No image", PillTone.WARN)
            }
        }
    }
}
