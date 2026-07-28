from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
from frontend.theme.theme_manager import theme_manager


def create_bordered_section(title: str, inner_widget: QWidget) -> QWidget:
    """Wraps a widget inside a clean panel with dynamic theme colors."""
    container = QWidget()
    container.setObjectName("BorderedSection")

    colors = theme_manager.get_colors()

    container.setStyleSheet(f"""
        QWidget#BorderedSection {{
            border: 1px solid {colors['border']};
            border-radius: 6px;
            background-color: {colors['bg_panel']};
        }}
    """)

    layout = QVBoxLayout(container)
    layout.setContentsMargins(10, 10, 10, 10)
    layout.setSpacing(8)

    title_label = QLabel(title)
    title_label.setStyleSheet(f"""
        font-weight: bold;
        font-size: 13px;
        color: {colors['text_primary']};
        border: none;
        background: transparent;
    """)

    layout.addWidget(title_label)
    layout.addWidget(inner_widget, stretch=1)

    return container