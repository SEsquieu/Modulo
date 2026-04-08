from __future__ import annotations

from modulo.gui.controller import GuiAppController, GuiShellState

try:
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import (
        QApplication,
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
        self.resize(760, 520)

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
        home_layout.addWidget(self.connected_label, 0, 0)
        home_layout.addWidget(self.openclaw_label, 1, 0)
        home_layout.addWidget(self.hosting_label, 2, 0)
        home_layout.addWidget(self.worker_health_label, 3, 0)
        home_layout.addWidget(connect_button, 0, 1)
        home_layout.addWidget(start_button, 1, 1)
        home_layout.addWidget(stop_button, 2, 1)
        home_layout.addWidget(smoke_button, 3, 1)
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

    def _poll_state(self) -> None:
        self._apply_state(self.controller.poll_worker())

    def _apply_state(self, state: GuiShellState) -> None:
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
