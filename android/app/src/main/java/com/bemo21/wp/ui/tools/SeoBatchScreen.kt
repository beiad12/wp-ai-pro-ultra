package com.bemo21.wp.ui.tools

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
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
import com.bemo21.wp.data.network.AiClient
import com.bemo21.wp.data.network.WordPressApi
import com.bemo21.wp.ui.EmptyState
import com.bemo21.wp.ui.LoadingBlock
import com.bemo21.wp.ui.ScreenPadding
import com.bemo21.wp.ui.ToolTopBar
import kotlinx.coroutines.launch

private data class RowState(val post: WpPost, val status: String, val detail: String)

@Composable
fun SeoBatchScreen(creds: BemoCredentials, onBack: () -> Unit) {
    var loading by remember { mutableStateOf(true) }
    var targets by remember { mutableStateOf<List<RowState>>(emptyList()) }
    var error by remember { mutableStateOf<String?>(null) }
    var running by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()
    val api = remember(creds) { WordPressApi(creds) }
    val aiClient = remember { AiClient() }

    LaunchedEffect(Unit) {
        loading = true
        api.fetchPosts("publish", 50).fold(
            onSuccess = { posts -> targets = posts.filter { it.excerpt.isBlank() }.map { RowState(it, "pending", "Waiting") } },
            onFailure = { error = it.message }
        )
        loading = false
    }

    Scaffold(topBar = { ToolTopBar("SEO batch fix", onBack) }) { padding ->
        Column(Modifier.fillMaxSize().padding(padding)) {
            when {
                loading -> LoadingBlock("Scanning posts for missing meta descriptions...")
                error != null -> EmptyState("⚠️", error ?: "Something went wrong")
                targets.isEmpty() -> EmptyState("🎉", "Every published post already has a meta description.")
                else -> {
                    Column(Modifier.padding(ScreenPadding)) {
                        Text(
                            "${targets.size} post(s) missing a meta description" + if (creds.sandboxMode) " · 🟡 Sandbox preview" else "",
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                        Button(
                            onClick = {
                                running = true
                                scope.launch {
                                    for (i in targets.indices) {
                                        val row = targets[i]
                                        if (row.status == "done") continue
                                        targets = targets.toMutableList().also { it[i] = row.copy(status = "running", detail = "Writing...") }
                                        val prompt = "Write a compelling 150-character max SEO meta description for this blog post titled '${row.post.title}'. Plain text only, no quotes."
                                        val result = aiClient.complete(creds.aiProvider, creds.aiApiKey, creds.aiModel, prompt, null, 0.4)
                                        val newState = result.fold(
                                            onSuccess = { text ->
                                                val excerpt = text.replace("\"", "").trim()
                                                if (creds.sandboxMode) {
                                                    row.copy(status = "done", detail = "🟡 Preview: $excerpt")
                                                } else {
                                                    val upd = api.updatePost(row.post.id, mapOf("excerpt" to excerpt))
                                                    if (upd.isSuccess) row.copy(status = "done", detail = "✅ $excerpt")
                                                    else row.copy(status = "error", detail = "⚠️ ${upd.exceptionOrNull()?.message}")
                                                }
                                            },
                                            onFailure = { row.copy(status = "error", detail = "⚠️ ${it.message}") }
                                        )
                                        targets = targets.toMutableList().also { it[i] = newState }
                                    }
                                    running = false
                                }
                            },
                            enabled = !running && creds.isAiComplete,
                            modifier = Modifier.fillMaxWidth().padding(top = 10.dp)
                        ) {
                            if (running) {
                                CircularProgressIndicator(modifier = Modifier.padding(end = 8.dp))
                                Text("Working...")
                            } else {
                                Text("🔍 Fix all ${targets.size}")
                            }
                        }
                    }
                    LazyColumn(
                        modifier = Modifier.fillMaxSize().padding(horizontal = ScreenPadding),
                        verticalArrangement = Arrangement.spacedBy(8.dp),
                        contentPadding = PaddingValues(bottom = 24.dp)
                    ) {
                        items(targets, key = { it.post.id }) { row ->
                            Card(Modifier.fillMaxWidth()) {
                                Column(Modifier.padding(12.dp)) {
                                    Text(row.post.title, style = MaterialTheme.typography.titleMedium)
                                    Text(
                                        row.detail, style = MaterialTheme.typography.bodyMedium,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                                        modifier = Modifier.padding(top = 2.dp)
                                    )
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
