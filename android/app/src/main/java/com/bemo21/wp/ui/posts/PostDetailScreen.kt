package com.bemo21.wp.ui.posts

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
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
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.bemo21.wp.data.BemoCredentials
import com.bemo21.wp.data.WpPost
import com.bemo21.wp.data.network.AiClient
import com.bemo21.wp.data.network.ImageGenerator
import com.bemo21.wp.data.network.WordPressApi
import com.bemo21.wp.ui.LoadingBlock
import com.bemo21.wp.ui.PillTone
import com.bemo21.wp.ui.ScreenPadding
import com.bemo21.wp.ui.StatusPill
import com.bemo21.wp.ui.ToolTopBar
import kotlinx.coroutines.launch
import org.jsoup.Jsoup

@Composable
fun PostDetailScreen(postId: Int, creds: BemoCredentials, onBack: () -> Unit) {
    var loading by remember { mutableStateOf(true) }
    var post by remember { mutableStateOf<WpPost?>(null) }
    var error by remember { mutableStateOf<String?>(null) }
    var actionMessage by remember { mutableStateOf<String?>(null) }
    var actionRunning by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()
    val api = remember(creds) { WordPressApi(creds) }
    val aiClient = remember { AiClient() }
    val imageGen = remember { ImageGenerator() }

    LaunchedEffect(postId) {
        loading = true; error = null
        api.fetchPosts("publish,draft,private", 100).fold(
            onSuccess = { list -> post = list.find { it.id == postId } ?: list.firstOrNull() },
            onFailure = { error = it.message }
        )
        loading = false
    }

    Scaffold(topBar = { ToolTopBar(post?.title?.take(28)?.ifBlank { "Post" } ?: "Post", onBack) }) { padding ->
        when {
            loading -> LoadingBlock("Loading post...")
            error != null -> Column(Modifier.padding(padding)) { com.bemo21.wp.ui.EmptyState("⚠️", error ?: "Couldn't load post") }
            post == null -> Column(Modifier.padding(padding)) { com.bemo21.wp.ui.EmptyState("📭", "Post not found") }
            else -> {
                val p = post!!
                LazyColumn(
                    modifier = Modifier.fillMaxSize().padding(padding).padding(ScreenPadding),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                    contentPadding = PaddingValues(bottom = 32.dp)
                ) {
                    item {
                        Text(p.title, style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
                        Row(modifier = Modifier.padding(top = 8.dp), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                            if (!p.hasFeaturedImage) StatusPill("No image", PillTone.WARN) else StatusPill("Has image", PillTone.SUCCESS)
                            if (p.isThin) StatusPill("Thin (${p.wordCount}w)", PillTone.WARN) else StatusPill("${p.wordCount} words", PillTone.SUCCESS)
                            if (p.excerpt.isBlank()) StatusPill("No meta", PillTone.WARN) else StatusPill("Has meta", PillTone.SUCCESS)
                        }
                    }

                    item {
                        Card(Modifier.fillMaxWidth()) {
                            Column(Modifier.padding(14.dp)) {
                                Text("Meta description", style = MaterialTheme.typography.titleMedium)
                                Text(
                                    p.excerpt.ifBlank { "None set" },
                                    style = MaterialTheme.typography.bodyMedium,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                    modifier = Modifier.padding(top = 4.dp)
                                )
                            }
                        }
                    }

                    item {
                        Card(Modifier.fillMaxWidth(), colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)) {
                            Column(Modifier.padding(14.dp)) {
                                Text("Content preview", style = MaterialTheme.typography.titleMedium)
                                Text(
                                    Jsoup.parse(p.contentHtml).text().take(400) + if (p.contentHtml.length > 400) "..." else "",
                                    style = MaterialTheme.typography.bodyMedium,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                    modifier = Modifier.padding(top = 4.dp)
                                )
                            }
                        }
                    }

                    if (actionMessage != null) {
                        item {
                            Text(actionMessage!!, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.primary)
                        }
                    }

                    item {
                        Button(
                            onClick = {
                                actionRunning = true; actionMessage = null
                                scope.launch {
                                    val prompt = "Write a compelling 150-character max SEO meta description for this blog post titled '${p.title}'. Plain text only, no quotes."
                                    val result = aiClient.complete(creds.aiProvider, creds.aiApiKey, creds.aiModel, prompt, null, 0.4)
                                    result.fold(
                                        onSuccess = { text ->
                                            val excerpt = text.replace("\"", "").trim()
                                            if (creds.sandboxMode) {
                                                actionMessage = "🟡 Sandbox preview: \"$excerpt\""
                                            } else {
                                                api.updatePost(p.id, mapOf("excerpt" to excerpt)).fold(
                                                    onSuccess = {
                                                        post = p.copy(excerpt = excerpt)
                                                        actionMessage = "✅ Meta description updated."
                                                    },
                                                    onFailure = { actionMessage = "⚠️ ${it.message}" }
                                                )
                                            }
                                        },
                                        onFailure = { actionMessage = "⚠️ ${it.message}" }
                                    )
                                    actionRunning = false
                                }
                            },
                            enabled = !actionRunning && creds.isAiComplete,
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            if (actionRunning) CircularProgressIndicator(modifier = Modifier.padding(end = 8.dp))
                            Text(if (p.excerpt.isBlank()) "🔍 Generate meta description" else "🔍 Regenerate meta description")
                        }
                    }

                    item {
                        Button(
                            onClick = {
                                actionRunning = true; actionMessage = null
                                scope.launch {
                                    val plain = Jsoup.parse(p.contentHtml).text().take(300)
                                    val promptText = aiClient.complete(
                                        creds.aiProvider, creds.aiApiKey, creds.aiModel,
                                        "2-sentence photorealistic image prompt for a blog post titled '${p.title}', about: $plain. Raw text only.",
                                        null, 0.2
                                    ).getOrElse { actionMessage = "⚠️ ${it.message}"; actionRunning = false; return@launch }

                                    if (creds.sandboxMode) {
                                        actionMessage = "🟡 Sandbox preview — would generate & attach a featured image."
                                        actionRunning = false
                                        return@launch
                                    }

                                    val imgBytes = imageGen.generate(promptText).getOrElse {
                                        actionMessage = "⚠️ ${it.message}"; actionRunning = false; return@launch
                                    }
                                    val mediaId = api.uploadMedia(imgBytes, "${p.id}-featured.jpg", p.title).getOrElse {
                                        actionMessage = "⚠️ Upload failed: ${it.message}"; actionRunning = false; return@launch
                                    }
                                    api.updatePost(p.id, mapOf("featured_media" to mediaId)).fold(
                                        onSuccess = {
                                            post = p.copy(featuredMediaId = mediaId)
                                            actionMessage = "✅ Featured image generated and attached."
                                        },
                                        onFailure = { actionMessage = "⚠️ ${it.message}" }
                                    )
                                    actionRunning = false
                                }
                            },
                            enabled = !actionRunning && creds.isAiComplete && !p.hasFeaturedImage,
                            colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.tertiary),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text(if (p.hasFeaturedImage) "🖼️ Already has a featured image" else "🖼️ Generate featured image")
                        }
                    }
                }
            }
        }
    }
}
