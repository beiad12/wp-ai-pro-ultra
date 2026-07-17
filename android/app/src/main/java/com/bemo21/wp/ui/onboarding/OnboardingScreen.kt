package com.bemo21.wp.ui.onboarding

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Error
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import com.bemo21.wp.data.AiProvider
import com.bemo21.wp.data.BemoCredentials
import com.bemo21.wp.data.network.WordPressApi
import com.bemo21.wp.ui.theme.BemoCoral
import com.bemo21.wp.ui.theme.BemoTeal
import kotlinx.coroutines.launch

private enum class Step { WELCOME, WORDPRESS, AI, DONE }

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun OnboardingScreen(onComplete: (BemoCredentials) -> Unit) {
    var step by remember { mutableStateOf(Step.WELCOME) }
    var domain by remember { mutableStateOf("") }
    var wpUser by remember { mutableStateOf("") }
    var wpPass by remember { mutableStateOf("") }
    var provider by remember { mutableStateOf(AiProvider.CLAUDE) }
    var aiKey by remember { mutableStateOf("") }
    var yourName by remember { mutableStateOf("") }

    var testing by remember { mutableStateOf(false) }
    var testResult by remember { mutableStateOf<Result<String>?>(null) }
    val scope = rememberCoroutineScope()

    val progress = when (step) { Step.WELCOME -> 0.1f; Step.WORDPRESS -> 0.45f; Step.AI -> 0.8f; Step.DONE -> 1f }

    Column(Modifier.fillMaxSize().padding(24.dp)) {
        LinearProgressIndicator(progress = { progress }, modifier = Modifier.fillMaxWidth())

        LazyColumn(
            modifier = Modifier.weight(1f).padding(top = 24.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
            contentPadding = PaddingValues(bottom = 16.dp)
        ) {
            when (step) {
                Step.WELCOME -> item {
                    Text("⚡", style = MaterialTheme.typography.headlineMedium)
                    Text("Meet Bemo21", style = MaterialTheme.typography.headlineMedium, modifier = Modifier.padding(top = 8.dp))
                    Text(
                        "Your AI WordPress assistant, right on your phone. I'll connect straight to your site and your AI provider — no computer needed.",
                        style = MaterialTheme.typography.bodyLarge, modifier = Modifier.padding(top = 8.dp)
                    )
                    OutlinedTextField(
                        value = yourName, onValueChange = { yourName = it },
                        label = { Text("Your name (optional)") },
                        modifier = Modifier.fillMaxWidth().padding(top = 16.dp)
                    )
                }

                Step.WORDPRESS -> item {
                    Text("Connect your WordPress site", style = MaterialTheme.typography.titleLarge)
                    Text(
                        "Use an Application Password, not your real password — generate one at WP Admin → Users → Profile → Application Passwords.",
                        style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.padding(top = 4.dp, bottom = 8.dp)
                    )
                    OutlinedTextField(
                        value = domain, onValueChange = { domain = it; testResult = null },
                        label = { Text("Site domain") }, placeholder = { Text("yourdomain.com") },
                        modifier = Modifier.fillMaxWidth()
                    )
                    OutlinedTextField(
                        value = wpUser, onValueChange = { wpUser = it; testResult = null },
                        label = { Text("WordPress username") }, modifier = Modifier.fillMaxWidth()
                    )
                    OutlinedTextField(
                        value = wpPass, onValueChange = { wpPass = it; testResult = null },
                        label = { Text("Application Password") },
                        visualTransformation = PasswordVisualTransformation(),
                        modifier = Modifier.fillMaxWidth()
                    )
                    Button(
                        onClick = {
                            testing = true; testResult = null
                            scope.launch {
                                val api = WordPressApi(BemoCredentials(domain = domain, wpUsername = wpUser, wpAppPassword = wpPass))
                                testResult = api.testConnection()
                                testing = false
                            }
                        },
                        enabled = domain.isNotBlank() && wpUser.isNotBlank() && wpPass.isNotBlank() && !testing,
                        modifier = Modifier.fillMaxWidth().padding(top = 8.dp)
                    ) {
                        if (testing) CircularProgressIndicator(modifier = Modifier.size(18.dp), color = Color.White)
                        else Text("Test connection")
                    }
                    testResult?.let { res ->
                        ConnectionResultRow(res)
                    }
                }

                Step.AI -> item {
                    Text("Connect your AI provider", style = MaterialTheme.typography.titleLarge)
                    Text(
                        "Bemo21 uses your own API key, sent directly from your phone to the provider — never through anyone else's server.",
                        style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.padding(top = 4.dp, bottom = 8.dp)
                    )
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        AiProvider.entries.forEach { p ->
                            FilterChip(
                                selected = provider == p,
                                onClick = { provider = p },
                                label = { Text(p.label) },
                                colors = FilterChipDefaults.filterChipColors(selectedContainerColor = MaterialTheme.colorScheme.primary)
                            )
                        }
                    }
                    OutlinedTextField(
                        value = aiKey, onValueChange = { aiKey = it },
                        label = { Text("${provider.label} API key") },
                        visualTransformation = PasswordVisualTransformation(),
                        modifier = Modifier.fillMaxWidth().padding(top = 12.dp)
                    )
                }

                Step.DONE -> item {
                    Icon(Icons.Filled.CheckCircle, contentDescription = null, tint = BemoTeal, modifier = Modifier.size(48.dp))
                    Text("You're all set!", style = MaterialTheme.typography.headlineMedium, modifier = Modifier.padding(top = 8.dp))
                    Text(
                        "Bemo21 is connected to $domain. Head to the dashboard to run your first check, or open Chat to just tell me what you need.",
                        style = MaterialTheme.typography.bodyLarge, modifier = Modifier.padding(top = 8.dp)
                    )
                }
            }
        }

        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            if (step != Step.WELCOME) {
                Button(
                    onClick = {
                        step = when (step) { Step.WORDPRESS -> Step.WELCOME; Step.AI -> Step.WORDPRESS; Step.DONE -> Step.AI; else -> step }
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
                    modifier = Modifier.weight(1f)
                ) { Text("Back") }
            }
            Button(
                onClick = {
                    when (step) {
                        Step.WELCOME -> step = Step.WORDPRESS
                        Step.WORDPRESS -> step = Step.AI
                        Step.AI -> step = Step.DONE
                        Step.DONE -> onComplete(
                            BemoCredentials(
                                domain = domain, wpUsername = wpUser, wpAppPassword = wpPass,
                                aiProvider = provider, aiModel = provider.defaultModel, aiApiKey = aiKey,
                                yourName = yourName, sandboxMode = true
                            )
                        )
                    }
                },
                enabled = when (step) {
                    Step.WELCOME -> true
                    Step.WORDPRESS -> testResult?.isSuccess == true
                    Step.AI -> aiKey.isNotBlank()
                    Step.DONE -> true
                },
                modifier = Modifier.weight(1f)
            ) {
                Text(if (step == Step.DONE) "Start using Bemo21" else "Continue")
            }
        }
    }
}

@Composable
private fun ConnectionResultRow(result: Result<String>) {
    Row(modifier = Modifier.padding(top = 8.dp)) {
        result.fold(
            onSuccess = { name ->
                Icon(Icons.Filled.CheckCircle, contentDescription = null, tint = BemoTeal)
                Text("  Connected as $name", color = BemoTeal, style = MaterialTheme.typography.bodyMedium)
            },
            onFailure = { err ->
                Icon(Icons.Filled.Error, contentDescription = null, tint = BemoCoral)
                Text("  ${err.message}", color = BemoCoral, style = MaterialTheme.typography.bodyMedium)
            }
        )
    }
}
