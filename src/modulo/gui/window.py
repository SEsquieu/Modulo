from __future__ import annotations

from datetime import datetime, timezone

from modulo.gui.controller import GuiAppController, GuiShellState

try:
    from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Qt, Signal
    from PySide6.QtGui import QFont
    from PySide6.QtWidgets import (
        QApplication,
        QComboBox,
        QFrame,
        QGroupBox,
        QHBoxLayout,
        QLabel,
        QMainWindow,
        QProgressBar,
        QPushButton,
        QPlainTextEdit,
        QScrollArea,
        QSizePolicy,
        QTabWidget,
        QVBoxLayout,
        QWidget,
    )
except ImportError as exc:  # pragma: no cover - import guard for environments without PySide6
    raise RuntimeError(
        "PySide6 is required for the Modulo GUI shell. Install it with `python -m pip install -e .[gui]`."
    ) from exc


class _AsyncGuiTaskSignals(QObject):
    completed = Signal(object)
    failed = Signal(str)


class _AsyncGuiTask(QRunnable):
    def __init__(self, fn) -> None:
        super().__init__()
        self.fn = fn
        self.signals = _AsyncGuiTaskSignals()

    def run(self) -> None:
        try:
            result = self.fn()
        except Exception as exc:  # pragma: no cover - UI background safeguard
            self.signals.failed.emit(str(exc))
            return
        self.signals.completed.emit(result)


class ModuloMainWindow(QMainWindow):
    def __init__(self, controller: GuiAppController) -> None:
        super().__init__()
        self.controller = controller
        self._thread_pool = QThreadPool.globalInstance()
        self._action_in_flight = False
        self._poll_in_flight = False
        self._ui_notice = ""
        self._active_action_kind = ""
        self._latest_state: GuiShellState | None = None
        self._active_tasks: list[_AsyncGuiTask] = []
        self.setWindowTitle("Modulo")
        self.resize(880, 720)
        self.setMinimumSize(720, 520)
        app_font = QFont("Consolas", 11)
        app_font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(app_font)
        self._apply_retro_theme()

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
        self.host_state_badge_label = QLabel()
        self.host_state_badge_label.setStyleSheet("font-size: 18px; font-weight: 700;")
        self.host_state_summary_label = QLabel()
        self.host_state_summary_label.setWordWrap(True)
        self.host_activity_label = QLabel()
        self.host_activity_label.setWordWrap(True)
        self.host_activity_bar = QProgressBar()
        self.host_activity_bar.setRange(0, 0)
        self.host_activity_bar.setTextVisible(False)
        self.host_activity_bar.hide()
        self.host_card_model_value = QLabel()
        self.host_card_model_value.setWordWrap(True)

        self.smoke_summary_label = QLabel()
        self.smoke_result_label = QLabel()
        self.smoke_activity_label = QLabel()
        self.smoke_activity_label.setWordWrap(True)
        self.smoke_activity_bar = QProgressBar()
        self.smoke_activity_bar.setRange(0, 0)
        self.smoke_activity_bar.setTextVisible(False)
        self.smoke_activity_bar.hide()
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
        self.buyer_platform_summary_label = QLabel()
        self.buyer_platform_summary_label.setWordWrap(True)
        self.buyer_account_summary_label = QLabel()
        self.buyer_account_summary_label.setWordWrap(True)
        self.buyer_credits_label = QLabel()
        self.buyer_credits_label.setWordWrap(True)
        self.buyer_config_label = QLabel()
        self.buyer_config_label.setWordWrap(True)
        self.buyer_network_models_box = QPlainTextEdit()
        self.buyer_network_models_box.setReadOnly(True)
        self.buyer_network_models_box.setMinimumHeight(110)
        self.buyer_cloud_models_box = QPlainTextEdit()
        self.buyer_cloud_models_box.setReadOnly(True)
        self.buyer_cloud_models_box.setMinimumHeight(90)
        self.openclaw_status_label = QLabel()
        self.openclaw_status_label.setStyleSheet("font-weight: 600;")
        self.openclaw_summary_label = QLabel()
        self.openclaw_summary_label.setWordWrap(True)
        self.openclaw_guidance_label = QLabel()
        self.openclaw_guidance_label.setWordWrap(True)
        self.openclaw_plan_summary_label = QLabel()
        self.openclaw_plan_summary_label.setWordWrap(True)
        self.openclaw_details_box = QPlainTextEdit()
        self.openclaw_details_box.setReadOnly(True)
        self.openclaw_details_box.setMinimumHeight(90)
        self.openclaw_plan_box = QPlainTextEdit()
        self.openclaw_plan_box.setReadOnly(True)
        self.openclaw_plan_box.setMinimumHeight(110)
        self.hosting_model_combo = QComboBox()
        combo_font = QFont("Consolas", 11)
        self.hosting_model_combo.setFont(combo_font)
        self.hosting_model_combo.view().setFont(combo_font)
        self.hosting_model_combo.currentIndexChanged.connect(self._apply_selected_hosting_model)
        self.ollama_status_label = QLabel()
        self.ollama_status_label.setStyleSheet("font-weight: 600;")
        self.hosting_mode_label = QLabel()
        self.hosting_mode_label.setStyleSheet("font-weight: 600;")
        self.hosting_warm_state_label = QLabel()
        self.hosting_warm_state_label.setStyleSheet("font-weight: 600;")
        self.hosting_warm_summary_label = QLabel()
        self.hosting_warm_summary_label.setWordWrap(True)
        self.host_runtime_details_label = QLabel()
        self.host_runtime_details_label.setWordWrap(True)
        self.hosting_warm_details_label = QLabel()
        self.hosting_warm_details_label.setWordWrap(True)
        self.execution_mode_label = QLabel()
        self.execution_mode_label.setStyleSheet("font-weight: 600;")
        self.execution_summary_label = QLabel()
        self.execution_summary_label.setWordWrap(True)
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
        self.apply_openclaw_button = QPushButton("Apply staged plan")
        self.apply_openclaw_button.clicked.connect(self._apply_openclaw_plan)

        self.host_toggle_button = QPushButton("Enable Hosting")
        self.host_toggle_button.clicked.connect(self._toggle_hosting_async)
        self.host_toggle_button.setMinimumWidth(120)
        self.host_toggle_button.setMinimumHeight(40)

        self.restart_button = QPushButton("Refresh Host")
        self.restart_button.clicked.connect(self._restart_hosting_async)
        self.restart_button.setMaximumWidth(140)

        self.smoke_button = QPushButton("Run Smoke Test")
        self.smoke_button.clicked.connect(self._run_smoke_test)

        overview_box = QGroupBox("Overview")
        overview_layout = QVBoxLayout()
        overview_layout.addWidget(self.title_label)
        overview_layout.addWidget(self.subtitle_label)
        overview_box.setLayout(overview_layout)

        host_box = QGroupBox("Hosting")
        host_box.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Maximum,
        )
        host_layout = QVBoxLayout()
        host_header_row = QHBoxLayout()
        host_header_row.addWidget(self.host_state_badge_label, 1)
        host_header_row.addWidget(self.host_toggle_button, 0)
        host_layout.addLayout(host_header_row)
        hosting_setup_prompt_row = QHBoxLayout()
        hosting_setup_prompt_row.addWidget(QLabel("Model"))
        hosting_setup_prompt_row.addWidget(self.hosting_model_combo, 1)
        host_layout.addLayout(hosting_setup_prompt_row)
        host_layout.addWidget(self.host_activity_label)
        host_layout.addWidget(self.host_activity_bar)
        host_layout.addWidget(self._build_host_card("Loaded Model", self.host_card_model_value))

        self.host_detail_tabs = QTabWidget()
        self.host_detail_tabs.addTab(self._build_host_details_page(), "Runtime")
        self.host_detail_tabs.addTab(self._build_readiness_page(), "Model")
        self.host_detail_tabs.addTab(self._build_worker_details_page(), "Worker")
        self.host_detail_tabs.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Maximum,
        )
        host_layout.addWidget(self.host_detail_tabs)
        host_box.setLayout(host_layout)

        use_box = QGroupBox("Use")
        use_layout = QVBoxLayout()
        use_layout.addWidget(self.openclaw_status_label)
        use_layout.addWidget(self.openclaw_summary_label)
        use_layout.addWidget(self.openclaw_guidance_label)
        use_layout.addWidget(self.openclaw_plan_summary_label)
        use_layout.addWidget(self.buyer_model_notice_label)
        use_layout.addWidget(self.buyer_platform_summary_label)
        use_layout.addWidget(self.buyer_account_summary_label)
        use_layout.addWidget(self.buyer_credits_label)
        use_layout.addWidget(self.buyer_config_label)
        use_layout.addWidget(QLabel("Network models"))
        use_layout.addWidget(self.buyer_network_models_box)
        use_layout.addWidget(QLabel("Cloud models"))
        use_layout.addWidget(self.buyer_cloud_models_box)
        use_layout.addWidget(self.openclaw_details_box)
        use_layout.addWidget(self.openclaw_plan_box)
        use_layout.addWidget(self.connect_button)
        use_layout.addWidget(self.apply_openclaw_button)
        use_box.setLayout(use_layout)

        diagnostics_box = QGroupBox("Diagnostics")
        smoke_layout = QVBoxLayout()
        smoke_layout.addWidget(self.smoke_button)
        smoke_layout.addWidget(self.smoke_activity_label)
        smoke_layout.addWidget(self.smoke_activity_bar)
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
        host_tab_layout.addWidget(host_box)
        host_tab_layout.addStretch(1)
        host_tab.setLayout(host_tab_layout)

        use_tab = QWidget()
        use_tab_layout = QVBoxLayout()
        use_tab_layout.setContentsMargins(0, 0, 0, 0)
        use_tab_layout.setSpacing(12)
        use_tab_layout.addWidget(use_box)
        use_tab_layout.addStretch(1)
        use_tab.setLayout(use_tab_layout)

        diagnostics_tab = QWidget()
        diagnostics_tab_layout = QVBoxLayout()
        diagnostics_tab_layout.setContentsMargins(0, 0, 0, 0)
        diagnostics_tab_layout.setSpacing(12)
        diagnostics_tab_layout.addWidget(diagnostics_box)
        diagnostics_tab_layout.addStretch(1)
        diagnostics_tab.setLayout(diagnostics_tab_layout)

        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(use_tab, "Use")
        self.tab_widget.addTab(host_tab, "Host")
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

    def _apply_retro_theme(self) -> None:
        self.setStyleSheet(
            """
            QWidget {
                background-color: #09110c;
                color: #8df7a6;
                font-family: "Consolas", "Courier New", monospace;
            }
            QMainWindow {
                background-color: #09110c;
            }
            QGroupBox {
                border: 2px solid #2bd66b;
                margin-top: 14px;
                padding-top: 12px;
                background-color: #0f1712;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                top: 2px;
                padding: 0 6px;
                color: #b8ff65;
                background-color: #09110c;
                font-weight: 700;
            }
            QLabel {
                background: transparent;
            }
            QFrame {
                background-color: #111a15;
            }
            QScrollArea {
                border: none;
                background-color: #09110c;
            }
            QTabWidget::pane {
                border: 2px solid #2bd66b;
                top: -2px;
                background-color: #0f1712;
            }
            QTabBar::tab {
                background-color: #101712;
                color: #8df7a6;
                border: 2px solid #2bd66b;
                padding: 6px 14px;
                margin-right: 4px;
                min-width: 68px;
            }
            QTabBar::tab:selected {
                background-color: #b8ff65;
                color: #09110c;
            }
            QPushButton {
                background-color: #111a15;
                color: #8df7a6;
                border: 2px solid #2bd66b;
                border-radius: 0px;
                padding: 8px 14px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #16221b;
            }
            QPushButton:pressed {
                padding-top: 10px;
                padding-left: 16px;
            }
            QPushButton:disabled {
                background-color: #101712;
                color: #4d7658;
                border: 2px solid #31503a;
            }
            QComboBox, QPlainTextEdit {
                background-color: #050906;
                color: #8df7a6;
                border: 2px solid #2bd66b;
                border-radius: 0px;
                padding: 6px 8px;
                selection-background-color: #b8ff65;
                selection-color: #09110c;
            }
            QComboBox QAbstractItemView {
                background-color: #050906;
                color: #8df7a6;
                border: 2px solid #2bd66b;
                selection-background-color: #b8ff65;
                selection-color: #09110c;
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
            QComboBox::down-arrow {
                width: 10px;
                height: 10px;
            }
            QProgressBar {
                border: 2px solid #2bd66b;
                background-color: #050906;
                min-height: 10px;
            }
            QProgressBar::chunk {
                background-color: #b8ff65;
            }
            QScrollBar:vertical {
                background-color: #050906;
                width: 12px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background-color: #2bd66b;
                min-height: 24px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            """
        )

    def _build_host_card(self, title: str, value_label: QLabel) -> QFrame:
        card = QFrame()
        card.setFrameShape(QFrame.StyledPanel)
        card.setStyleSheet(
            "QFrame { border: 1px solid #3f3f46; border-radius: 8px; padding: 8px; }"
        )
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 11px; color: #a1a1aa; text-transform: uppercase;")
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        card.setLayout(layout)
        return card

    def _build_host_details_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        layout.addWidget(self.hosting_warm_summary_label)
        layout.addWidget(self.host_runtime_details_label)
        layout.addStretch(1)
        page.setLayout(layout)
        return page

    def _build_readiness_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        layout.addWidget(self.hosting_warm_details_label)
        layout.addStretch(1)
        page.setLayout(layout)
        return page

    def _build_worker_details_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        restart_row = QHBoxLayout()
        restart_row.addStretch(1)
        restart_row.addWidget(self.restart_button, 0)
        layout.addLayout(restart_row)
        layout.addWidget(self.worker_registration_label)
        layout.addWidget(self.worker_health_summary_label)
        layout.addWidget(self.worker_activity_label)
        layout.addWidget(self.worker_id_label)
        layout.addWidget(self.worker_state_label)
        layout.addWidget(self.worker_models_label)
        layout.addWidget(self.worker_load_label)
        layout.addWidget(self.worker_jobs_label)
        layout.addWidget(self.worker_last_job_label)
        layout.addWidget(self.worker_error_label)
        layout.addStretch(1)
        page.setLayout(layout)
        return page

    def _apply_window_sizing(self) -> None:
        screen = self.screen() or QApplication.primaryScreen()
        if screen is None:
            return
        available = screen.availableGeometry()
        target_width = min(920, max(720, available.width() - 120))
        target_height = min(760, max(520, available.height() - 120))
        self.resize(target_width, target_height)

    def _poll_state(self) -> None:
        if self._action_in_flight or self._poll_in_flight:
            return
        scrollbar = self.scroll_area.verticalScrollBar()
        previous_value = scrollbar.value()
        self._run_async_state_action(
            self.controller.poll_worker,
            on_success=lambda state: self._apply_state_with_scroll_restore(state, previous_value),
            busy_message="",
            action=False,
        )
        scrollbar.setValue(previous_value)

    def _run_smoke_test(self) -> None:
        self._run_async_state_action(
            self.controller.run_smoke_test,
            busy_message="Running constrained smoke probe...",
            action_kind="smoke_test",
            action=True,
        )

    def _run_openclaw_action(self) -> None:
        self._run_async_state_action(
            self.controller.configure_openclaw,
            busy_message="Refreshing OpenClaw configuration state...",
            action_kind="openclaw",
            action=True,
        )

    def _apply_openclaw_plan(self) -> None:
        self._run_async_state_action(
            self.controller.apply_openclaw_connection,
            busy_message="Applying staged OpenClaw plan...",
            action_kind="openclaw",
            action=True,
        )

    def _apply_selected_hosting_model(self) -> None:
        model_id = self.hosting_model_combo.currentData()
        if isinstance(model_id, str) and model_id:
            if self._latest_state is not None and model_id == self._latest_state.hosting_selected_model_id:
                return
            self._run_async_state_action(
                lambda: self.controller.select_hosting_model(model_id),
                busy_message=f"Switching host model to {model_id}...",
                action_kind="host_warm",
                action=True,
            )

    def _start_hosting_async(self) -> None:
        self._run_async_state_action(
            self.controller.start_hosting,
            busy_message="Starting hosting and warming the selected model...",
            action_kind="host_warm",
            action=True,
        )

    def _toggle_hosting_async(self) -> None:
        latest = self._latest_state or self.controller.refresh()
        if latest.hosting_enabled:
            self._stop_hosting_async()
            return
        self._start_hosting_async()

    def _stop_hosting_async(self) -> None:
        self._run_async_state_action(
            self.controller.stop_hosting,
            busy_message="Stopping hosting...",
            action_kind="host_warm",
            action=True,
        )

    def _restart_hosting_async(self) -> None:
        self._run_async_state_action(
            self.controller.restart_hosting,
            busy_message="Restarting hosting and refreshing warm state...",
            action_kind="host_warm",
            action=True,
        )

    def _apply_state_with_scroll_restore(self, state: GuiShellState, previous_value: int) -> None:
        self._apply_state(state)
        self.scroll_area.verticalScrollBar().setValue(previous_value)

    @staticmethod
    def _host_card_expiry_text(state: GuiShellState) -> str:
        for detail in state.hosting_warm_details:
            if not detail.startswith("Expires at: "):
                continue
            expires_raw = detail.removeprefix("Expires at: ").strip()
            try:
                expires_at = datetime.fromisoformat(expires_raw.replace("Z", "+00:00"))
            except ValueError:
                return expires_raw
            remaining_seconds = int((expires_at - datetime.now(timezone.utc)).total_seconds())
            if remaining_seconds <= 0:
                return "expired"
            if remaining_seconds < 60:
                return f"{remaining_seconds}s"
            minutes = remaining_seconds // 60
            return f"{minutes}m"

        warm_state = state.hosting_warm_state_badge.upper()
        if warm_state == "WARMING":
            return "warming"
        if warm_state in {"COLD", "NO MODEL"}:
            return "not loaded"
        if warm_state == "WARM_FAILED":
            return "unavailable"
        return "unknown"

    def _apply_host_toggle_style(self, *, hosting_enabled: bool) -> None:
        if hosting_enabled:
            self.host_toggle_button.setStyleSheet(
                """
                QPushButton {
                    background-color: #b91c1c;
                    color: white;
                    border: 1px solid #ef4444;
                    border-radius: 8px;
                    font-weight: 700;
                    padding: 8px 18px;
                }
                QPushButton:disabled {
                    background-color: #3f3f46;
                    color: #a1a1aa;
                    border: 1px solid #52525b;
                }
                """
            )
            return
        self.host_toggle_button.setStyleSheet(
            """
            QPushButton {
                background-color: #166534;
                color: white;
                border: 1px solid #22c55e;
                border-radius: 8px;
                font-weight: 700;
                padding: 8px 18px;
            }
            QPushButton:disabled {
                background-color: #3f3f46;
                color: #a1a1aa;
                border: 1px solid #52525b;
            }
            """
        )

    def _run_async_state_action(
        self,
        fn,
        *,
        on_success=None,
        busy_message: str,
        action_kind: str = "",
        action: bool,
    ) -> None:
        if action and self._action_in_flight:
            return
        if not action and (self._action_in_flight or self._poll_in_flight):
            return

        if action:
            self._action_in_flight = True
            self._ui_notice = busy_message
            self._active_action_kind = action_kind
            if self._latest_state is not None:
                self._apply_state(self._latest_state)
        else:
            self._poll_in_flight = True

        task = _AsyncGuiTask(fn)
        self._active_tasks.append(task)
        task.signals.completed.connect(
            lambda state, task=task, on_success=on_success, action=action: self._complete_async_state_action(
                task,
                state,
                on_success=on_success,
                action=action,
            )
        )
        task.signals.failed.connect(
            lambda message, task=task, action=action: self._fail_async_state_action(
                task,
                message,
                action=action,
            )
        )
        self._thread_pool.start(task)

    def _complete_async_state_action(self, task: _AsyncGuiTask, state: GuiShellState, *, on_success, action: bool) -> None:
        self._discard_task(task)
        if action:
            self._action_in_flight = False
            self._ui_notice = ""
            self._active_action_kind = ""
        else:
            self._poll_in_flight = False

        if on_success is not None:
            on_success(state)
        else:
            self._apply_state(state)

    def _fail_async_state_action(self, task: _AsyncGuiTask, message: str, *, action: bool) -> None:
        self._discard_task(task)
        if action:
            self._action_in_flight = False
            self._active_action_kind = ""
        else:
            self._poll_in_flight = False
        self._ui_notice = f"Action failed: {message}"
        self._apply_state(self.controller.refresh())

    def _discard_task(self, task: _AsyncGuiTask) -> None:
        if task in self._active_tasks:
            self._active_tasks.remove(task)

    def _apply_state(self, state: GuiShellState) -> None:
        self._latest_state = state
        self.title_label.setText(state.home_title)
        self.subtitle_label.setText(state.home_subtitle)

        footer_parts = [
            f"Modulo {'online' if state.connected_to_modulo else 'offline'}",
            f"Hosting {'enabled' if state.hosting_enabled else 'disabled'}",
            f"Worker {state.worker_status_badge.lower()}",
        ]
        if self._ui_notice:
            footer_parts.append(self._ui_notice)
        self.status_strip.setText(
            " | ".join(footer_parts)
        )

        self.connect_button.setText(state.openclaw_action_label)
        controls_enabled = not self._action_in_flight
        self.connect_button.setEnabled(state.connect_action_enabled and controls_enabled)
        self.apply_openclaw_button.setText(state.openclaw_plan_apply_label)
        self.apply_openclaw_button.setEnabled(state.openclaw_plan_apply_enabled and controls_enabled)
        self.hosting_model_combo.setEnabled(state.hosting_setup_action_enabled and controls_enabled)
        self.host_toggle_button.setText("Stop" if state.hosting_enabled else "Host")
        self._apply_host_toggle_style(hosting_enabled=state.hosting_enabled)
        self.host_toggle_button.setEnabled(
            (state.start_action_enabled or state.stop_action_enabled) and controls_enabled
        )
        self.restart_button.setEnabled(state.restart_action_enabled and controls_enabled)
        self.smoke_button.setEnabled(state.smoke_action_enabled and controls_enabled)
        host_busy = self._action_in_flight and self._active_action_kind == "host_warm"
        smoke_busy = self._action_in_flight and self._active_action_kind == "smoke_test"
        self.host_activity_label.setText(
            "Working: preparing host model and refreshing warm state..." if host_busy else ""
        )
        self.host_activity_label.setVisible(host_busy)
        self.host_activity_bar.setVisible(host_busy)
        self.smoke_activity_label.setText(
            "Working: running constrained smoke probe..." if smoke_busy else ""
        )
        self.smoke_activity_label.setVisible(smoke_busy)
        self.smoke_activity_bar.setVisible(smoke_busy)

        host_state_badge = (
            "Host: Active"
            if state.hosting_enabled and state.worker_healthy
            else "Host: Attention"
            if state.hosting_enabled
            else "Host: Idle"
        )
        self.host_state_badge_label.setText(host_state_badge)
        self.host_state_summary_label.setText("")
        selected_model_text = (
            self.hosting_model_combo.currentText()
            or state.hosting_selected_model_id
            or "No model selected"
        )
        self.host_card_model_value.setText(
            "\n".join(
                (
                    f"Model: {selected_model_text}",
                    f"State: {state.hosting_warm_state_badge.title()}",
                    f"Host: {state.hosting_mode_badge}",
                    f"Expires: {self._host_card_expiry_text(state)}",
                )
            )
        )

        self.openclaw_status_label.setText(
            f"Status: {state.openclaw_status_badge}"
        )
        self.openclaw_summary_label.setText(state.openclaw_summary)
        next_steps = "\n".join(f"- {step}" for step in state.openclaw_next_steps)
        self.openclaw_guidance_label.setText(
            f"{state.openclaw_guidance_badge}: {state.openclaw_guidance_summary}\n{next_steps}"
        )
        self.openclaw_plan_summary_label.setText(state.openclaw_plan_summary)
        self.buyer_model_notice_label.setText(
            "Model selection is a separate step. OpenClaw routing only matters after a model "
            "has been chosen, and that selector is not implemented in the client yet."
        )
        self.buyer_platform_summary_label.setText(state.buyer_platform_summary)
        self.buyer_account_summary_label.setText(state.buyer_account_summary)
        self.buyer_credits_label.setText(f"Credits: {state.buyer_credits_summary}")
        self.buyer_config_label.setText(f"Use config: {state.buyer_config_summary}")
        self.buyer_network_models_box.setPlainText("\n".join(state.buyer_network_models))
        self.buyer_cloud_models_box.setPlainText("\n".join(state.buyer_cloud_models))
        self.openclaw_details_box.setPlainText(
            f"{state.openclaw_details}\n\n{state.openclaw_safety_note}"
        )
        plan_lines = "\n".join(f"- {line}" for line in state.openclaw_plan_changes)
        self.openclaw_plan_box.setPlainText(
            f"{state.openclaw_plan_details}\n\nPlanned changes:\n{plan_lines or '- None'}"
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

        self.hosting_mode_label.setText(f"Host: {state.hosting_mode_badge}")
        self.hosting_warm_state_label.setText(f"State: {state.hosting_warm_state_badge}")
        self.hosting_warm_summary_label.setText(state.hosting_warm_summary)
        model_detail_lines = []
        runtime_detail_lines = []
        for detail in state.hosting_warm_details:
            if detail.startswith(
                (
                    "Loaded model:",
                    "Expires at:",
                    "VRAM:",
                    "Loaded size:",
                    "Context length:",
                    "Family:",
                    "Parameters:",
                    "Quantization:",
                )
            ):
                model_detail_lines.append(detail)
            else:
                runtime_detail_lines.append(detail)
        runtime_detail_lines.extend(
            (
                f"Execution path: {state.execution_mode_badge}",
                state.execution_summary,
                f"Ollama: {state.ollama_status_badge}",
                state.ollama_summary,
                state.ollama_inventory_summary,
                f"Readiness: {state.hosting_readiness_badge}",
                state.hosting_preflight_summary,
            )
        )
        if state.hosting_preflight_reason:
            runtime_detail_lines.append(f"Why blocked: {state.hosting_preflight_reason}")
        supported_installed = len(state.hosting_supported_installed_model_ids)
        supported_missing = len(state.hosting_supported_missing_model_ids)
        unsupported_installed = len(state.hosting_unsupported_installed_model_ids)
        runtime_detail_lines.append(
            "Inventory: "
            f"{supported_installed} supported installed, "
            f"{supported_missing} supported missing, "
            f"{unsupported_installed} installed outside the curated catalog."
        )
        self.host_runtime_details_label.setText("\n".join(line for line in runtime_detail_lines if line))
        self.hosting_warm_details_label.setText(
            "\n".join(model_detail_lines) or "No active loaded-model details are available yet."
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
