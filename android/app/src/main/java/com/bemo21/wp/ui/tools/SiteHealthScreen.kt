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
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.bemo21.wp.data.BemoCredentials
import com.bemo21.wp.data.HealthCheck
import com.bemo21.wp.data.network.SiteHealthChecker
import com.bemo21.wp.ui.LoadingBlock
import com.bemo21.wp.ui.ScreenPadding
import com.bemo21.wp.ui.StatusPill
import com.bemo21.wp.ui.ToolTopBar
import com.bemo21.wp.ui.toPillTone

@Composable
fun SiteHealthScreen(creds: BemoCredentials, onBack: () -> Unit) {
    var loading by remember { mutableStateOf(true) }
    var checks by remember { mutableStateOf<List<HealthCheck>>(emptyList()) }
    val checker = remember { SiteHealthChecker() }

    LaunchedEffect(creds.domain) {
        loading = true
        checks = checker.run(creds.siteUrl)
        loading = false
    }

    Scaffold(topBar = { ToolTopBar("Site health", onBack) }) { padding ->
        if (loading) {
            Column(Modifier.padding(padding)) { LoadingBlock("Checking ${creds.domain}...") }
        } else {
            val passCount = checks.count { it.status == com.bemo21.wp.data.CheckStatus.PASS }
            LazyColumn(
                modifier = Modifier.fillMaxSize().padding(padding).padding(ScreenPadding),
                verticalArrangement = Arrangement.spacedBy(10.dp),
                contentPadding = PaddingValues(bottom = 32.dp)
            ) {
                item {
                    Text(
                        "$passCount of ${checks.size} checks passed",
                        style = MaterialTheme.typography.titleLarge
                    )
                }
                items(checks, key = { it.id }) { check ->
                    Card(Modifier.fillMaxWidth()) {
                        Row(
                            Modifier.fillMaxWidth().padding(14.dp),
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Column(Modifier.weight(1f)) {
                                Text(check.label, style = MaterialTheme.typography.titleMedium)
                                Text(
                                    check.detail, style = MaterialTheme.typography.bodyMedium,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                    modifier = Modifier.padding(top = 2.dp)
                                )
                            }
                            StatusPill(check.status.name, check.status.toPillTone())
                        }
                    }
                }
            }
        }
    }
}
