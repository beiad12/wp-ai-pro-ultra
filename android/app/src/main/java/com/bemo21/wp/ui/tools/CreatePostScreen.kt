package com.bemo21.wp.ui.tools

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.bemo21.wp.data.BemoCredentials
import com.bemo21.wp.data.network.AiClient
import com.bemo21.wp.data.network.WordPressApi
import com.bemo21.wp.ui.ScreenPadding
import com.bemo21.wp.ui.ToolTopBar
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CreatePostScreen(creds: BemoCredentials, onBack: () -> Unit) {
    var topic by remember { mutableStateOf("") }
    var wordCount by remember { mutableIntStateOf(700) }
    var publishNow by remember { mutableStateOf(false) }
    var running by remember { mutableStateOf(false) }
    var resultMessage by remember { mutableStateOf<String?>(null) }
    var resultOk by remember { mutableStateOf(true) }
    val scope = rememberCoroutineScope()
    val api = remember(creds) { WordPressApi(creds) }
    val aiClient = remember { AiClient() }

    Scaffold(topBar = { ToolTopBar("Create post", onBack) }) { padding ->
        LazyColumn(
            modifier = Modifier.fillMaxSize().padding(padding).padding(ScreenPadding),
            verticalArrangement = Arrangement.spacedBy(14.dp),
            contentPadding = PaddingValues(bottom = 32.dp)
        ) {
            item {
                Text("What's the post about?", style = MaterialTheme.typography.titleMedium)
                OutlinedTextField(
                    value = topic, onValueChange = { topic = it },
                    placeholder = { Text("e.g. Home coffee brewing for beginners") },
                    modifier = Modifier.fillMaxWidth().padding(top = 6.dp)
                )
            }
            item {
                Text("Target length: $wordCount words", style = MaterialTheme.typography.titleMedium)
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.padding(top = 6.dp)) {
                    listOf(400, 700, 1200, 1800).forEach { wc ->
                        FilterChip(selected = wordCount == wc, onClick = { wordCount = wc }, label = { Text("$wc") })
                    }
                }
            }
            item {
                Row(
                    Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column {
                        Text("Publish immediately", style = MaterialTheme.typography.titleMedium)
                        Text(
                            if (publishNow) "Goes live as soon as it's created" else "Saved as a draft for you to review",
                            style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                    Switch(checked = publishNow, onCheckedChange = { publishNow = it })
                }
            }
            if (creds.sandboxMode) {
                item {
                    Text(
                        "🟡 Sandbox mode is on — this will preview the post without publishing it. Turn it off in Settings to go live.",
                        style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.primary
                    )
                }
            }
            resultMessage?.let { msg ->
                item {
                    Text(msg, color = if (resultOk) MaterialTheme.colorScheme.tertiary else MaterialTheme.colorScheme.error)
                }
            }
            item {
                Button(
                    onClick = {
                        running = true; resultMessage = null
                        scope.launch {
                            val sys = "You are an expert SEO content writer and WordPress editor. Write well-structured HTML " +
                                "using h2, h3, p, ul, strong tags. No html/head/body/title tags. No markdown fences. Raw HTML only."
                            val prompt = "Blog post about: $topic\n~$wordCount words. Include an intro, subheadings, practical tips, and a closing CTA.\nReturn HTML body only."
                            val htmlResult = aiClient.complete(creds.aiProvider, creds.aiApiKey, creds.aiModel, prompt, sys, 0.6)
                            val html = htmlResult.getOrElse {
                                resultOk = false; resultMessage = "Couldn't write the post: ${it.message}"; running = false; return@launch
                            }.replace("```html", "").replace("```", "").trim()

                            val excerptPrompt = "Write a compelling 150-character max SEO meta description for a blog post about: $topic. Plain text only, no quotes."
                            val excerpt = aiClient.complete(creds.aiProvider, creds.aiApiKey, creds.aiModel, excerptPrompt, null, 0.4)
                                .getOrDefault("").replace("\"", "").trim()

                            if (creds.sandboxMode) {
                                resultOk = true
                                resultMessage = "🟡 Preview — \"$topic\" (~$wordCount words) would be ${if (publishNow) "published" else "saved as a draft"}. Meta: $excerpt"
                                running = false
                                return@launch
                            }

                            api.createPost(topic, html, if (publishNow) "publish" else "draft", excerpt).fold(
                                onSuccess = { post ->
                                    resultOk = true
                                    resultMessage = "✅ Created \"${post.title}\" — ${post.link}"
                                    topic = ""
                                },
                                onFailure = { resultOk = false; resultMessage = "⚠️ ${it.message}" }
                            )
                            running = false
                        }
                    },
                    enabled = !running && topic.isNotBlank() && creds.isAiComplete,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    if (running) {
                        CircularProgressIndicator(modifier = Modifier.padding(end = 8.dp))
                        Text("Writing...")
                    } else {
                        Text(if (publishNow) "✨ Write & publish" else "✨ Write & save draft")
                    }
                }
            }
        }
    }
}
