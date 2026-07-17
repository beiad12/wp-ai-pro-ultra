package com.bemo21.wp.ui.theme

import android.app.Activity
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.SideEffect
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat

private val DarkColors = darkColorScheme(
    primary = BemoPurple,
    secondary = BemoPurpleDark,
    tertiary = BemoTeal,
    background = BgDark,
    surface = SurfaceDark,
    surfaceVariant = SurfaceDarkAlt,
    onBackground = TextPrimaryDark,
    onSurface = TextPrimaryDark,
    error = BemoCoral,
)

private val LightColors = lightColorScheme(
    primary = BemoPurple,
    secondary = BemoPurpleDark,
    tertiary = BemoTeal,
    background = BgLight,
    surface = SurfaceLight,
    surfaceVariant = SurfaceLightAlt,
    onBackground = TextPrimaryLight,
    onSurface = TextPrimaryLight,
    error = BemoCoral,
)

@Composable
fun Bemo21Theme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit
) {
    val colors = if (darkTheme) DarkColors else LightColors
    val view = LocalView.current
    if (!view.isInEditMode) {
        SideEffect {
            val window = (view.context as Activity).window
            window.statusBarColor = colors.background.toArgb()
            WindowCompat.getInsetsController(window, view).isAppearanceLightStatusBars = !darkTheme
        }
    }
    MaterialTheme(
        colorScheme = colors,
        typography = Bemo21Typography,
        content = content
    )
}
