package com.bemo21.wp.ui.settings

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
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import com.bemo21.wp.data.AiProvider
import com.bemo21.wp.data.BemoCredentials
import com.bemo21.wp.ui.CardSpacing
import com.bemo21.wp.ui.ScreenPadding
import com.bemo21.wp.ui.SectionHeader

@Composable
fun SettingsScreen(
    creds: BemoCredentials,
    onSave: (BemoCredentials) -> Unit,
    onDisconnect: () -> Unit
) {
    var domain by remember(creds) { mutableStateOf(creds.domain) }
    var wpUser by remember(creds) { mutableStateOf(creds.wpUsername) }
    var wpPass by remember(creds) { mutableStateOf(creds.wpAppPassword) }
    var provider by remember(creds) { mutableStateOf(creds.aiProvider) }
    var aiKey by remember(creds) { mutableStateOf(creds.aiApiKey) }
    var yourName by remember(creds) { mutableStateOf(creds.yourName) }
    var agencyName by remember(creds) { mutableStateOf(creds.agencyName) }
    var sandbox by remember(creds) { mutableStateOf(creds.sandboxMode) }
    var bgSync by remember(creds) { mutableStateOf(creds.backgroundSyncEnabled) }

    LazyColumn(
        modifier = Modifier.fillMaxSize().padding(ScreenPadding),
        verticalArrangement = Arrangement.spacedBy(CardSpacing),
        contentPadding = PaddingValues(bottom = 32.dp)
    ) {
        item {
            Text("Settings", style = MaterialTheme.typography.headlineMedium, modifier = Modifier.padding(bottom = 4.dp))
        }
        item {
            SectionHeader("WordPress site")
            OutlinedTextField(domain, { domain = it }, label = { Text("Domain") }, modifier = Modifier.fillMaxWidth())
            OutlinedTextField(wpUser, { wpUser = it }, label = { Text("Username") }, modifier = Modifier.fillMaxWidth())
            OutlinedTextField(
                wpPass, { wpPass = it }, label = { Text("Application Password") },
                visualTransformation = PasswordVisualTransformation(), modifier = Modifier.fillMaxWidth()
            )
        }

        item {
            SectionHeader("AI provider")
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                AiProvider.entries.forEach { p ->
                    FilterChip(selected = provider == p, onClick = { provider = p }, label = { Text(p.label) })
                }
            }
            OutlinedTextField(
                aiKey, { aiKey = it }, label = { Text("${provider.label} API key") },
                visualTransformation = PasswordVisualTransformation(),
                modifier = Modifier.fillMaxWidth().padding(top = 8.dp)
            )
        }

        item {
            SectionHeader("Preferences")
            OutlinedTextField(yourName, { yourName = it }, label = { Text("Your name") }, modifier = Modifier.fillMaxWidth())
            OutlinedTextField(agencyName, { agencyName = it }, label = { Text("Agency / brand name") }, modifier = Modifier.fillMaxWidth())
        }

        item {
            Card(modifier = Modifier.fillMaxWidth()) {
                Row(
                    Modifier.fillMaxWidth().padding(16.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column(Modifier.weight(1f)) {
                        Text("Sandbox mode", style = MaterialTheme.typography.titleMedium)
                        Text(
                            "Previews every change instead of writing to WordPress.",
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                    Switch(checked = sandbox, onCheckedChange = { sandbox = it })
                }
            }
        }

        item {
            Card(modifier = Modifier.fillMaxWidth()) {
                Row(
                    Modifier.fillMaxWidth().padding(16.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column(Modifier.weight(1f)) {
                        Text("Background site sync", style = MaterialTheme.typography.titleMedium)
                        Text(
                            "Bemo21 checks your site periodically, even when closed. Android reschedules this " +
                                "automatically after a reboot — no app needs to be running.",
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                    Switch(checked = bgSync, onCheckedChange = { bgSync = it })
                }
            }
        }

        item {
            Button(
                onClick = {
                    onSave(
                        creds.copy(
                            domain = domain, wpUsername = wpUser, wpAppPassword = wpPass,
                            aiProvider = provider, aiModel = provider.defaultModel, aiApiKey = aiKey,
                            yourName = yourName, agencyName = agencyName,
                            sandboxMode = sandbox, backgroundSyncEnabled = bgSync
                        )
                    )
                },
                modifier = Modifier.fillMaxWidth()
            ) { Text("Save changes") }
        }

        item {
            Button(
                onClick = onDisconnect,
                colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.errorContainer),
                modifier = Modifier.fillMaxWidth()
            ) { Text("Disconnect & reset", color = MaterialTheme.colorScheme.onErrorContainer) }
        }
    }
}
