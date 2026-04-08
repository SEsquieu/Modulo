from __future__ import annotations

from modulo.gui.controller import GuiAppController, GuiShellState

try:
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import (
        QApplication,
        QFrame,
        QGridLayout,
        QGroupBox,
        QLabel,
        QMainWindow,
        QPushButton,
        QPlainTextEdit,
        QVBoxLayout,
        QWidget,
    )
except ImportError as exc:  # pragma: no cover - import guard for environments without PySide6
    raise RuntimeError(
        "PySide6 is required for the Modulo GUI shell. Install it with `python -m pip install -e .[gui]`."
    ) from exc


class ModuloMainWindow(QMainWindow):
    def __init__(self, controller: GuiAppController) -> None:
        super().__init__()
        self.controller = controller
        self.setWindowTitle("Modulo")
        self.resize(900, 640)

        self.title_label = QLabel()
        self.title_label.setStyleSheet("font-size: 24px; font-weight: 700;")
        self.subtitle_label = QLabel()
        self.subtitle_label.setWordWrap(True)

        self.connection_card = self._build_status_card("Connection")
        self.hosting_card = self._build_status_card("Hosting")
        self.worker_card = self._build_status_card("Worker")
        self.smoke_card = self._build_status_card("Smoke Test")

        self.connected_label = QLabel()
        self.openclaw_label = QLabel()
        self.hosting_label = QLabel()
        self.worker_health_label = QLabel()

        self.worker_id_label = QLabel()
        self.worker_state_label = QLabel()
        self.worker_models_label = QLabel()
        self.worker_load_label = QLabel()
        self.worker_jobs_label = QLabel()
        self.worker_error_label = QLabel()

        self.smoke_summary_label = QLabel()
        self.smoke_details_box = QPlainTextEdit()
        self.smoke_details_box.setReadOnly(True)
        self.smoke_details_box.setMinimumHeight(120)

        connect_button = QPushButton("Connect OpenClaw")
        connect_button.clicked.connect(lambda: self._apply_state(self.controller.connect_openclaw()))

        start_button = QPushButton("Start Hosting")
        start_button.clicked.connect(lambda: self._apply_state(self.controller.start_hosting()))

        stop_button = QPushButton("Stop Hosting")
        stop_button.clicked.connect(lambda: self._apply_state(self.controller.stop_hosting()))

        restart_button = QPushButton("Restart Hosting")
        restart_button.clicked.connect(lambda: self._apply_state(self.controller.restart_hosting()))

        smoke_button = QPushButton("Run Smoke Test")
        smoke_button.clicked.connect(lambda: self._apply_state(self.controller.run_smoke_test()))

        home_box = QGroupBox("Home")
        home_layout = QGridLayout()
        home_layout.addWidget(self.title_label, 0, 0, 1, 2)
        home_layout.addWidget(self.subtitle_label, 1, 0, 1, 2)
        home_layout.addWidget(self.connection_card, 2, 0)
        home_layout.addWidget(self.hosting_card, 2, 1)
        home_layout.addWidget(self.worker_card, 3, 0)
        home_layout.addWidget(self.smoke_card, 3, 1)
        home_layout.addWidget(connect_button, 4, 0)
        home_layout.addWidget(smoke_button, 4, 1)
        home_layout.addWidget(start_button, 5, 0)
        home_layout.addWidget(stop_button, 5, 1)
        home_box.setLayout(home_layout)

        worker_box = QGroupBox("Worker")
        worker_layout = QVBoxLayout()
        worker_layout.addWidget(self.worker_id_label)
        worker_layout.addWidget(self.worker_state_label)
        worker_layout.addWidget(self.worker_models_label)
        worker_layout.addWidget(self.worker_load_label)
        worker_layout.addWidget(self.worker_jobs_label)
        worker_layout.addWidget(self.worker_error_label)
        worker_layout.addWidget(restart_button)
        worker_box.setLayout(worker_layout)

        smoke_box = QGroupBox("Smoke Test")
        smoke_layout = QVBoxLayout()
        smoke_layout.addWidget(self.smoke_summary_label)
        smoke_layout.addWidget(self.smoke_details_box)
        smoke_box.setLayout(smoke_layout)

        root = QWidget()
        root_layout = QVBoxLayout()
        root_layout.addWidget(home_box)
        root_layout.addWidget(worker_box)
        root_layout.addWidget(smoke_box)
        root.setLayout(root_layout)
        self.setCentralWidget(root)

        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(1000)
        self._poll_timer.timeout.connect(self._poll_state)
        self._poll_timer.start()

        self._apply_state(self.controller.refresh())

    @staticmethod
    def _build_status_card(title: str) -> QFrame:
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setStyleSheet(
            "QFrame { border: 1px solid #d4d4d8; border-radius: 8px; padding: 8px; background: #fafaf9; }"
        )
        layout = QVBoxLayout()
        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight: 600; font-size: 14px;")
        value_label = QLabel()
        value_label.setObjectName("value")
        value_label.setWordWrap(True)
        value_label.setStyleSheet("font-size: 13px;")
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        frame.setLayout(layout)
        return frame

    @staticmethod
    def _set_card_text(card: QFrame, text: str) -> None:
        value_label = card.findChild(QLabel, "value")
        if value_label is not None:
            value_label.setText(text)

    def _poll_state(self) -> None:
        self._apply_state(self.controller.poll_worker())

    def _apply_state(self, state: GuiShellState) -> None:
        self.title_label.setText(state.home_title)
        self.subtitle_label.setText(state.home_subtitle)

        self.connected_label.setText(
            f"Modulo connection: {'Connected' if state.connected_to_modulo else 'Disconnected'}"
        )
        self.openclaw_label.setText(
            f"OpenClaw: {'Connected' if state.openclaw_connected else 'Not connected'}"
        )
        self.hosting_label.setText(
            f"Hosting: {'Enabled' if state.hosting_enabled else 'Disabled'}"
        )
        self.worker_health_label.setText(
            f"Worker health: {'Healthy' if state.worker_healthy else 'Unhealthy'}"
        )
        self._set_card_text(self.connection_card, state.connection_summary)
        self._set_card_text(self.hosting_card, state.hosting_summary)
        self._set_card_text(
            self.worker_card,
            f"{state.worker_status_badge}\nRuntime: {state.worker_runtime_state}",
        )
        self._set_card_text(
            self.smoke_card,
            f"{state.smoke_status_badge}\n{state.smoke_test_summary}",
        )

        self.worker_id_label.setText(f"Worker ID: {state.worker_id or 'Unavailable'}")
        self.worker_state_label.setText(f"Runtime state: {state.worker_runtime_state}")
        self.worker_models_label.setText(f"Enabled models: {state.enabled_models_text or 'None'}")
        self.worker_load_label.setText(f"Current load: {state.current_load}")
        self.worker_jobs_label.setText(
            f"Jobs: {state.completed_jobs} completed / {state.failed_jobs} failed"
        )
        self.worker_error_label.setText(
            f"Last worker error: {state.last_worker_error or 'None'}"
        )

        self.smoke_summary_label.setText(state.smoke_test_summary)
        self.smoke_details_box.setPlainText(state.smoke_test_details)


def launch_gui(controller: GuiAppController | None = None) -> int:
    app = QApplication.instance() or QApplication([])
    window = ModuloMainWindow(controller or GuiAppController.build_default())
    window.show()
    return app.exec()
