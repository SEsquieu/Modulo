from __future__ import annotations

from modulo.gui.controller import GuiAppController, GuiShellState

try:
    from PySide6.QtCore import QTimer, Qt
    from PySide6.QtWidgets import (
        QApplication,
        QComboBox,
        QFrame,
        QGroupBox,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMainWindow,
        QPushButton,
        QPlainTextEdit,
        QScrollArea,
        QTabWidget,
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
        self.status_strip = QLabel()
        self.status_strip.setWordWrap(True)
        self.status_strip.setStyleSheet("color: #a1a1aa; font-size: 13px;")

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
        self.continuity_summary_label = QLabel()
        self.continuity_summary_label.setWordWrap(True)
        self.activity_box = QPlainTextEdit()
        self.activity_box.setReadOnly(True)
        self.activity_box.setMinimumHeight(110)
        self.buyer_model_notice_label = QLabel()
        self.buyer_model_notice_label.setWordWrap(True)
        self.openclaw_status_label = QLabel()
        self.openclaw_status_label.setStyleSheet("font-weight: 600;")
        self.openclaw_summary_label = QLabel()
        self.openclaw_summary_label.setWordWrap(True)
        self.openclaw_details_box = QPlainTextEdit()
        self.openclaw_details_box.setReadOnly(True)
        self.openclaw_details_box.setMinimumHeight(90)
        self.hosting_model_combo = QComboBox()
        self.hosting_model_combo.currentIndexChanged.connect(self._apply_selected_hosting_model)
        self.ollama_status_label = QLabel()
        self.ollama_status_label.setStyleSheet("font-weight: 600;")
        self.hosting_mode_label = QLabel()
        self.hosting_mode_label.setStyleSheet("font-weight: 600;")
        self.ollama_summary_label = QLabel()
        self.ollama_summary_label.setWordWrap(True)
        self.ollama_inventory_summary_label = QLabel()
        self.ollama_inventory_summary_label.setWordWrap(True)
        self.hosting_readiness_label = QLabel()
        self.hosting_readiness_label.setStyleSheet("font-weight: 600;")
        self.hosting_preflight_summary_label = QLabel()
        self.hosting_preflight_summary_label.setWordWrap(True)
        self.hosting_preflight_reason_label = QLabel()
        self.hosting_preflight_reason_label.setWordWrap(True)
        self.hosting_inventory_label = QLabel()
        self.hosting_inventory_label.setWordWrap(True)

        self.connect_button = QPushButton("Configure OpenClaw")
        self.connect_button.clicked.connect(self._run_openclaw_action)

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

        overview_box = QGroupBox("Overview")
        overview_layout = QVBoxLayout()
        overview_layout.addWidget(self.title_label)
        overview_layout.addWidget(self.subtitle_label)
        overview_box.setLayout(overview_layout)

        host_setup_box = QGroupBox("Hosting Setup")
        host_setup_layout = QVBoxLayout()
        hosting_setup_prompt_row = QHBoxLayout()
        hosting_setup_prompt_row.addWidget(QLabel("Hosting model"))
        hosting_setup_prompt_row.addWidget(self.hosting_model_combo)
        host_setup_layout.addLayout(hosting_setup_prompt_row)
        host_setup_layout.addWidget(self.hosting_mode_label)
        host_setup_layout.addWidget(self.ollama_status_label)
        host_setup_layout.addWidget(self.ollama_summary_label)
        host_setup_layout.addWidget(self.ollama_inventory_summary_label)
        host_setup_layout.addWidget(self.hosting_readiness_label)
        host_setup_layout.addWidget(self.hosting_preflight_summary_label)
        host_setup_layout.addWidget(self.hosting_preflight_reason_label)
        host_setup_layout.addWidget(self.hosting_inventory_label)
        host_setup_box.setLayout(host_setup_layout)

        worker_box = QGroupBox("Hosting")
        worker_layout = QVBoxLayout()
        hosting_controls_row = QHBoxLayout()
        hosting_controls_row.addWidget(self.start_button)
        hosting_controls_row.addWidget(self.stop_button)
        hosting_controls_row.addWidget(self.restart_button)
        worker_layout.addLayout(hosting_controls_row)
        worker_layout.addWidget(self.worker_registration_label)
        worker_layout.addWidget(self.worker_health_summary_label)
        worker_layout.addWidget(self.worker_activity_label)
        worker_layout.addWidget(self.worker_id_label)
        worker_layout.addWidget(self.worker_state_label)
        worker_layout.addWidget(self.worker_models_label)
        worker_layout.addWidget(self.worker_load_label)
        worker_layout.addWidget(self.worker_jobs_label)
        worker_layout.addWidget(self.worker_last_job_label)
        worker_layout.addWidget(self.worker_error_label)
        worker_box.setLayout(worker_layout)

        buyer_box = QGroupBox("Buyer Routing")
        buyer_layout = QVBoxLayout()
        buyer_layout.addWidget(self.openclaw_status_label)
        buyer_layout.addWidget(self.openclaw_summary_label)
        buyer_layout.addWidget(self.buyer_model_notice_label)
        buyer_layout.addWidget(self.openclaw_details_box)
        buyer_layout.addWidget(self.connect_button)
        buyer_box.setLayout(buyer_layout)

        diagnostics_box = QGroupBox("Diagnostics")
        smoke_layout = QVBoxLayout()
        prompt_row = QHBoxLayout()
        prompt_row.addWidget(QLabel("Prompt"))
        prompt_row.addWidget(self.smoke_prompt_input)
        smoke_layout.addLayout(prompt_row)
        smoke_layout.addWidget(self.smoke_button)
        smoke_layout.addWidget(self.smoke_result_label)
        smoke_layout.addWidget(self.smoke_summary_label)
        smoke_layout.addWidget(self.smoke_details_box)
        smoke_layout.addWidget(self.diagnostics_summary_label)
        smoke_layout.addWidget(self.diagnostics_details_box)
        smoke_layout.addWidget(self.continuity_summary_label)
        smoke_layout.addWidget(self.activity_box)
        diagnostics_box.setLayout(smoke_layout)

        host_tab = QWidget()
        host_tab_layout = QVBoxLayout()
        host_tab_layout.setContentsMargins(0, 0, 0, 0)
        host_tab_layout.setSpacing(12)
        host_tab_layout.addWidget(host_setup_box)
        host_tab_layout.addWidget(worker_box)
        host_tab.setLayout(host_tab_layout)

        buyer_tab = QWidget()
        buyer_tab_layout = QVBoxLayout()
        buyer_tab_layout.setContentsMargins(0, 0, 0, 0)
        buyer_tab_layout.setSpacing(12)
        buyer_tab_layout.addWidget(buyer_box)
        buyer_tab_layout.addStretch(1)
        buyer_tab.setLayout(buyer_tab_layout)

        diagnostics_tab = QWidget()
        diagnostics_tab_layout = QVBoxLayout()
        diagnostics_tab_layout.setContentsMargins(0, 0, 0, 0)
        diagnostics_tab_layout.setSpacing(12)
        diagnostics_tab_layout.addWidget(diagnostics_box)
        diagnostics_tab_layout.addStretch(1)
        diagnostics_tab.setLayout(diagnostics_tab_layout)

        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(host_tab, "Host")
        self.tab_widget.addTab(buyer_tab, "Buyer")
        self.tab_widget.addTab(diagnostics_tab, "Diagnostics")

        root = QWidget()
        root_layout = QVBoxLayout()
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(12)
        root_layout.addWidget(overview_box)
        root_layout.addWidget(self.tab_widget)
        root_layout.addStretch(1)
        root.setLayout(root_layout)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setWidget(root)

        container = QWidget()
        container_layout = QVBoxLayout()
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        container_layout.addWidget(self.scroll_area, 1)
        container_layout.addWidget(self.status_strip, 0)
        container.setLayout(container_layout)
        self.setCentralWidget(container)

        self._apply_window_sizing()

        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(1000)
        self._poll_timer.timeout.connect(self._poll_state)
        self._poll_timer.start()

        self._apply_state(self.controller.refresh())

    def _apply_window_sizing(self) -> None:
        screen = self.screen() or QApplication.primaryScreen()
        if screen is None:
            return
        available = screen.availableGeometry()
        target_width = min(920, max(720, available.width() - 120))
        target_height = min(760, max(520, available.height() - 120))
        self.resize(target_width, target_height)

    def _poll_state(self) -> None:
        scrollbar = self.scroll_area.verticalScrollBar()
        previous_value = scrollbar.value()
        self._apply_state(self.controller.poll_worker())
        scrollbar.setValue(previous_value)

    def _run_smoke_test_from_input(self) -> None:
        prompt = self.smoke_prompt_input.text().strip() or "GUI smoke test request"
        self._apply_state(self.controller.run_smoke_test(prompt))

    def _run_openclaw_action(self) -> None:
        self._apply_state(self.controller.configure_openclaw())

    def _apply_selected_hosting_model(self) -> None:
        model_id = self.hosting_model_combo.currentData()
        if isinstance(model_id, str) and model_id:
            state = self.controller.refresh()
            if model_id != state.hosting_selected_model_id:
                self._apply_state(self.controller.select_hosting_model(model_id))

    def _apply_state(self, state: GuiShellState) -> None:
        self.title_label.setText(state.home_title)
        self.subtitle_label.setText(state.home_subtitle)

        self.status_strip.setText(
            " | ".join(
                (
                    f"Modulo {'online' if state.connected_to_modulo else 'offline'}",
                    f"Hosting {'enabled' if state.hosting_enabled else 'disabled'}",
                    f"Worker {state.worker_status_badge.lower()}",
                )
            )
        )

        self.connect_button.setText(state.openclaw_action_label)
        self.connect_button.setEnabled(state.connect_action_enabled)
        self.hosting_model_combo.setEnabled(state.hosting_setup_action_enabled)
        self.start_button.setEnabled(state.start_action_enabled)
        self.stop_button.setEnabled(state.stop_action_enabled)
        self.restart_button.setEnabled(state.restart_action_enabled)
        self.smoke_button.setEnabled(state.smoke_action_enabled)

        self.openclaw_status_label.setText(
            f"Status: {state.openclaw_status_badge}"
        )
        self.openclaw_summary_label.setText(state.openclaw_summary)
        self.buyer_model_notice_label.setText(
            "Buyer model selection is a separate step. OpenClaw routing only matters after a buyer "
            "model has been chosen, and that selector is not implemented in the client yet."
        )
        self.openclaw_details_box.setPlainText(
            f"{state.openclaw_details}\n\n{state.openclaw_safety_note}"
        )

        combo_model_ids = tuple(
            self.hosting_model_combo.itemData(index)
            for index in range(self.hosting_model_combo.count())
        )
        if combo_model_ids != state.hosting_available_model_ids:
            self.hosting_model_combo.blockSignals(True)
            self.hosting_model_combo.clear()
            for label, model_id in zip(
                state.hosting_available_model_labels,
                state.hosting_available_model_ids,
                strict=False,
            ):
                self.hosting_model_combo.addItem(label, model_id)
            self.hosting_model_combo.blockSignals(False)

        selected_index = self.hosting_model_combo.findData(state.hosting_selected_model_id)
        if selected_index >= 0 and selected_index != self.hosting_model_combo.currentIndex():
            self.hosting_model_combo.blockSignals(True)
            self.hosting_model_combo.setCurrentIndex(selected_index)
            self.hosting_model_combo.blockSignals(False)

        self.hosting_mode_label.setText(f"Hosting mode: {state.hosting_mode_badge}")
        self.ollama_status_label.setText(f"Ollama: {state.ollama_status_badge}")
        self.ollama_summary_label.setText(state.ollama_summary)
        self.ollama_inventory_summary_label.setText(state.ollama_inventory_summary)
        self.hosting_readiness_label.setText(f"Readiness: {state.hosting_readiness_badge}")
        self.hosting_preflight_summary_label.setText(state.hosting_preflight_summary)
        self.hosting_preflight_reason_label.setText(
            f"Why blocked: {state.hosting_preflight_reason}"
            if state.hosting_preflight_reason
            else ""
        )
        supported_installed = len(state.hosting_supported_installed_model_ids)
        supported_missing = len(state.hosting_supported_missing_model_ids)
        unsupported_installed = len(state.hosting_unsupported_installed_model_ids)
        self.hosting_inventory_label.setText(
            "Inventory: "
            f"{supported_installed} supported installed, "
            f"{supported_missing} supported missing, "
            f"{unsupported_installed} installed outside the curated catalog."
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
        self.continuity_summary_label.setText(state.continuity_summary)
        self.activity_box.setPlainText("\n".join(state.activity_lines))


def launch_gui(controller: GuiAppController | None = None) -> int:
    app = QApplication.instance() or QApplication([])
    window = ModuloMainWindow(controller or GuiAppController.build_default())
    window.show()
    return app.exec()
