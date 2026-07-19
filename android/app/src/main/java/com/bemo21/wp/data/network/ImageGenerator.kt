package com.bemo21.wp.data.network

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.net.URLEncoder
import java.util.concurrent.TimeUnit

class ImageGenException(message: String) : Exception(message)

/** Free, keyless AI image generation via Pollinations — same provider the desktop app defaults to. */
class ImageGenerator {
    private val client = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(60, TimeUnit.SECONDS)
        .build()

    suspend fun generate(prompt: String): Result<ByteArray> = withContext(Dispatchers.IO) {
        try {
            val encoded = URLEncoder.encode(prompt, "UTF-8").replace("+", "%20")
            val url = "https://image.pollinations.ai/prompt/$encoded?width=1024&height=683&nologo=true"
            val req = Request.Builder().url(url).get().build()
            client.newCall(req).execute().use { resp ->
                if (!resp.isSuccessful) return@withContext Result.failure(ImageGenException("Image provider returned HTTP ${resp.code}"))
                val bytes = resp.body?.bytes()
                if (bytes == null || bytes.isEmpty()) Result.failure(ImageGenException("Empty image response"))
                else Result.success(bytes)
            }
        } catch (e: Exception) {
            Result.failure(ImageGenException(e.message ?: "Image generation failed"))
        }
    }
}
