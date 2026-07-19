package com.bemo21.wp.ui.tools

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.bemo21.wp.ui.CardSpacing
import com.bemo21.wp.ui.Overlay
import com.bemo21.wp.ui.ScreenPadding
import com.bemo21.wp.ui.SectionHeader
import com.bemo21.wp.ui.ToolCard

@Composable
fun ToolsScreen(onOpen: (Overlay) -> Unit) {
    LazyColumn(
        modifier = Modifier.fillMaxSize().padding(ScreenPadding),
        verticalArrangement = Arrangement.spacedBy(CardSpacing),
        contentPadding = PaddingValues(bottom = 32.dp)
    ) {
        item { SectionHeader("Pro tools", "Real actions against your live site") }
        item {
            ToolCard(
                icon = "✨", title = "Create post",
                subtitle = "Write and publish a new AI post with SEO meta",
                onClick = { onOpen(Overlay.CreatePost) }
            )
        }
        item {
            ToolCard(
                icon = "🔍", title = "SEO batch fix",
                subtitle = "Generate meta descriptions for every post missing one",
                onClick = { onOpen(Overlay.SeoBatch) }
            )
        }
        item {
            ToolCard(
                icon = "🖼️", title = "Fix missing images",
                subtitle = "Generate & attach featured images across your site",
                onClick = { onOpen(Overlay.FixImages) }
            )
        }
        item {
            ToolCard(
                icon = "🩺", title = "Site health check",
                subtitle = "SSL, speed, meta tags, mobile, robots.txt & sitemap",
                onClick = { onOpen(Overlay.SiteHealth) }
            )
        }
    }
}
