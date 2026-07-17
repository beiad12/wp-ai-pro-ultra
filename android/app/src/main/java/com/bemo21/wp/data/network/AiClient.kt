package com.bemo21.wp.data.network

import com.bemo21.wp.data.AiProvider
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.TimeUnit

class AiException(message: String) : Exception(message)

/**
 * Direct HTTP calls to each provider's own API, exactly like the desktop
 * app's run_ai_provider — no server in between, the phone talks straight to
 * Anthropic/OpenAI/Mistral/Google using the key the user typed in Settings.
 */
class AiClient {
    private val client = OkHttpClient.Builder()
        .connectTimeout(20, TimeUnit.SECONDS)
        .readTimeout(90, TimeUnit.SECONDS)
        .build()
    private val jsonMedia = "application/json; charset=utf-8".toMediaType()

    suspend fun complete(
        provider: AiProvider,
        apiKey: String,
        model: String,
        prompt: String,
        system: String? = null,
        temperature: Double = 0.4
    ): Result<String> = withContext(Dispatchers.IO) {
        try {
            val text = when (provider) {
                AiProvider.CLAUDE -> callClaude(apiKey, model, prompt, system)
                AiProvider.OPENAI -> callOpenAiCompatible(
                    "https://api.openai.com/v1/chat/completions", apiKey, model, prompt, system, temperature
                )
                AiProvider.MISTRAL -> callOpenAiCompatible(
                    "https://api.mistral.ai/v1/chat/completions", apiKey, model, prompt, system, temperature
                )
                AiProvider.GEMINI -> callGemini(apiKey, model, prompt, system)
            }
            Result.success(text.trim())
        } catch (e: Exception) {
            Result.failure(AiException(e.message ?: "AI request failed"))
        }
    }

    private fun callClaude(apiKey: String, model: String, prompt: String, system: String?): String {
        val body = JSONObject().apply {
            put("model", model)
            put("max_tokens", 4096)
            put("messages", JSONArray().put(JSONObject().put("role", "user").put("content", prompt)))
            if (system != null) put("system", system)
        }
        val req = Request.Builder()
            .url("https://api.anthropic.com/v1/messages")
            .header("x-api-key", apiKey)
            .header("anthropic-version", "2023-06-01")
            .post(body.toString().toRequestBody(jsonMedia))
            .build()
        client.newCall(req).execute().use { resp ->
            val bodyStr = resp.body?.string() ?: "{}"
            if (!resp.isSuccessful) throw AiException(parseProviderError(bodyStr, resp.code))
            val content = JSONObject(bodyStr).getJSONArray("content")
            return content.getJSONObject(0).getString("text")
        }
    }

    private fun callOpenAiCompatible(
        url: String, apiKey: String, model: String, prompt: String, system: String?, temperature: Double
    ): String {
        val messages = JSONArray()
        if (system != null) messages.put(JSONObject().put("role", "system").put("content", system))
        messages.put(JSONObject().put("role", "user").put("content", prompt))
        val body = JSONObject().apply {
            put("model", model)
            put("messages", messages)
            put("temperature", temperature)
        }
        val req = Request.Builder()
            .url(url)
            .header("Authorization", "Bearer $apiKey")
            .post(body.toString().toRequestBody(jsonMedia))
            .build()
        client.newCall(req).execute().use { resp ->
            val bodyStr = resp.body?.string() ?: "{}"
            if (!resp.isSuccessful) throw AiException(parseProviderError(bodyStr, resp.code))
            val choices = JSONObject(bodyStr).getJSONArray("choices")
            return choices.getJSONObject(0).getJSONObject("message").getString("content")
        }
    }

    private fun callGemini(apiKey: String, model: String, prompt: String, system: String?): String {
        val fullPrompt = if (system != null) "$system\n\n$prompt" else prompt
        val body = JSONObject().apply {
            put("contents", JSONArray().put(
                JSONObject().put("parts", JSONArray().put(JSONObject().put("text", fullPrompt)))
            ))
        }
        val req = Request.Builder()
            .url("https://generativelanguage.googleapis.com/v1beta/models/$model:generateContent?key=$apiKey")
            .post(body.toString().toRequestBody(jsonMedia))
            .build()
        client.newCall(req).execute().use { resp ->
            val bodyStr = resp.body?.string() ?: "{}"
            if (!resp.isSuccessful) throw AiException(parseProviderError(bodyStr, resp.code))
            val candidates = JSONObject(bodyStr).getJSONArray("candidates")
            val parts = candidates.getJSONObject(0).getJSONObject("content").getJSONArray("parts")
            return parts.getJSONObject(0).getString("text")
        }
    }

    private fun parseProviderError(bodyStr: String, code: Int): String = try {
        val o = JSONObject(bodyStr)
        val err = o.optJSONObject("error")
        err?.optString("message")?.takeIf { it.isNotBlank() }
            ?: "AI provider returned HTTP $code"
    } catch (e: Exception) {
        "AI provider returned HTTP $code"
    }
}
