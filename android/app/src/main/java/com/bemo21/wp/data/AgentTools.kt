package com.bemo21.wp.data

import com.bemo21.wp.data.network.AiClient
import com.bemo21.wp.data.network.WordPressApi
import org.json.JSONObject

data class ToolSpec(val name: String, val desc: String)

/**
 * The fixed, whitelisted list of real actions Bemo21's chat may propose.
 * The AI plans against this exact list and nothing else — it never writes
 * or runs arbitrary code, and every step here is a genuine WordPress REST
 * API call, gated behind user confirmation and Sandbox mode.
 */
object AgentTools {
    val registry = listOf(
        ToolSpec("list_posts", "List posts from WordPress. Args: status ('publish'/'draft', default 'publish'), max_count (int, default 10)."),
        ToolSpec("create_post", "Write and publish one new AI-generated blog post with an SEO excerpt. Args: topic (string, required), word_count (int, default 700), publish (bool, default false — false saves as a draft for review)."),
        ToolSpec("fix_seo_meta", "Generate and push a short SEO excerpt/meta description for posts that don't have one yet. Args: max_count (int, default 5)."),
    )

    private fun toolsDescription(): String = registry.joinToString("\n") { "- ${it.name}: ${it.desc}" }

    suspend fun plan(
        aiClient: AiClient,
        creds: BemoCredentials,
        userRequest: String,
        contextSummary: String
    ): Pair<String, List<AgentStep>> {
        val system = """
            You are the planning brain for a WordPress assistant called Bemo21. You never write or run code
            yourself — you only choose from this fixed list of whitelisted tools and respond with strict JSON,
            nothing else, no markdown fences, no commentary outside the JSON.

            Available tools:
            ${toolsDescription()}

            Respond with exactly this JSON shape:
            {"reply": "one short friendly sentence about the plan", "steps": [{"tool": "<tool name>", "args": {}, "why": "short reason"}]}

            Rules: use only tool names from the list above, at most 4 steps, only include args the tool actually
            accepts, all arg values must be strings. If the request doesn't match any tool, return an empty
            steps list and explain why in reply.
        """.trimIndent()
        val prompt = "Site context: $contextSummary\n\nUser request: $userRequest"

        val result = aiClient.complete(creds.aiProvider, creds.aiApiKey, creds.aiModel, prompt, system, 0.2)
        val raw = result.getOrElse { return "I couldn't reach the AI provider to plan that: ${it.message}" to emptyList() }

        val cleaned = raw.trim().removeSurrounding("```json", "```").removeSurrounding("```", "```").trim()
        return try {
            val obj = JSONObject(cleaned)
            val reply = obj.optString("reply", "Here's what I'd do:")
            val stepsArr = obj.optJSONArray("steps")
            val validNames = registry.map { it.name }.toSet()
            val steps = mutableListOf<AgentStep>()
            if (stepsArr != null) {
                for (i in 0 until minOf(stepsArr.length(), 4)) {
                    val s = stepsArr.getJSONObject(i)
                    val tool = s.optString("tool")
                    if (tool !in validNames) continue
                    val argsObj = s.optJSONObject("args") ?: JSONObject()
                    val args = mutableMapOf<String, String>()
                    argsObj.keys().forEach { k -> args[k] = argsObj.get(k).toString() }
                    steps.add(AgentStep(tool, args, s.optString("why", "")))
                }
            }
            reply to steps
        } catch (e: Exception) {
            "I couldn't build a clear plan from that — try rephrasing." to emptyList()
        }
    }

    suspend fun execute(
        step: AgentStep,
        creds: BemoCredentials,
        wpApi: WordPressApi,
        aiClient: AiClient,
        isDryRun: Boolean
    ): ToolResult {
        return when (step.tool) {
        "list_posts" -> {
            val status = step.args["status"]?.takeIf { it in setOf("publish", "draft", "private") } ?: "publish"
            val maxCount = step.args["max_count"]?.toIntOrNull() ?: 10
            wpApi.fetchPosts(status, maxCount).fold(
                onSuccess = { posts ->
                    if (posts.isEmpty()) ToolResult(true, "No $status posts found.")
                    else ToolResult(true, "Found ${posts.size} $status post(s):\n" +
                        posts.take(maxCount).joinToString("\n") { "• ${it.title} (#${it.id}, ${it.wordCount}w)" })
                },
                onFailure = { ToolResult(false, it.message ?: "Couldn't load posts.") }
            )
        }

        "create_post" -> {
            val topic = step.args["topic"]?.trim().orEmpty()
            if (topic.isEmpty()) return ToolResult(false, "I need a topic to write about.")
            val wordCount = step.args["word_count"]?.toIntOrNull() ?: 700
            val publish = step.args["publish"]?.toBooleanStrictOrNull() ?: false
            if (isDryRun) {
                return ToolResult(true, "🟡 Sandbox preview — would create '$topic' (~$wordCount words, ${if (publish) "published" else "draft"}).")
            }
            val sys = "You are an expert SEO content writer and WordPress editor. Write well-structured HTML " +
                "using h2, h3, p, ul, strong tags. No html/head/body/title tags. No markdown fences. Raw HTML only."
            val prompt = "Blog post about: $topic\n~$wordCount words. Include an intro, subheadings, practical tips, and a closing CTA.\nReturn HTML body only."
            val htmlResult = aiClient.complete(creds.aiProvider, creds.aiApiKey, creds.aiModel, prompt, sys, 0.6)
            val html = htmlResult.getOrElse { return ToolResult(false, "Couldn't write the post: ${it.message}") }
                .replace("```html", "").replace("```", "").trim()

            val excerptPrompt = "Write a compelling 150-character max SEO meta description for a blog post about: $topic. Plain text only, no quotes."
            val excerpt = aiClient.complete(creds.aiProvider, creds.aiApiKey, creds.aiModel, excerptPrompt, null, 0.4)
                .getOrDefault("").replace("\"", "").trim()

            wpApi.createPost(topic, html, if (publish) "publish" else "draft", excerpt).fold(
                onSuccess = { post -> ToolResult(true, "Created post #${post.id} — ${post.link} ✅") },
                onFailure = { ToolResult(false, "Couldn't create the post: ${it.message}") }
            )
        }

        "fix_seo_meta" -> {
            val maxCount = step.args["max_count"]?.toIntOrNull() ?: 5
            val postsResult = wpApi.fetchPosts("publish", 50)
            val posts = postsResult.getOrElse { return ToolResult(false, it.message ?: "Couldn't load posts.") }
            val targets = posts.filter { it.excerpt.isBlank() }.take(maxCount)
            if (targets.isEmpty()) return ToolResult(true, "Every loaded post already has a meta description.")
            if (isDryRun) return ToolResult(true, "🟡 Sandbox preview — ${targets.size} post(s) would get a new meta description.")
            var okCount = 0
            for (post in targets) {
                val prompt = "Write a compelling 150-character max SEO meta description for this blog post titled '${post.title}'. Plain text only, no quotes."
                val excerpt = aiClient.complete(creds.aiProvider, creds.aiApiKey, creds.aiModel, prompt, null, 0.4)
                    .getOrNull()?.replace("\"", "")?.trim() ?: continue
                if (excerpt.isBlank()) continue
                if (wpApi.updatePostExcerpt(post.id, excerpt).isSuccess) okCount++
            }
            ToolResult(true, "Wrote meta descriptions for $okCount of ${targets.size} post(s). ✅")
        }

        else -> ToolResult(false, "Unknown tool: ${step.tool}")
        }
    }
}
