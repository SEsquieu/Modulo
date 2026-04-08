from __future__ import annotations

from modulo.gui.controller import GuiAppController, GuiShellState

try:
    from PySide6.QtCore import QTimer, Qt
    from PySide6.QtWidgets import (
        QApplication,
        QFrame,
        QGridLayout,
        QGroupBox,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMainWindow,
        QPushButton,
        QPlainTextEdit,
        QScrollArea,
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
        self.resize(880, 720)
        self.setMinimumSize(720, 520)

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
        self.worker_registration_label = QLabel()
        self.worker_health_summary_label = QLabel()
        self.worker_activity_label = QLabel()
        self.worker_models_label = QLabel()
        self.worker_load_label = QLabel()
        self.worker_jobs_label = QLabel()
        self.worker_last_job_label = QLabel()
        self.worker_error_label = QLabel()

        self.smoke_summary_label = QLabel()
        self.smoke_result_label = QLabel()
        self.smoke_prompt_input = QLineEdit()
        self.smoke_prompt_input.setPlaceholderText("Enter a smoke-test prompt")
        self.smoke_details_box = QPlainTextEdit()
        self.smoke_details_box.setReadOnly(True)
        self.smoke_details_box.setMinimumHeight(120)
        self.diagnostics_summary_label = QLabel()
        self.diagnostics_summary_label.setWordWrap(True)
        self.diagnostics_details_box = QPlainTextEdit()
        self.diagnostics_details_box.setReadOnly(True)
        self.diagnostics_details_box.setMinimumHeight(100)
        self.openclaw_status_label = QLabel()
        self.openclaw_status_label.setStyleSheet("font-weight: 600;")
        self.openclaw_summary_label = QLabel()
        self.openclaw_summary_label.setWordWrap(True)
        self.openclaw_details_box = QPlainTextEdit()
        self.openclaw_details_box.setReadOnly(True)
        self.openclaw_details_box.setMinimumHeight(90)

        self.connect_button = QPushButton("Connect OpenClaw")
        self.connect_button.clicked.connect(
            self._toggle_openclaw_connection
        )

        self.start_button = QPushButton("Start Hosting")
        self.start_button.clicked.connect(
            lambda: self._apply_state(self.controller.start_hosting())
        )

        self.stop_button = QPushButton("Stop Hosting")
        self.stop_button.clicked.connect(lambda: self._apply_state(self.controller.stop_hosting()))

        self.restart_button = QPushButton("Restart Hosting")
        self.restart_button.clicked.connect(
            lambda: self._apply_state(self.controller.restart_hosting())
        )

        self.smoke_button = QPushButton("Run Smoke Test")
        self.smoke_button.clicked.connect(
            self._run_smoke_test_from_input
        )

        home_box = QGroupBox("Home")
        home_layout = QGridLayout()
        home_layout.setHorizontalSpacing(12)
        home_layout.setVerticalSpacing(12)
        home_layout.addWidget(self.title_label, 0, 0, 1, 2)
        home_layout.addWidget(self.subtitle_label, 1, 0, 1, 2)
        home_layout.addWidget(self.connection_card, 2, 0)
        home_layout.addWidget(self.hosting_card, 2, 1)
        home_layout.addWidget(self.worker_card, 3, 0)
        home_layout.addWidget(self.smoke_card, 3, 1)
        home_layout.addWidget(self.connect_button, 4, 0)
        home_layout.addWidget(self.smoke_button, 4, 1)
        home_box.setLayout(home_layout)

        hosting_box = QGroupBox("Hosting Controls")
        hosting_layout = QGridLayout()
        hosting_layout.addWidget(self.start_button, 0, 0)
        hosting_layout.addWidget(self.stop_button, 0, 1)
        hosting_layout.addWidget(self.restart_button, 1, 0, 1, 2)
        hosting_box.setLayout(hosting_layout)

        openclaw_box = QGroupBox("OpenClaw")
        openclaw_layout = QVBoxLayout()
        openclaw_layout.addWidget(self.openclaw_status_label)
        openclaw_layout.addWidget(self.openclaw_summary_label)
        openclaw_layout.addWidget(self.openclaw_details_box)
        openclaw_layout.addWidget(self.connect_button)
        openclaw_box.setLayout(openclaw_layout)

        worker_box = QGroupBox("Worker")
        worker_layout = QVBoxLayout()
        worker_layout.addWidget(self.worker_id_label)
        worker_layout.addWidget(self.worker_state_label)
        worker_layout.addWidget(self.worker_registration_label)
        worker_layout.addWidget(self.worker_health_summary_label)
        worker_layout.addWidget(self.worker_activity_label)
        worker_layout.addWidget(self.worker_models_label)
        worker_layout.addWidget(self.worker_load_label)
        worker_layout.addWidget(self.worker_jobs_label)
        worker_layout.addWidget(self.worker_last_job_label)
        worker_layout.addWidget(self.worker_error_label)
        worker_box.setLayout(worker_layout)

        smoke_box = QGroupBox("Smoke Test")
        smoke_layout = QVBoxLayout()
        prompt_row = QHBoxLayout()
        prompt_row.addWidget(QLabel("Prompt"))
        prompt_row.addWidget(self.smoke_prompt_input)
        smoke_layout.addLayout(prompt_row)
        smoke_layout.addWidget(self.smoke_result_label)
        smoke_layout.addWidget(self.smoke_summary_label)
        smoke_layout.addWidget(self.smoke_details_box)
        smoke_layout.addWidget(self.diagnostics_summary_label)
        smoke_layout.addWidget(self.diagnostics_details_box)
        smoke_box.setLayout(smoke_layout)

        root = QWidget()
        root_layout = QVBoxLayout()
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(12)
        root_layout.addWidget(home_box)
        root_layout.addWidget(openclaw_box)
        root_layout.addWidget(hosting_box)
        root_layout.addWidget(worker_box)
        root_layout.addWidget(smoke_box)
        root_layout.addStretch(1)
        root.setLayout(root_layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidget(root)
        self.setCentralWidget(scroll)

        self._apply_window_sizing()

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
            "QFrame { border: 1px solid #3f3f46; border-radius: 10px; padding: 10px; background: #27272a; }"
        )
        layout = QVBoxLayout()
        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight: 600; font-size: 14px; color: #f4f4f5;")
        value_label = QLabel()
        value_label.setObjectName("value")
        value_label.setWordWrap(True)
        value_label.setStyleSheet("font-size: 13px; color: #d4d4d8;")
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        frame.setLayout(layout)
        return frame

    def _apply_window_sizing(self) -> None:
        screen = self.screen() or QApplication.primaryScreen()
        if screen is None:
            return
        available = screen.availableGeometry()
        target_width = min(920, max(720, available.width() - 120))
        target_height = min(760, max(520, available.height() - 120))
        self.resize(target_width, target_height)

    @staticmethod
    def _set_card_text(card: QFrame, text: str) -> None:
        value_label = card.findChild(QLabel, "value")
        if value_label is not None:
            value_label.setText(text)

    def _poll_state(self) -> None:
        self._apply_state(self.controller.poll_worker())

    def _run_smoke_test_from_input(self) -> None:
        prompt = self.smoke_prompt_input.text().strip() or "GUI smoke test request"
        self._apply_state(self.controller.run_smoke_test(prompt))

    def _toggle_openclaw_connection(self) -> None:
        state = self.controller.refresh()
        next_state = (
            self.controller.disconnect_openclaw()
            if state.openclaw_connected
            else self.controller.connect_openclaw()
        )
        self._apply_state(next_state)

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
            f"{state.worker_status_badge}\n{state.worker_health_summary}",
        )
        self._set_card_text(
            self.smoke_card,
            f"{state.smoke_status_badge}\n{state.smoke_test_summary}",
        )

        self.connect_button.setText(state.openclaw_action_label)
        self.connect_button.setEnabled(state.connect_action_enabled)
        self.start_button.setEnabled(state.start_action_enabled)
        self.stop_button.setEnabled(state.stop_action_enabled)
        self.restart_button.setEnabled(state.restart_action_enabled)
        self.smoke_button.setEnabled(state.smoke_action_enabled)

        self.openclaw_status_label.setText(
            f"Status: {state.openclaw_status_badge}"
        )
        self.openclaw_summary_label.setText(state.openclaw_summary)
        self.openclaw_details_box.setPlainText(
            f"{state.openclaw_details}\n\n{state.openclaw_safety_note}"
        )

        self.worker_id_label.setText(f"Worker ID: {state.worker_id or 'Unavailable'}")
        self.worker_state_label.setText(f"Runtime state: {state.worker_runtime_state}")
        self.worker_registration_label.setText(f"Registration: {state.worker_registration_text}")
        self.worker_health_summary_label.setText(f"Health: {state.worker_health_summary}")
        self.worker_activity_label.setText(f"Activity: {state.worker_activity_summary}")
        self.worker_models_label.setText(f"Enabled models: {state.enabled_models_text or 'None'}")
        self.worker_load_label.setText(f"Current load: {state.current_load}")
        self.worker_jobs_label.setText(
            f"Jobs: {state.completed_jobs} completed / {state.failed_jobs} failed"
        )
        self.worker_last_job_label.setText(
            f"Last job: {state.last_job_id or 'None'}"
            + (f" ({state.last_job_status})" if state.last_job_status else "")
        )
        self.worker_error_label.setText(
            f"Last worker error: {state.last_worker_error or 'None'}"
        )

        self.smoke_summary_label.setText(state.smoke_test_summary)
        self.smoke_result_label.setText(f"Result: {state.smoke_test_result_label}")
        if self.smoke_prompt_input.text() != state.smoke_test_prompt:
            self.smoke_prompt_input.setText(state.smoke_test_prompt)
        self.smoke_details_box.setPlainText(state.smoke_test_details)
        self.diagnostics_summary_label.setText(state.diagnostics_summary)
        self.diagnostics_details_box.setPlainText(state.diagnostics_details)


def launch_gui(controller: GuiAppController | None = None) -> int:
    app = QApplication.instance() or QApplication([])
    window = ModuloMainWindow(controller or GuiAppController.build_default())
    window.show()
    return app.exec()
