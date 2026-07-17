package com.bemo21.wp.work

import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.ActivityCompat
import androidx.core.app.NotificationCompat
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.NetworkType
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import androidx.work.Constraints
import com.bemo21.wp.data.network.WordPressApi
import com.bemo21.wp.data.store.CredentialStore
import java.util.concurrent.TimeUnit

/**
 * Real, Android-sanctioned periodic background check via WorkManager — the
 * platform re-arms this on its own after a reboot (its manifest-declared
 * boot receiver ships inside the work-runtime library), so nothing app-side
 * needs to "auto-start" or keep a fragile always-on process alive. This is
 * the honest equivalent of "runs in the background after reboot" that
 * Android's battery/privacy model actually allows.
 */
class SiteSyncWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result {
        val store = CredentialStore(applicationContext)
        val creds = store.load()
        if (!creds.isWpComplete || !creds.backgroundSyncEnabled) return Result.success()

        val api = WordPressApi(creds)
        val outcome = api.testConnection()
        if (outcome.isFailure) {
            notifyProblem(creds.domain, outcome.exceptionOrNull()?.message ?: "Site unreachable")
        }
        return Result.success()
    }

    private fun notifyProblem(domain: String, message: String) {
        val nm = applicationContext.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            nm.createNotificationChannel(
                NotificationChannel(CHANNEL_ID, "Site health alerts", NotificationManager.IMPORTANCE_DEFAULT)
            )
        }
        val notification = NotificationCompat.Builder(applicationContext, CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_dialog_alert)
            .setContentTitle("Bemo21 — $domain unreachable")
            .setContentText(message)
            .setAutoCancel(true)
            .build()
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU ||
            ActivityCompat.checkSelfPermission(applicationContext, android.Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED
        ) {
            nm.notify(1001, notification)
        }
    }

    companion object {
        private const val CHANNEL_ID = "bemo21_site_health"
        private const val UNIQUE_WORK_NAME = "bemo21_site_sync"

        fun enable(context: Context) {
            val request = PeriodicWorkRequestBuilder<SiteSyncWorker>(6, TimeUnit.HOURS)
                .setConstraints(Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build())
                .build()
            WorkManager.getInstance(context)
                .enqueueUniquePeriodicWork(UNIQUE_WORK_NAME, ExistingPeriodicWorkPolicy.UPDATE, request)
        }

        fun disable(context: Context) {
            WorkManager.getInstance(context).cancelUniqueWork(UNIQUE_WORK_NAME)
        }
    }
}
