package com.bemo21.wp.data

enum class AiProvider(val label: String, val defaultModel: String) {
    CLAUDE("Claude", "claude-sonnet-4-20250514"),
    OPENAI("OpenAI", "gpt-4o"),
    MISTRAL("Mistral", "mistral-large-latest"),
    GEMINI("Gemini", "gemini-1.5-flash");

    companion object {
        fun fromLabel(label: String): AiProvider = entries.firstOrNull { it.label == label } ?: CLAUDE
    }
}

data class BemoCredentials(
    val domain: String = "",
    val wpUsername: String = "",
    val wpAppPassword: String = "",
    val aiProvider: AiProvider = AiProvider.CLAUDE,
    val aiModel: String = AiProvider.CLAUDE.defaultModel,
    val aiApiKey: String = "",
    val agencyName: String = "",
    val yourName: String = "",
    val sandboxMode: Boolean = true,
    val backgroundSyncEnabled: Boolean = false
) {
    val isWpComplete: Boolean get() = domain.isNotBlank() && wpUsername.isNotBlank() && wpAppPassword.isNotBlank()
    val isAiComplete: Boolean get() = aiApiKey.isNotBlank()
    val siteUrl: String get() = "https://${domain.trim().removePrefix("https://").removePrefix("http://").trimEnd('/')}"
}

data class WpPost(
    val id: Int,
    val title: String,
    val excerpt: String,
    val contentHtml: String,
    val status: String,
    val link: String,
    val featuredMediaId: Int,
    val wordCount: Int,
    val modified: String
) {
    val hasFeaturedImage: Boolean get() = featuredMediaId != 0
    val isThin: Boolean get() = wordCount < 200
}

enum class CheckStatus { PASS, WARN, FAIL }

data class HealthCheck(
    val id: String,
    val label: String,
    val status: CheckStatus,
    val detail: String
)
