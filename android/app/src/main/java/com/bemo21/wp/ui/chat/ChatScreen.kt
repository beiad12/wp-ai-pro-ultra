package com.bemo21.wp.ui.chat

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilledIconButton
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.bemo21.wp.data.AgentStep
import com.bemo21.wp.data.AgentTools
import com.bemo21.wp.data.BemoCredentials
import com.bemo21.wp.data.ChatMessage
import com.bemo21.wp.data.ChatRole
import com.bemo21.wp.data.network.AiClient
import com.bemo21.wp.data.network.WordPressApi
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ChatScreen(creds: BemoCredentials) {
    val messages = remember { mutableStateListOf<ChatMessage>() }
    var input by remember { mutableStateOf("") }
    var pendingPlan by remember { mutableStateOf<List<AgentStep>>(emptyList()) }
    val checkedSteps = remember { mutableStateListOf<Boolean>() }
    var thinking by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()
    val listState = rememberLazyListState()
    val aiClient = remember { AiClient() }
    val wpApi = remember(creds) { WordPressApi(creds) }

    LaunchedEffect(Unit) {
        if (messages.isEmpty()) {
            val name = creds.yourName.ifBlank { creds.wpUsername }
            messages.add(
                ChatMessage(
                    ChatRole.ASSISTANT,
                    "Hey ${name.ifBlank { "there" }}! I'm Bemo21. Tell me what you need — " +
                        "\"list my recent posts\", \"write a post about home coffee brewing\", " +
                        "or \"fix my missing meta descriptions\"."
                )
            )
        }
    }

    LaunchedEffect(messages.size) {
        if (messages.isNotEmpty()) listState.animateScrollToItem(messages.size - 1)
    }

    fun send() {
        val text = input.trim()
        if (text.isEmpty() || thinking) return
        messages.add(ChatMessage(ChatRole.USER, text))
        input = ""
        thinking = true
        scope.launch {
            val contextSummary = "Connected to ${creds.domain}, sandbox=${if (creds.sandboxMode) "on" else "off"}."
            val (reply, steps) = AgentTools.plan(aiClient, creds, text, contextSummary)
            messages.add(ChatMessage(ChatRole.ASSISTANT, reply, plan = steps.ifEmpty { null }))
            pendingPlan = steps
            checkedSteps.clear()
            steps.forEach { checkedSteps.add(true) }
            thinking = false
        }
    }

    fun runPlan() {
        val steps = pendingPlan.filterIndexed { i, _ -> checkedSteps.getOrElse(i) { true } }
        pendingPlan = emptyList()
        if (steps.isEmpty()) return
        thinking = true
        scope.launch {
            for (step in steps) {
                val result = AgentTools.execute(step, creds, wpApi, aiClient, creds.sandboxMode)
                messages.add(ChatMessage(ChatRole.ASSISTANT, (if (result.ok) "✅ " else "⚠️ ") + result.message))
            }
            thinking = false
        }
    }

    Column(Modifier.fillMaxSize()) {
        LazyColumn(
            state = listState,
            modifier = Modifier.weight(1f).padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
            contentPadding = PaddingValues(vertical = 16.dp)
        ) {
            items(messages) { msg -> ChatBubble(msg) }
            if (thinking) {
                item {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        CircularProgressIndicator(modifier = Modifier.size(16.dp), strokeWidth = 2.dp)
                        Text("  Bemo21 is working...", style = MaterialTheme.typography.bodyMedium, modifier = Modifier.padding(start = 6.dp))
                    }
                }
            }
            if (pendingPlan.isNotEmpty()) {
                item { PlanConfirmCard(pendingPlan, checkedSteps, onRun = { runPlan() }, onDiscard = { pendingPlan = emptyList() }) }
            }
        }

        Row(
            modifier = Modifier.fillMaxWidth().imePadding().padding(12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            OutlinedTextField(
                value = input,
                onValueChange = { input = it },
                modifier = Modifier.weight(1f),
                placeholder = { Text("Ask Bemo21 anything...") },
                shape = RoundedCornerShape(20.dp)
            )
            FilledIconButton(onClick = { send() }, enabled = input.isNotBlank() && !thinking, modifier = Modifier.padding(start = 8.dp)) {
                Icon(Icons.AutoMirrored.Filled.Send, contentDescription = "Send")
            }
        }
    }
}

@Composable
private fun ChatBubble(msg: ChatMessage) {
    val isUser = msg.role == ChatRole.USER
    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = if (isUser) Arrangement.End else Arrangement.Start) {
        Card(
            colors = CardDefaults.cardColors(
                containerColor = if (isUser) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.surfaceVariant
            ),
            shape = RoundedCornerShape(16.dp),
            modifier = Modifier.padding(start = if (isUser) 40.dp else 0.dp, end = if (isUser) 0.dp else 40.dp)
        ) {
            Text(
                msg.text,
                modifier = Modifier.padding(12.dp),
                color = if (isUser) MaterialTheme.colorScheme.onPrimary else MaterialTheme.colorScheme.onSurfaceVariant,
                style = MaterialTheme.typography.bodyLarge
            )
        }
    }
}

@Composable
private fun PlanConfirmCard(
    steps: List<AgentStep>,
    checked: androidx.compose.runtime.snapshots.SnapshotStateList<Boolean>,
    onRun: () -> Unit,
    onDiscard: () -> Unit
) {
    Card(modifier = Modifier.fillMaxWidth(), colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)) {
        Column(Modifier.padding(14.dp)) {
            Text("Proposed steps — review before I run anything", style = MaterialTheme.typography.titleMedium)
            steps.forEachIndexed { i, step ->
                Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.padding(top = 6.dp)) {
                    Checkbox(
                        checked = checked.getOrElse(i) { true },
                        onCheckedChange = { v -> if (i < checked.size) checked[i] = v }
                    )
                    Column {
                        Text(step.tool, style = MaterialTheme.typography.titleMedium)
                        if (step.why.isNotBlank()) {
                            Text(step.why, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                    }
                }
            }
            Row(modifier = Modifier.padding(top = 10.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                TextButton(onClick = onDiscard) { Text("Discard") }
                Box(modifier = Modifier.weight(1f))
                androidx.compose.material3.Button(onClick = onRun) { Text("Run selected") }
            }
        }
    }
}
