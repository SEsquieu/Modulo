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
        QLineEdit,
        QMainWindow,
        QProgressBar,
        QPushButton,
        QPlainTextEdit,
        QScrollArea,
        QSizePolicy,
        QTabWidget,
        QTreeWidget,
        QTreeWidgetItem,
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
        self._use_model_tree_expanded_keys: set[str] = set()
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
        self.footer_status_label = QLabel()
        self.footer_status_label.setTextFormat(Qt.TextFormat.RichText)
        self.footer_status_label.setStyleSheet("font-size: 13px;")
        self.footer_notice_label = QLabel()
        self.footer_notice_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.footer_notice_label.setStyleSheet("color: #7ee787; font-size: 13px;")

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
        self.smoke_details_box.setMaximumHeight(120)
        self.smoke_details_box.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        self.diagnostics_summary_label = QLabel()
        self.diagnostics_summary_label.setWordWrap(True)
        self.diagnostics_details_box = QPlainTextEdit()
        self.diagnostics_details_box.setReadOnly(True)
        self.diagnostics_details_box.setMinimumHeight(100)
        self.diagnostics_details_box.setMaximumHeight(100)
        self.diagnostics_details_box.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        self.continuity_summary_label = QLabel()
        self.continuity_summary_label.setWordWrap(True)
        self.route_trace_summary_label = QLabel()
        self.route_trace_summary_label.setWordWrap(True)
        self.route_trace_result_label = QLabel()
        self.route_trace_details_box = QPlainTextEdit()
        self.route_trace_details_box.setReadOnly(True)
        self.route_trace_details_box.setMinimumHeight(120)
        self.route_trace_details_box.setMaximumHeight(140)
        self.route_trace_details_box.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        self.activity_box = QPlainTextEdit()
        self.activity_box.setReadOnly(True)
        self.activity_box.setMinimumHeight(110)
        self.activity_box.setMaximumHeight(110)
        self.activity_box.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        self.debug_state_badge_label = QLabel()
        self.debug_state_badge_label.setStyleSheet("font-size: 18px; font-weight: 700;")
        self.debug_summary_label = QLabel()
        self.debug_summary_label.setWordWrap(True)
        self.debug_platform_value = QLabel()
        self.debug_platform_value.setWordWrap(True)
        self.debug_target_url_input = QLineEdit()
        self.debug_target_url_input.setPlaceholderText("http://REMOTE_HOST:PORT")
        self.debug_private_network_input = QLineEdit()
        self.debug_private_network_input.setPlaceholderText("private-network-id")
        self.debug_apply_target_button = QPushButton("Apply Target")
        self.debug_apply_target_button.clicked.connect(self._apply_debug_target)
        self.debug_probe_button = QPushButton("Run Debug Probe")
        self.debug_probe_button.clicked.connect(self._run_debug_probe)
        self.debug_topology_box = QPlainTextEdit()
        self.debug_topology_box.setReadOnly(True)
        self.debug_topology_box.setMinimumHeight(110)
        self.debug_topology_box.setMaximumHeight(110)
        self.debug_worker_command_box = QPlainTextEdit()
        self.debug_worker_command_box.setReadOnly(True)
        self.debug_worker_command_box.setMinimumHeight(120)
        self.debug_request_command_box = QPlainTextEdit()
        self.debug_request_command_box.setReadOnly(True)
        self.debug_request_command_box.setMinimumHeight(170)
        self.debug_probe_summary_label = QLabel()
        self.debug_probe_summary_label.setWordWrap(True)
        self.debug_probe_result_label = QLabel()
        self.debug_probe_details_box = QPlainTextEdit()
        self.debug_probe_details_box.setReadOnly(True)
        self.debug_probe_details_box.setMinimumHeight(100)
        self.diagnostics_state_badge_label = QLabel()
        self.diagnostics_state_badge_label.setStyleSheet("font-size: 18px; font-weight: 700;")
        self.diagnostics_card_value = QLabel()
        self.diagnostics_card_value.setWordWrap(True)
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
        self.use_state_badge_label = QLabel()
        self.use_state_badge_label.setStyleSheet("font-size: 18px; font-weight: 700;")
        self.use_summary_label = QLabel()
        self.use_summary_label.setWordWrap(True)
        combo_font = QFont("Consolas", 11)
        self.use_model_button = QPushButton("Choose model...")
        self.use_model_button.setFont(combo_font)
        self.use_model_button.setStyleSheet("text-align: left; padding: 6px 10px;")
        self.use_model_button.clicked.connect(self._toggle_use_model_picker)
        self._use_model_picker_popup = QFrame(self, Qt.WindowType.Popup)
        self._use_model_picker_popup.setObjectName("UseModelPicker")
        self._use_model_picker_popup.setFrameShape(QFrame.Shape.Box)
        self._use_model_picker_popup.setLineWidth(2)
        self._use_model_picker_popup.setMinimumWidth(360)
        self._use_model_picker_popup.setMaximumHeight(360)
        self._use_model_picker_popup_layout = QVBoxLayout()
        self._use_model_picker_popup_layout.setContentsMargins(8, 8, 8, 8)
        self._use_model_picker_popup_layout.setSpacing(6)
        self.use_model_tree = QTreeWidget()
        self.use_model_tree.setHeaderHidden(True)
        self.use_model_tree.setUniformRowHeights(True)
        self.use_model_tree.setIndentation(18)
        self.use_model_tree.itemClicked.connect(self._handle_use_model_tree_click)
        self._use_model_picker_popup_layout.addWidget(self.use_model_tree)
        self._use_model_picker_popup.setLayout(self._use_model_picker_popup_layout)
        self.use_card_value = QLabel()
        self.use_card_value.setWordWrap(True)
        self.use_route_health_label = QLabel()
        self.use_route_health_label.setTextFormat(Qt.TextFormat.RichText)
        self.use_route_health_summary_label = QLabel()
        self.use_route_health_summary_label.setWordWrap(True)
        self.use_mount_status_label = QLabel()
        self.use_mount_status_label.setTextFormat(Qt.TextFormat.RichText)
        self.use_mount_status_summary_label = QLabel()
        self.use_mount_status_summary_label.setWordWrap(True)
        self.mount_shape_combo = QComboBox()
        self.mount_shape_combo.setFont(combo_font)
        self.mount_shape_combo.view().setFont(combo_font)
        self.mount_shape_combo.currentIndexChanged.connect(self._apply_selected_mount_shape)
        self.mount_consumer_combo = QComboBox()
        self.mount_consumer_combo.setFont(combo_font)
        self.mount_consumer_combo.view().setFont(combo_font)
        self.mount_consumer_combo.currentIndexChanged.connect(self._apply_selected_mount_consumer)
        self.mount_consumer_summary_label = QLabel()
        self.mount_consumer_summary_label.setWordWrap(True)
        self.mount_details_label = QLabel()
        self.mount_details_label.setWordWrap(True)
        self.use_route_details_label = QLabel()
        self.use_route_details_label.setWordWrap(True)
        self.use_local_models_label = QLabel()
        self.use_local_models_label.setWordWrap(True)
        self.use_private_models_label = QLabel()
        self.use_private_models_label.setWordWrap(True)
        self.use_public_models_label = QLabel()
        self.use_public_models_label.setWordWrap(True)
        self.use_cloud_models_label = QLabel()
        self.use_cloud_models_label.setWordWrap(True)
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
        self.apply_continue_button = QPushButton("Apply Continue Mount")
        self.apply_continue_button.clicked.connect(self._apply_continue_mount)
        self.rollback_continue_button = QPushButton("Rollback Continue Mount")
        self.rollback_continue_button.clicked.connect(self._rollback_continue_mount)

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
        use_box.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Maximum,
        )
        use_layout = QVBoxLayout()
        use_header_row = QHBoxLayout()
        use_header_row.addWidget(self.use_state_badge_label, 1)
        use_header_row.addStretch(1)
        use_layout.addLayout(use_header_row)
        use_model_row = QHBoxLayout()
        use_model_row.addWidget(QLabel("Model"))
        use_model_row.addWidget(self.use_model_button, 1)
        use_layout.addLayout(use_model_row)
        use_layout.addWidget(self._build_host_card("Active Route", self.use_card_value))
        self.use_detail_tabs = QTabWidget()
        self.use_detail_tabs.addTab(self._build_use_sources_page(), "Sources")
        self.use_detail_tabs.addTab(self._build_use_mount_page(), "Mount")
        self.use_detail_tabs.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Maximum,
        )
        use_layout.addWidget(self.use_detail_tabs)
        use_box.setLayout(use_layout)

        diagnostics_box = QGroupBox("Diagnostics")
        diagnostics_box.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Maximum,
        )
        diagnostics_layout = QVBoxLayout()
        diagnostics_header_row = QHBoxLayout()
        diagnostics_header_row.addWidget(self.diagnostics_state_badge_label, 1)
        diagnostics_header_row.addWidget(self.smoke_button, 0)
        diagnostics_layout.addLayout(diagnostics_header_row)
        diagnostics_layout.addWidget(self.smoke_activity_label)
        diagnostics_layout.addWidget(self.smoke_activity_bar)
        diagnostics_layout.addWidget(self._build_host_card("Latest Check", self.diagnostics_card_value))
        self.diagnostics_detail_tabs = QTabWidget()
        self.diagnostics_detail_tabs.addTab(self._build_diagnostics_smoke_page(), "Smoke")
        self.diagnostics_detail_tabs.addTab(self._build_diagnostics_route_page(), "Route")
        self.diagnostics_detail_tabs.addTab(self._build_diagnostics_activity_page(), "Activity")
        self.diagnostics_detail_tabs.addTab(self._build_diagnostics_errors_page(), "Errors")
        self.diagnostics_detail_tabs.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Maximum,
        )
        diagnostics_layout.addWidget(self.diagnostics_detail_tabs)
        diagnostics_box.setLayout(diagnostics_layout)

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

        debug_tab = QWidget()
        debug_tab_layout = QVBoxLayout()
        debug_tab_layout.setContentsMargins(0, 0, 0, 0)
        debug_tab_layout.setSpacing(12)
        debug_tab_layout.addWidget(self._build_debug_box())
        debug_tab_layout.addStretch(1)
        debug_tab.setLayout(debug_tab_layout)

        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(use_tab, "Use")
        self.tab_widget.addTab(host_tab, "Host")
        self.tab_widget.addTab(diagnostics_tab, "Diagnostics")
        self.tab_widget.addTab(debug_tab, "Debug")
        self.tab_widget.currentChanged.connect(self._refresh_active_tab_layout)

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
        footer_row = QHBoxLayout()
        footer_row.setContentsMargins(12, 6, 12, 6)
        footer_row.setSpacing(12)
        footer_row.addWidget(self.footer_status_label, 0)
        footer_row.addStretch(1)
        footer_row.addWidget(self.footer_notice_label, 0)
        container_layout.addLayout(footer_row)
        container.setLayout(container_layout)
        self.setCentralWidget(container)

        self._apply_window_sizing()

        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(1000)
        self._poll_timer.timeout.connect(self._poll_state)
        self._poll_timer.start()

        self._apply_state(self.controller.refresh())
        self._refresh_active_tab_layout()

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
            """
            QFrame {
                background-color: #0b130e;
                border: 1px solid #1f6b39;
                border-radius: 4px;
                padding: 6px;
            }
            """
        )
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)
        title_label = QLabel(title)
        title_label.setStyleSheet(
            "font-size: 10px; color: #5fd98f; letter-spacing: 1px; text-transform: uppercase;"
        )
        value_label.setStyleSheet("color: #d7ffe3; background: transparent;")
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

    def _build_use_mount_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        mount_shape_row = QHBoxLayout()
        mount_shape_row.addWidget(self._build_section_label("Shape"))
        mount_shape_row.addWidget(self.mount_shape_combo, 1)
        layout.addLayout(mount_shape_row)
        mount_consumer_row = QHBoxLayout()
        mount_consumer_row.addWidget(self._build_section_label("Consumer"))
        mount_consumer_row.addWidget(self.mount_consumer_combo, 1)
        layout.addLayout(mount_consumer_row)
        layout.addWidget(self.mount_consumer_summary_label)
        layout.addWidget(self.mount_details_label)
        layout.addWidget(self.openclaw_status_label)
        layout.addWidget(self.openclaw_summary_label)
        layout.addWidget(self.openclaw_guidance_label)
        layout.addWidget(self.openclaw_plan_summary_label)
        route_actions = QHBoxLayout()
        route_actions.addWidget(self.connect_button, 0)
        route_actions.addWidget(self.apply_openclaw_button, 0)
        route_actions.addWidget(self.apply_continue_button, 0)
        route_actions.addWidget(self.rollback_continue_button, 0)
        route_actions.addStretch(1)
        layout.addLayout(route_actions)
        layout.addWidget(self.openclaw_details_box)
        layout.addWidget(self.openclaw_plan_box)
        layout.addStretch(1)
        page.setLayout(layout)
        return page

    def _build_use_sources_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        layout.addWidget(self._build_section_label("Local"))
        layout.addWidget(self.use_local_models_label)
        layout.addWidget(self._build_section_label("Private"))
        layout.addWidget(self.use_private_models_label)
        layout.addWidget(self._build_section_label("Public"))
        layout.addWidget(self.use_public_models_label)
        layout.addWidget(self._build_section_label("Cloud"))
        layout.addWidget(self.use_cloud_models_label)
        layout.addStretch(1)
        page.setLayout(layout)
        return page

    def _build_diagnostics_smoke_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        layout.addWidget(self.smoke_result_label)
        layout.addWidget(self.smoke_summary_label)
        layout.addWidget(self.smoke_details_box)
        layout.addStretch(1)
        page.setLayout(layout)
        return page

    def _build_diagnostics_route_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        layout.addWidget(self.route_trace_result_label)
        layout.addWidget(self.route_trace_summary_label)
        layout.addWidget(self.route_trace_details_box)
        layout.addStretch(1)
        page.setLayout(layout)
        return page

    def _build_diagnostics_activity_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        layout.addWidget(self.continuity_summary_label)
        layout.addWidget(self.activity_box)
        layout.addStretch(1)
        page.setLayout(layout)
        return page

    def _build_diagnostics_errors_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        layout.addWidget(self.diagnostics_summary_label)
        layout.addWidget(self.diagnostics_details_box)
        layout.addStretch(1)
        page.setLayout(layout)
        return page

    def _build_debug_box(self) -> QGroupBox:
        debug_box = QGroupBox("Debug")
        debug_box.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Maximum,
        )
        layout = QVBoxLayout()
        layout.addWidget(self.debug_state_badge_label)
        layout.addWidget(self.debug_summary_label)
        layout.addWidget(self._build_host_card("Platform", self.debug_platform_value))
        layout.addWidget(self._build_debug_page())
        debug_box.setLayout(layout)
        return debug_box

    def _build_debug_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout()
        target_row = QHBoxLayout()
        target_row.addWidget(self._build_section_label("Target URL"))
        target_row.addWidget(self.debug_target_url_input, 1)
        target_row.addWidget(self.debug_apply_target_button, 0)
        layout.addLayout(target_row)
        network_row = QHBoxLayout()
        network_row.addWidget(self._build_section_label("Private Network"))
        network_row.addWidget(self.debug_private_network_input, 1)
        network_row.addWidget(self.debug_probe_button, 0)
        layout.addLayout(network_row)
        layout.addWidget(self._build_section_label("Current Topology"))
        layout.addWidget(self.debug_topology_box)
        layout.addWidget(self._build_section_label("Remote Worker Command"))
        layout.addWidget(self.debug_worker_command_box)
        layout.addWidget(self._build_section_label("Request Command"))
        layout.addWidget(self.debug_request_command_box)
        layout.addWidget(self._build_section_label("Probe Result"))
        layout.addWidget(self.debug_probe_result_label)
        layout.addWidget(self.debug_probe_summary_label)
        layout.addWidget(self.debug_probe_details_box)
        layout.addStretch(1)
        page.setLayout(layout)
        return page

    @staticmethod
    def _build_section_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet("font-size: 10px; color: #5fd98f; letter-spacing: 1px;")
        return label

    def _apply_window_sizing(self) -> None:
        screen = self.screen() or QApplication.primaryScreen()
        if screen is None:
            return
        available = screen.availableGeometry()
        target_width = min(920, max(720, available.width() - 120))
        target_height = min(760, max(520, available.height() - 120))
        self.resize(target_width, target_height)

    def _refresh_active_tab_layout(self) -> None:
        root = self.scroll_area.widget()
        if root is None:
            return
        current_tab = self.tab_widget.currentWidget()
        if current_tab is not None:
            current_tab.adjustSize()
        self.tab_widget.adjustSize()
        root.adjustSize()
        scrollbar = self.scroll_area.verticalScrollBar()
        scrollbar.setValue(min(scrollbar.value(), scrollbar.maximum()))

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

    def _persist_debug_target_url(self) -> None:
        target_url = self.debug_target_url_input.text().strip()
        if self._latest_state is not None and target_url == self._latest_state.debug_target_url:
            return
        self._apply_state(self.controller.set_debug_target_url(target_url))

    def _persist_debug_private_network_id(self) -> None:
        private_network_id = self.debug_private_network_input.text().strip()
        if (
            self._latest_state is not None
            and private_network_id == self._latest_state.debug_private_network_id
        ):
            return
        self._apply_state(self.controller.set_debug_private_network_id(private_network_id))

    def _apply_debug_target(self) -> None:
        self._persist_debug_target_url()
        self._persist_debug_private_network_id()

    def _run_debug_probe(self) -> None:
        self._run_async_state_action(
            self.controller.run_debug_probe,
            busy_message="Running debug network probe...",
            action_kind="debug_probe",
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

    def _apply_continue_mount(self) -> None:
        self._run_async_state_action(
            self.controller.apply_continue_mount,
            busy_message="Applying Continue mount...",
            action_kind="mount_apply",
            action=True,
        )

    def _rollback_continue_mount(self) -> None:
        self._run_async_state_action(
            self.controller.rollback_continue_mount,
            busy_message="Rolling back Continue mount...",
            action_kind="mount_apply",
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

    def _apply_selected_use_model(self, model_id: str) -> None:
        if not model_id:
            return
        if self._latest_state is not None and model_id == self._latest_state.use_selected_model_id:
            self._use_model_picker_popup.hide()
            return
        self._use_model_picker_popup.hide()
        self._apply_state(self.controller.select_use_model(model_id))

    def _apply_selected_mount_shape(self) -> None:
        shape_id = self.mount_shape_combo.currentData()
        if not isinstance(shape_id, str):
            return
        if self._latest_state is not None and shape_id == self._latest_state.mount_selected_shape_id:
            return
        self._apply_state(self.controller.select_mount_shape(shape_id))

    def _apply_selected_mount_consumer(self) -> None:
        consumer_id = self.mount_consumer_combo.currentData()
        if not isinstance(consumer_id, str):
            return
        if self._latest_state is not None and consumer_id == self._latest_state.mount_selected_consumer_id:
            return
        self._apply_state(self.controller.select_mount_consumer(consumer_id))

    def _toggle_use_model_picker(self) -> None:
        if self._use_model_picker_popup.isVisible():
            self._use_model_picker_popup.hide()
            return
        self._show_use_model_picker()

    def _show_use_model_picker(self) -> None:
        row_height = self.use_model_tree.sizeHintForRow(0)
        if row_height <= 0:
            row_height = 22
        self._use_model_picker_popup.resize(
            max(self.use_model_button.width(), 360),
            min(360, max(220, row_height * 10 + 24)),
        )
        popup_pos = self.use_model_button.mapToGlobal(self.use_model_button.rect().bottomLeft())
        self._use_model_picker_popup.move(popup_pos)
        self._use_model_picker_popup.show()
        self.use_model_tree.setFocus()

    def _handle_use_model_tree_click(self, item: QTreeWidgetItem, column: int) -> None:
        del column
        model_id = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(model_id, str) and model_id:
            self._apply_selected_use_model(model_id)
            return
        item.setExpanded(not item.isExpanded())
        self._remember_use_model_tree_expansion_state()

    def _remember_use_model_tree_expansion_state(self) -> None:
        expanded_keys: set[str] = set()

        def visit(item: QTreeWidgetItem) -> None:
            key = item.data(0, Qt.ItemDataRole.UserRole + 1)
            if item.childCount() and item.isExpanded() and isinstance(key, str) and key:
                expanded_keys.add(key)
            for index in range(item.childCount()):
                visit(item.child(index))

        for index in range(self.use_model_tree.topLevelItemCount()):
            visit(self.use_model_tree.topLevelItem(index))
        self._use_model_tree_expanded_keys = expanded_keys

    def _rebuild_use_model_tree(self, state: GuiShellState) -> None:
        self._remember_use_model_tree_expansion_state()
        self.use_model_tree.clear()
        selected_item: QTreeWidgetItem | None = None
        expandable_items: list[tuple[QTreeWidgetItem, str]] = []
        for source in state.use_model_menu_sources:
            source_item = QTreeWidgetItem([source.source_label])
            source_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            source_key = f"source:{source.source_label}"
            source_item.setData(0, Qt.ItemDataRole.UserRole + 1, source_key)
            self.use_model_tree.addTopLevelItem(source_item)
            expandable_items.append((source_item, source_key))
            source_item.setExpanded(
                source_key in self._use_model_tree_expanded_keys or not self._use_model_tree_expanded_keys
            )
            for scope in source.scopes:
                scope_item = QTreeWidgetItem([scope.scope_label])
                scope_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                scope_key = f"{source_key}/scope:{scope.scope_label}"
                scope_item.setData(0, Qt.ItemDataRole.UserRole + 1, scope_key)
                source_item.addChild(scope_item)
                expandable_items.append((scope_item, scope_key))
                scope_item.setExpanded(
                    scope_key in self._use_model_tree_expanded_keys or not self._use_model_tree_expanded_keys
                )
                for model in scope.models:
                    model_item = QTreeWidgetItem([model.label])
                    model_item.setData(0, Qt.ItemDataRole.UserRole, model.model_id)
                    model_item.setData(0, Qt.ItemDataRole.UserRole + 1, f"{scope_key}/model:{model.model_id}")
                    scope_item.addChild(model_item)
                    if model.model_id == state.use_selected_model_id:
                        selected_item = model_item
        if selected_item is not None:
            self.use_model_tree.setCurrentItem(selected_item)
        if self._use_model_tree_expanded_keys:
            for item, key in expandable_items:
                item.setExpanded(key in self._use_model_tree_expanded_keys)

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
                    background-color: #2a120f;
                    color: #ffb4a8;
                    border: 2px solid #b14d3f;
                    border-radius: 0px;
                    font-weight: 700;
                    font-size: 14px;
                    padding: 8px 18px;
                }
                QPushButton:hover {
                    background-color: #341613;
                    color: #ffd2ca;
                }
                QPushButton:disabled {
                    background-color: #101712;
                    color: #4d7658;
                    border: 2px solid #31503a;
                }
                """
            )
            return
        self.host_toggle_button.setStyleSheet(
            """
            QPushButton {
                background-color: #102015;
                color: #b8ff65;
                border: 2px solid #2bd66b;
                border-radius: 0px;
                font-weight: 700;
                font-size: 14px;
                padding: 8px 18px;
            }
            QPushButton:hover {
                background-color: #16291b;
                color: #e1ffae;
            }
            QPushButton:disabled {
                background-color: #101712;
                color: #4d7658;
                border: 2px solid #31503a;
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

        modulo_value = self._footer_status_html(
            "online" if state.connected_to_modulo else "offline",
            ok=state.connected_to_modulo,
        )
        hosting_value = self._footer_status_html(
            "enabled" if state.hosting_enabled else "disabled",
            ok=state.hosting_enabled,
        )
        worker_ok = state.worker_status_badge.upper() == "HEALTHY"
        worker_value = self._footer_status_html(
            state.worker_status_badge.lower(),
            ok=worker_ok,
        )
        self.footer_status_label.setText(
            "  |  ".join(
                (
                    f"Modulo: {modulo_value}",
                    f"Hosting: {hosting_value}",
                    f"Worker: {worker_value}",
                )
            )
        )
        self.footer_notice_label.setText(self._ui_notice)

        self.connect_button.setText(state.openclaw_action_label)
        controls_enabled = not self._action_in_flight
        self.connect_button.setEnabled(state.connect_action_enabled and controls_enabled)
        self.apply_openclaw_button.setText(state.openclaw_plan_apply_label)
        self.apply_openclaw_button.setEnabled(state.openclaw_plan_apply_enabled and controls_enabled)
        self.apply_continue_button.setText(state.mount_apply_label)
        self.apply_continue_button.setEnabled(state.mount_apply_enabled and controls_enabled)
        self.rollback_continue_button.setText(state.mount_rollback_label)
        self.rollback_continue_button.setEnabled(state.mount_rollback_enabled and controls_enabled)
        self.use_model_button.setEnabled(bool(state.use_available_model_ids) and controls_enabled)
        if not self.use_model_button.isEnabled():
            self._use_model_picker_popup.hide()
        self.hosting_model_combo.setEnabled(state.hosting_setup_action_enabled and controls_enabled)
        self.host_toggle_button.setText("Stop" if state.hosting_enabled else "Host")
        self._apply_host_toggle_style(hosting_enabled=state.hosting_enabled)
        self.host_toggle_button.setEnabled(
            (state.start_action_enabled or state.stop_action_enabled) and controls_enabled
        )
        self.restart_button.setEnabled(state.restart_action_enabled and controls_enabled)
        self.smoke_button.setEnabled(state.smoke_action_enabled and controls_enabled)
        self.debug_apply_target_button.setEnabled(controls_enabled)
        self.debug_probe_button.setEnabled(controls_enabled)
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

        diagnostics_badge = "Diagnostics: Ready"
        if state.smoke_test_result_label == "Fail" or state.last_worker_error:
            diagnostics_badge = "Diagnostics: Attention"
        elif state.smoke_test_result_label == "Not run yet":
            diagnostics_badge = "Diagnostics: Idle"
        self.diagnostics_state_badge_label.setText(diagnostics_badge)
        self.diagnostics_card_value.setText(
            "\n".join(
                (
                    "Probe: Constrained GUI smoke probe",
                    f"Result: {state.smoke_test_result_label}",
                    f"Path: {state.execution_mode_badge}",
                    f"Status: {state.diagnostics_summary}",
                )
            )
        )

        self.use_state_badge_label.setText(state.use_status_badge)
        self._rebuild_use_model_tree(state)
        self.use_model_button.setText(state.use_selected_model_label or "Choose model...")
        self.use_card_value.setText(self._use_route_card_html(state.use_route_details))

        self.use_route_health_label.setText(
            self._kv_status_html("Route", state.use_route_health_value)
        )
        self.use_route_health_summary_label.setText(state.use_route_health_summary)
        self.use_mount_status_label.setText(
            self._kv_status_html("Mount", state.use_mount_status_value)
        )
        self.use_mount_status_summary_label.setText(state.use_mount_status_summary)
        mount_shape_ids = tuple(
            self.mount_shape_combo.itemData(index)
            for index in range(self.mount_shape_combo.count())
        )
        if mount_shape_ids != state.mount_available_shape_ids:
            self.mount_shape_combo.blockSignals(True)
            self.mount_shape_combo.clear()
            for label, shape_id in zip(
                state.mount_available_shape_labels,
                state.mount_available_shape_ids,
                strict=False,
            ):
                self.mount_shape_combo.addItem(label, shape_id)
            self.mount_shape_combo.blockSignals(False)
        selected_mount_index = self.mount_shape_combo.findData(state.mount_selected_shape_id)
        if selected_mount_index >= 0 and selected_mount_index != self.mount_shape_combo.currentIndex():
            self.mount_shape_combo.blockSignals(True)
            self.mount_shape_combo.setCurrentIndex(selected_mount_index)
            self.mount_shape_combo.blockSignals(False)
        mount_consumer_ids = tuple(
            self.mount_consumer_combo.itemData(index)
            for index in range(self.mount_consumer_combo.count())
        )
        if mount_consumer_ids != state.mount_available_consumer_ids:
            self.mount_consumer_combo.blockSignals(True)
            self.mount_consumer_combo.clear()
            for label, consumer_id in zip(
                state.mount_available_consumer_labels,
                state.mount_available_consumer_ids,
                strict=False,
            ):
                self.mount_consumer_combo.addItem(label, consumer_id)
            self.mount_consumer_combo.blockSignals(False)
        selected_consumer_index = self.mount_consumer_combo.findData(state.mount_selected_consumer_id)
        if (
            selected_consumer_index >= 0
            and selected_consumer_index != self.mount_consumer_combo.currentIndex()
        ):
            self.mount_consumer_combo.blockSignals(True)
            self.mount_consumer_combo.setCurrentIndex(selected_consumer_index)
            self.mount_consumer_combo.blockSignals(False)
        self.mount_consumer_summary_label.setText(state.mount_consumer_summary)
        self.mount_details_label.setText("\n".join(state.mount_detail_lines))
        self.openclaw_status_label.setText(
            f"OpenClaw: {state.openclaw_status_badge}"
        )
        self.use_summary_label.setText(state.use_summary)
        self.openclaw_summary_label.setText(state.openclaw_summary)
        self.openclaw_guidance_label.setText(f"Next: {state.openclaw_guidance_summary}")
        self.openclaw_plan_summary_label.setText(state.openclaw_plan_summary)
        self.openclaw_details_box.setPlainText(state.openclaw_details)
        self.openclaw_plan_box.setPlainText(
            "\n".join(
                line
                for line in (
                    state.openclaw_plan_details,
                    *state.openclaw_plan_changes,
                )
                if line
            )
        )
        self.use_local_models_label.setText("\n".join(state.use_local_model_lines))
        self.use_private_models_label.setText("\n".join(state.use_private_model_lines))
        self.use_public_models_label.setText("\n".join(state.use_public_model_lines))
        self.use_cloud_models_label.setText("\n".join(state.buyer_cloud_models))
        openclaw_visible = state.mount_selected_consumer_id == "openclaw"
        continue_visible = state.mount_selected_consumer_id == "continue_vscode"
        for widget in (
            self.openclaw_status_label,
            self.openclaw_summary_label,
            self.openclaw_guidance_label,
            self.openclaw_plan_summary_label,
            self.connect_button,
            self.apply_openclaw_button,
            self.openclaw_details_box,
            self.openclaw_plan_box,
        ):
            widget.setVisible(openclaw_visible)
        for widget in (
            self.apply_continue_button,
            self.rollback_continue_button,
        ):
            widget.setVisible(continue_visible)

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
        self.route_trace_result_label.setText(f"Result: {state.route_trace_result_label}")
        self.route_trace_summary_label.setText(state.route_trace_summary)
        self.route_trace_details_box.setPlainText(state.route_trace_details)
        self.diagnostics_summary_label.setText(state.diagnostics_summary)
        self.diagnostics_details_box.setPlainText(state.diagnostics_details)
        self.continuity_summary_label.setText(state.continuity_summary)
        self.activity_box.setPlainText("\n".join(state.activity_lines))
        self.debug_state_badge_label.setText(state.debug_status_badge)
        self.debug_summary_label.setText(state.debug_summary)
        self.debug_platform_value.setText(
            "\n".join(
                (
                    f"Local platform URL: {state.debug_platform_url or 'Unavailable'}",
                    f"Active target URL: {state.debug_target_url or state.debug_platform_url or 'Unavailable'}",
                    f"Private network: {state.debug_private_network_id or 'unset'}",
                    f"Worker ID: {state.debug_worker_id or 'unset'}",
                    f"Model: {state.debug_model_id or 'unset'}",
                )
            )
        )
        if (
            not self.debug_target_url_input.hasFocus()
            and not self.debug_target_url_input.text().strip()
        ):
            self.debug_target_url_input.setText(state.debug_target_url)
        if not self.debug_private_network_input.hasFocus():
            self.debug_private_network_input.setText(state.debug_private_network_id)
        self.debug_topology_box.setPlainText("\n".join(state.debug_topology_lines))
        self.debug_worker_command_box.setPlainText(state.debug_worker_command)
        self.debug_request_command_box.setPlainText(state.debug_request_command)
        self.debug_probe_result_label.setText(f"Result: {state.debug_probe_result_label}")
        self.debug_probe_summary_label.setText(state.debug_probe_summary)
        self.debug_probe_details_box.setPlainText(state.debug_probe_details)

    @staticmethod
    def _footer_status_html(value: str, *, ok: bool) -> str:
        color = "#7ee787" if ok else "#ff7b72"
        return f"<b><span style='color: {color};'>{value}</span></b>"

    @staticmethod
    def _kv_status_html(label: str, value: str) -> str:
        normalized = value.strip().lower()
        if normalized in {"healthy", "ready"}:
            color = "#7ee787"
        elif normalized in {"staged", "local only"}:
            color = "#ffd866"
        else:
            color = "#ff7b72"
        return f"{label}: <b><span style='color: {color};'>{value}</span></b>"

    @staticmethod
    def _use_route_card_html(details: tuple[str, ...]) -> str:
        rows: list[str] = []
        for detail in details:
            if ": " not in detail:
                rows.append(detail)
                continue
            label, value = detail.split(": ", 1)
            if label == "Status":
                ok = value.strip().lower() == "ready"
                color = "#7ee787" if ok else "#ff7b72"
                rows.append(f"{label}: <b><span style='color: {color};'>{value}</span></b>")
                continue
            rows.append(f"{label}: <b>{value}</b>")
        return "<br>".join(rows)


def launch_gui(controller: GuiAppController | None = None) -> int:
    app = QApplication.instance() or QApplication([])
    window = ModuloMainWindow(controller or GuiAppController.build_default())
    window.show()
    return app.exec()
