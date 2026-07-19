package com.bemo21.wp.ui.posts

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
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.Card
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
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
import com.bemo21.wp.ui.LoadingBlock
import com.bemo21.wp.ui.PillTone
import com.bemo21.wp.ui.ScreenPadding
import com.bemo21.wp.ui.StatusPill
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PostsScreen(creds: BemoCredentials, onOpenPost: (Int) -> Unit) {
    var status by remember { mutableStateOf("publish") }
    var query by remember { mutableStateOf("") }
    var loading by remember { mutableStateOf(true) }
    var posts by remember { mutableStateOf<List<WpPost>>(emptyList()) }
    var error by remember { mutableStateOf<String?>(null) }
    val scope = rememberCoroutineScope()
    val api = remember(creds) { WordPressApi(creds) }

    suspend fun load() {
        loading = true; error = null
        api.fetchPosts(status, 50, query.ifBlank { null }).fold(
            onSuccess = { posts = it },
            onFailure = { error = it.message }
        )
        loading = false
    }

    LaunchedEffect(status) { load() }
    LaunchedEffect(query) {
        delay(400)
        load()
    }

    Column(Modifier.fillMaxSize()) {
        Column(Modifier.padding(ScreenPadding)) {
            Text("Posts", style = MaterialTheme.typography.headlineMedium, modifier = Modifier.padding(bottom = 12.dp))
            OutlinedTextField(
                value = query,
                onValueChange = { query = it },
                placeholder = { Text("Search posts...") },
                leadingIcon = { Icon(Icons.Filled.Search, contentDescription = null) },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true
            )
            Row(modifier = Modifier.padding(top = 10.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                listOf("publish" to "Published", "draft" to "Drafts", "private" to "Private").forEach { (value, label) ->
                    FilterChip(selected = status == value, onClick = { status = value }, label = { Text(label) })
                }
            }
        }

        when {
            loading -> LoadingBlock("Loading posts...")
            error != null -> EmptyState("⚠️", error ?: "Something went wrong")
            posts.isEmpty() -> EmptyState("📭", "No ${status} posts found.")
            else -> LazyColumn(
                modifier = Modifier.fillMaxSize().padding(horizontal = ScreenPadding),
                verticalArrangement = Arrangement.spacedBy(CardSpacing),
                contentPadding = PaddingValues(bottom = 24.dp)
            ) {
                items(posts, key = { it.id }) { post -> PostRow(post, onClick = { onOpenPost(post.id) }) }
            }
        }
    }
}

@Composable
private fun PostRow(post: WpPost, onClick: () -> Unit) {
    Card(modifier = Modifier.fillMaxWidth().clickable(onClick = onClick)) {
        Column(Modifier.padding(14.dp)) {
            Text(post.title.ifBlank { "(untitled)" }, style = MaterialTheme.typography.titleMedium)
            Text(
                "${post.wordCount} words",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(top = 2.dp, bottom = 8.dp)
            )
            Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                if (!post.hasFeaturedImage) StatusPill("No image", PillTone.WARN)
                if (post.isThin) StatusPill("Thin", PillTone.WARN)
                if (post.excerpt.isBlank()) StatusPill("No meta", PillTone.WARN)
                if (post.hasFeaturedImage && !post.isThin && post.excerpt.isNotBlank()) StatusPill("Healthy", PillTone.SUCCESS)
            }
        }
    }
}
