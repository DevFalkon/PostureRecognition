import sys
from PySide6.QtCore import Qt, QObject, Signal
from PySide6.QtGui import QGuiApplication, QPalette


class ThemeManager(QObject):
    theme_changed = Signal(bool)  # Emits True for dark mode, False for light mode

    def __init__(self):
        super().__init__()
        # Connect to system theme change notifications if available
        hints = QGuiApplication.styleHints()
        if hasattr(hints, "colorSchemeChanged"):
            hints.colorSchemeChanged.connect(self._on_system_theme_changed)

    def is_dark_mode(self) -> bool:
        """Detects if the application or system is in dark mode."""
        app = QGuiApplication.instance()
        if not app:
            return False

        # Method 1: Check Qt6 styleHints (Qt 6.5+)
        hints = app.styleHints()
        if hasattr(hints, "colorScheme"):
            return hints.colorScheme() == Qt.ColorScheme.Dark

        # Method 2: Fallback — inspect window background brightness from palette
        bg_color = app.palette().color(QPalette.Window)
        return bg_color.lightness() < 128

    def get_colors(self) -> dict:
        """Returns color tokens appropriate for current light/dark mode."""
        if self.is_dark_mode():
            return {
                "bg_panel": "#2b2b2b",
                "bg_dropzone": "#252526",
                "bg_dropzone_hover": "#2a2d2e",
                "border": "#444444",
                "border_accent": "#007acc",
                "text_primary": "#e1e1e1",
                "text_secondary": "#aaaaaa",
                "preview_bg": "#1e1e1e"
            }
        else:
            return {
                "bg_panel": "#fafafa",
                "bg_dropzone": "#f9f9f9",
                "bg_dropzone_hover": "#f0f8ff",
                "border": "#ccc",
                "border_accent": "#007acc",
                "text_primary": "#333333",
                "text_secondary": "#555555",
                "preview_bg": "#1e1e1e"
            }

    def _on_system_theme_changed(self):
        self.theme_changed.emit(self.is_dark_mode())


# Global instance for easy import across widgets
theme_manager = ThemeManager()