package com.bemo21.wp.data.network

import android.util.Base64
import com.bemo21.wp.data.BemoCredentials
import com.bemo21.wp.data.WpPost
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.Credentials
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.TimeUnit

class WordPressException(message: String) : Exception(message)

/**
 * Thin, real wrapper around the WordPress REST API — the same endpoints the
 * desktop app uses (Application Passwords over Basic Auth). Every call here
 * is a genuine network round-trip to the user's own site; nothing here is
 * simulated.
 */
class WordPressApi(private val creds: BemoCredentials) {

    private val client = OkHttpClient.Builder()
        .connectTimeout(20, TimeUnit.SECONDS)
        .readTimeout(45, TimeUnit.SECONDS)
        .build()

    private val authHeader: String
        get() = Credentials.basic(creds.wpUsername, creds.wpAppPassword)

    private val jsonMedia = "application/json; charset=utf-8".toMediaType()

    suspend fun testConnection(): Result<String> = withContext(Dispatchers.IO) {
        try {
            val req = Request.Builder()
                .url("${creds.siteUrl}/wp-json/wp/v2/users/me")
                .header("Authorization", authHeader)
                .get().build()
            client.newCall(req).execute().use { resp ->
                if (!resp.isSuccessful) {
                    return@withContext Result.failure(WordPressException(friendlyHttpError(resp.code)))
                }
                val body = JSONObject(resp.body?.string() ?: "{}")
                Result.success(body.optString("name", creds.wpUsername))
            }
        } catch (e: Exception) {
            Result.failure(WordPressException(friendlyNetworkError(e)))
        }
    }

    suspend fun fetchPosts(status: String = "publish", perPage: Int = 30): Result<List<WpPost>> =
        withContext(Dispatchers.IO) {
            try {
                val url = "${creds.siteUrl}/wp-json/wp/v2/posts?status=$status&per_page=$perPage&_fields=id,title,excerpt,status,link,featured_media,content"
                val req = Request.Builder().url(url).header("Authorization", authHeader).get().build()
                client.newCall(req).execute().use { resp ->
                    if (!resp.isSuccessful) return@withContext Result.failure(WordPressException(friendlyHttpError(resp.code)))
                    val arr = JSONArray(resp.body?.string() ?: "[]")
                    val posts = (0 until arr.length()).map { i ->
                        val o = arr.getJSONObject(i)
                        val content = o.optJSONObject("content")?.optString("rendered", "") ?: ""
                        WpPost(
                            id = o.getInt("id"),
                            title = htmlDecode(o.optJSONObject("title")?.optString("rendered", "") ?: ""),
                            excerpt = htmlDecode(stripTags(o.optJSONObject("excerpt")?.optString("rendered", "") ?: "")),
                            status = o.optString("status", "publish"),
                            link = o.optString("link", ""),
                            hasFeaturedImage = o.optInt("featured_media", 0) != 0,
                            wordCount = stripTags(content).trim().split(Regex("\\s+")).filter { it.isNotBlank() }.size
                        )
                    }
                    Result.success(posts)
                }
            } catch (e: Exception) {
                Result.failure(WordPressException(friendlyNetworkError(e)))
            }
        }

    suspend fun createPost(
        title: String,
        contentHtml: String,
        status: String,
        excerpt: String = ""
    ): Result<WpPost> = withContext(Dispatchers.IO) {
        try {
            val payload = JSONObject().apply {
                put("title", title)
                put("content", contentHtml)
                put("status", status)
                if (excerpt.isNotBlank()) put("excerpt", excerpt)
            }
            val req = Request.Builder()
                .url("${creds.siteUrl}/wp-json/wp/v2/posts")
                .header("Authorization", authHeader)
                .post(payload.toString().toRequestBody(jsonMedia))
                .build()
            client.newCall(req).execute().use { resp ->
                val bodyStr = resp.body?.string() ?: "{}"
                if (!resp.isSuccessful) return@withContext Result.failure(WordPressException(friendlyHttpError(resp.code)))
                val o = JSONObject(bodyStr)
                Result.success(
                    WpPost(
                        id = o.getInt("id"),
                        title = htmlDecode(o.optJSONObject("title")?.optString("rendered", title) ?: title),
                        excerpt = excerpt,
                        status = o.optString("status", status),
                        link = o.optString("link", ""),
                        hasFeaturedImage = false,
                        wordCount = stripTags(contentHtml).trim().split(Regex("\\s+")).size
                    )
                )
            }
        } catch (e: Exception) {
            Result.failure(WordPressException(friendlyNetworkError(e)))
        }
    }

    suspend fun updatePostExcerpt(postId: Int, excerpt: String): Result<Unit> = withContext(Dispatchers.IO) {
        try {
            val payload = JSONObject().put("excerpt", excerpt)
            val req = Request.Builder()
                .url("${creds.siteUrl}/wp-json/wp/v2/posts/$postId")
                .header("Authorization", authHeader)
                .post(payload.toString().toRequestBody(jsonMedia))
                .build()
            client.newCall(req).execute().use { resp ->
                if (!resp.isSuccessful) return@withContext Result.failure(WordPressException(friendlyHttpError(resp.code)))
                Result.success(Unit)
            }
        } catch (e: Exception) {
            Result.failure(WordPressException(friendlyNetworkError(e)))
        }
    }

    private fun friendlyHttpError(code: Int): String = when (code) {
        401 -> "WordPress rejected the login — check your username and Application Password."
        403 -> "WordPress blocked this request (403) — some hosts block the REST API by default; check your security plugin."
        404 -> "Couldn't find the WordPress REST API at this domain — check the site address."
        else -> "WordPress returned an error (HTTP $code)."
    }

    private fun friendlyNetworkError(e: Exception): String =
        "Couldn't reach the site: ${e.message ?: e.javaClass.simpleName}"

    private fun stripTags(html: String): String = html.replace(Regex("<[^>]*>"), " ")
    private fun htmlDecode(s: String): String = s
        .replace("&#8217;", "'").replace("&#8220;", "\"").replace("&#8221;", "\"")
        .replace("&amp;", "&").replace("&nbsp;", " ").trim()
}
