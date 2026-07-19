package com.bemo21.wp.data.network

import com.bemo21.wp.data.CheckStatus
import com.bemo21.wp.data.HealthCheck
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import org.jsoup.Jsoup
import java.security.cert.X509Certificate
import java.util.concurrent.TimeUnit

/**
 * Real technical checks against the live homepage — the same category of
 * checks as the desktop app's Technical tab, run directly from the phone
 * via a genuine HTTPS request. No result here is guessed or simulated.
 */
class SiteHealthChecker {
    private val client = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(20, TimeUnit.SECONDS)
        .followRedirects(true)
        .build()

    suspend fun run(siteUrl: String): List<HealthCheck> = withContext(Dispatchers.IO) {
        val checks = mutableListOf<HealthCheck>()
        val start = System.currentTimeMillis()

        val req = Request.Builder().url(siteUrl).header("User-Agent", "Bemo21/1.0 (+wordpress-health-check)").get().build()
        try {
            client.newCall(req).execute().use { resp ->
                val elapsedMs = System.currentTimeMillis() - start
                val body = resp.body?.bytes() ?: ByteArray(0)
                val html = String(body)
                val sizeKb = body.size / 1024.0

                checks += HealthCheck(
                    "response_time", "Response time",
                    if (elapsedMs < 800) CheckStatus.PASS else if (elapsedMs < 2000) CheckStatus.WARN else CheckStatus.FAIL,
                    "${elapsedMs}ms"
                )
                checks += HealthCheck(
                    "page_weight", "Page weight",
                    if (sizeKb < 1500) CheckStatus.PASS else if (sizeKb < 3000) CheckStatus.WARN else CheckStatus.FAIL,
                    "${"%.0f".format(sizeKb)} KB"
                )

                val encoding = resp.header("Content-Encoding")
                checks += HealthCheck(
                    "compression", "GZIP / Brotli compression",
                    if (encoding == "gzip" || encoding == "br") CheckStatus.PASS else CheckStatus.WARN,
                    encoding ?: "not compressed"
                )

                checks += sslCheck(resp)

                val doc = try { Jsoup.parse(html, siteUrl) } catch (e: Exception) { null }
                if (doc != null) {
                    val title = doc.title()
                    checks += HealthCheck(
                        "title_tag", "Title tag",
                        when { title.isBlank() -> CheckStatus.FAIL; title.length in 10..60 -> CheckStatus.PASS; else -> CheckStatus.WARN },
                        if (title.isBlank()) "Missing" else "${title.length} chars: \"${title.take(60)}\""
                    )

                    val metaDesc = doc.select("meta[name=description]").attr("content")
                    checks += HealthCheck(
                        "meta_description", "Meta description",
                        when { metaDesc.isBlank() -> CheckStatus.FAIL; metaDesc.length in 50..160 -> CheckStatus.PASS; else -> CheckStatus.WARN },
                        if (metaDesc.isBlank()) "Missing" else "${metaDesc.length} chars"
                    )

                    val viewport = doc.select("meta[name=viewport]").isNotEmpty()
                    checks += HealthCheck(
                        "viewport", "Mobile viewport tag",
                        if (viewport) CheckStatus.PASS else CheckStatus.FAIL,
                        if (viewport) "Present" else "Missing — site may not be mobile-friendly"
                    )

                    val h1Count = doc.select("h1").size
                    checks += HealthCheck(
                        "h1_count", "Single H1 usage",
                        when (h1Count) { 1 -> CheckStatus.PASS; 0 -> CheckStatus.FAIL; else -> CheckStatus.WARN },
                        "$h1Count H1 tag(s) found"
                    )

                    val imgs = doc.select("img")
                    val imgsNoAlt = imgs.count { it.attr("alt").isBlank() }
                    checks += HealthCheck(
                        "image_alt", "Homepage image alt text",
                        if (imgs.isEmpty() || imgsNoAlt == 0) CheckStatus.PASS else CheckStatus.WARN,
                        if (imgs.isEmpty()) "No images found" else "$imgsNoAlt of ${imgs.size} image(s) missing alt text"
                    )
                }

                checks += headExists("$siteUrl/robots.txt", "robots_txt", "robots.txt")
                checks += headExists("$siteUrl/sitemap.xml", "sitemap_xml", "XML sitemap")
            }
        } catch (e: Exception) {
            checks += HealthCheck("connection", "Connection", CheckStatus.FAIL, e.message ?: "Couldn't reach the site")
        }
        checks
    }

    private fun sslCheck(resp: okhttp3.Response): HealthCheck {
        val handshake = resp.handshake ?: return HealthCheck("ssl", "SSL certificate", CheckStatus.WARN, "Site is not served over HTTPS")
        val leaf = handshake.peerCertificates.firstOrNull() as? X509Certificate
            ?: return HealthCheck("ssl", "SSL certificate", CheckStatus.WARN, "Couldn't read certificate")
        val daysLeft = (leaf.notAfter.time - System.currentTimeMillis()) / (1000 * 60 * 60 * 24)
        return HealthCheck(
            "ssl", "SSL certificate",
            if (daysLeft > 14) CheckStatus.PASS else if (daysLeft > 0) CheckStatus.WARN else CheckStatus.FAIL,
            if (daysLeft > 0) "Valid, expires in $daysLeft day(s)" else "Expired"
        )
    }

    private fun headExists(url: String, id: String, label: String): HealthCheck = try {
        val req = Request.Builder().url(url).head().build()
        client.newCall(req).execute().use { resp ->
            HealthCheck(id, label, if (resp.isSuccessful) CheckStatus.PASS else CheckStatus.WARN,
                if (resp.isSuccessful) "Found" else "Not found (HTTP ${resp.code})")
        }
    } catch (e: Exception) {
        HealthCheck(id, label, CheckStatus.WARN, "Couldn't check: ${e.message}")
    }
}
