"""
PySide6 GUI for Tripo AI 3D generation.

Usage:
    tripo-gui
"""

import sys
import os
import json
import logging
import threading
from pathlib import Path

try:
    from PySide6.QtCore import Qt, QSettings, Signal, QObject
    from PySide6.QtGui import QTextCursor, QPixmap, QDragEnterEvent, QDropEvent
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QLineEdit, QPushButton, QComboBox, QTextEdit, QFileDialog,
        QGroupBox, QFormLayout, QProgressBar, QMessageBox, QGridLayout,
        QTabWidget, QSpinBox,
    )
except ImportError:
    print("PySide6 not installed. Run: pip install PySide6")
    print("Or install with GUI support: pip install tripo-tools[gui]")
    sys.exit(1)

from .client import TripoClient, MODEL_VERSIONS, TEXTURE_OPTIONS

OUTPUT_FORMATS = ["glb", "fbx", "obj", "stl", "usdz"]
SUPPORTED_IMAGES = "Images (*.png *.jpg *.jpeg *.webp *.bmp);;All Files (*)"


class QSignalLogHandler(logging.Handler):
    """Logging handler that emits to a Qt signal."""
    def __init__(self, signal_fn):
        super().__init__()
        self.signal_fn = signal_fn
        self.setFormatter(logging.Formatter("[%(asctime)s] %(message)s", datefmt="%H:%M:%S"))

    def emit(self, record):
        try:
            msg = self.format(record)
            self.signal_fn(msg + "\n")
        except Exception:
            pass


class WorkerSignals(QObject):
    """Thread-safe signals for GUI updates."""
    progress = Signal(int, str)
    log = Signal(str)
    finished = Signal(bool, str)
    balance = Signal(str)


class ImageDropLabel(QLabel):
    """A label that accepts drag-and-drop images and click-to-browse."""
    image_set = Signal(str)

    def __init__(self, placeholder="Drop image here\nor click to browse", parent=None):
        super().__init__(placeholder, parent)
        self.placeholder = placeholder
        self.image_path = None

        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(160, 160)
        self.setMaximumHeight(200)
        self.setAcceptDrops(True)
        self.setCursor(Qt.PointingHandCursor)
        self._set_empty_style()

    def _set_empty_style(self):
        self.setStyleSheet(
            "QLabel { border: 2px dashed #555; border-radius: 8px; "
            "color: #888; background: #1e1e1e; font-size: 12px; padding: 8px; }"
        )

    def _set_filled_style(self):
        self.setStyleSheet(
            "QLabel { border: 2px solid #2d7d46; border-radius: 8px; "
            "background: #1e1e1e; padding: 4px; }"
        )

    def set_image(self, path):
        if path and os.path.isfile(path):
            self.image_path = path
            pixmap = QPixmap(path)
            scaled = pixmap.scaled(
                self.width() - 8, self.height() - 8,
                Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.setPixmap(scaled)
            self._set_filled_style()
            self.setToolTip(path)
            self.image_set.emit(path)
        else:
            self.clear_image()

    def clear_image(self):
        self.image_path = None
        self.setText(self.placeholder)
        self._set_empty_style()
        self.setToolTip("")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            path, _ = QFileDialog.getOpenFileName(self, "Select Image", "", SUPPORTED_IMAGES)
            if path:
                self.set_image(path)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if path:
                self.set_image(path)


class TripoGUI(QMainWindow):
    """Main Tripo GUI window."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tripo AI — 3D Generation")
        self.setMinimumSize(700, 750)
        self.settings = QSettings("ObsoleteRobot", "TripoGenerate")
        self.worker_thread = None
        self.signals = WorkerSignals()

        self.signals.progress.connect(self._on_progress)
        self.signals.log.connect(self._on_log)
        self.signals.finished.connect(self._on_finished)
        self.signals.balance.connect(self._on_balance)

        # Hook up tripo_tools logger to GUI log panel
        self._log_handler = QSignalLogHandler(self.signals.log.emit)
        tripo_logger = logging.getLogger("tripo_tools")
        tripo_logger.addHandler(self._log_handler)
        tripo_logger.setLevel(logging.DEBUG)

        self._build_ui()
        self._load_settings()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(8)

        # API Key row
        key_row = QHBoxLayout()
        key_row.addWidget(QLabel("API Key:"))
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("tsk_... (or set TRIPO_API_KEY env var)")
        self.api_key_input.setEchoMode(QLineEdit.Password)
        key_row.addWidget(self.api_key_input, 1)

        self.show_key_btn = QPushButton("Show")
        self.show_key_btn.setCheckable(True)
        self.show_key_btn.toggled.connect(self._toggle_key_visibility)
        key_row.addWidget(self.show_key_btn)

        self.balance_btn = QPushButton("Check Balance")
        self.balance_btn.clicked.connect(self._check_balance)
        key_row.addWidget(self.balance_btn)

        layout.addLayout(key_row)

        # Input Tabs
        self.input_tabs = QTabWidget()

        # Tab 1: Single Image
        single_tab = QWidget()
        single_layout = QVBoxLayout(single_tab)
        self.single_image = ImageDropLabel("Drop image here\nor click to browse")
        single_layout.addWidget(self.single_image)
        self.input_tabs.addTab(single_tab, "📷 Single Image")

        # Tab 2: Multiview
        multi_tab = QWidget()
        multi_layout = QVBoxLayout(multi_tab)
        
        multi_desc = QLabel("Add 4 turnaround images from different angles.")
        multi_desc.setStyleSheet("color: #888; font-size: 11px;")
        multi_layout.addWidget(multi_desc)

        self.multi_images = []
        grid = QGridLayout()
        grid.setSpacing(8)
        
        for i, label in enumerate(["Front", "Back", "Left", "Right"]):
            img = ImageDropLabel(f"{label}\n(click/drop)")
            img.setMinimumSize(120, 120)
            img.setMaximumHeight(140)
            self.multi_images.append(img)
            
            col_widget = QVBoxLayout()
            lbl = QLabel(label)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("color: #aaa; font-size: 11px;")
            col_widget.addWidget(lbl)
            col_widget.addWidget(img)
            grid.addLayout(col_widget, i // 2, i % 2)

        multi_layout.addLayout(grid)

        clear_btn = QPushButton("Clear All")
        clear_btn.clicked.connect(self._clear_multiview)
        multi_layout.addWidget(clear_btn, alignment=Qt.AlignRight)

        self.input_tabs.addTab(multi_tab, "🔄 Multiview")

        # Tab 3: Text Prompt
        text_tab = QWidget()
        text_layout = QVBoxLayout(text_tab)
        self.prompt_input = QTextEdit()
        self.prompt_input.setPlaceholderText(
            "Describe the 3D object you want to generate...\n\n"
            'e.g., "A weathered wooden barrel with iron bands"'
        )
        self.prompt_input.setMaximumHeight(120)
        text_layout.addWidget(self.prompt_input)
        self.input_tabs.addTab(text_tab, "✍️ Text Prompt")

        layout.addWidget(self.input_tabs)

        # Output Settings
        output_group = QGroupBox("Output")
        output_layout = QFormLayout(output_group)

        output_row = QHBoxLayout()
        self.output_path = QLineEdit()
        self.output_path.setPlaceholderText("Output file path")
        output_browse = QPushButton("Browse...")
        output_browse.clicked.connect(self._browse_output)
        output_row.addWidget(self.output_path, 1)
        output_row.addWidget(output_browse)
        output_layout.addRow("Save to:", output_row)

        options_row = QHBoxLayout()
        options_row.addWidget(QLabel("Format:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(OUTPUT_FORMATS)
        options_row.addWidget(self.format_combo)
        options_row.addSpacing(20)
        options_row.addWidget(QLabel("Timeout (s):"))
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(60, 1800)
        self.timeout_spin.setValue(600)
        options_row.addWidget(self.timeout_spin)
        options_row.addStretch()
        output_layout.addRow(options_row)

        layout.addWidget(output_group)

        # Advanced Options
        advanced_group = QGroupBox("Generation Options")
        advanced_layout = QFormLayout(advanced_group)

        # Model version
        self.model_version_combo = QComboBox()
        self.model_version_combo.addItem("Auto (latest)", None)
        for v in MODEL_VERSIONS:
            self.model_version_combo.addItem(v, v)
        advanced_layout.addRow("Model Version:", self.model_version_combo)

        # Texture quality
        self.texture_quality_combo = QComboBox()
        self.texture_quality_combo.addItem("standard", "standard")
        self.texture_quality_combo.addItem("detailed (4K)", "detailed")
        advanced_layout.addRow("Texture Quality:", self.texture_quality_combo)

        # Texture alignment
        self.texture_alignment_combo = QComboBox()
        self.texture_alignment_combo.addItem("Default", None)
        self.texture_alignment_combo.addItem("Original Image", "original_image")
        self.texture_alignment_combo.addItem("Geometry", "geometry")
        advanced_layout.addRow("Texture Alignment:", self.texture_alignment_combo)

        # Row with checkboxes
        checks_row = QHBoxLayout()

        from PySide6.QtWidgets import QCheckBox
        self.texture_check = QCheckBox("Texture")
        self.texture_check.setChecked(True)
        checks_row.addWidget(self.texture_check)

        self.pbr_check = QCheckBox("PBR Materials")
        self.pbr_check.setChecked(True)
        checks_row.addWidget(self.pbr_check)

        self.quad_check = QCheckBox("Quad Mesh")
        self.quad_check.setToolTip("Generate quad mesh (extra cost)")
        checks_row.addWidget(self.quad_check)

        self.auto_size_check = QCheckBox("Auto Size")
        self.auto_size_check.setToolTip("Scale to real-world dimensions")
        checks_row.addWidget(self.auto_size_check)

        checks_row.addStretch()
        advanced_layout.addRow(checks_row)

        # Seed and face limit row
        numbers_row = QHBoxLayout()
        numbers_row.addWidget(QLabel("Seed:"))
        self.seed_spin = QSpinBox()
        self.seed_spin.setRange(-1, 999999999)
        self.seed_spin.setValue(-1)
        self.seed_spin.setSpecialValueText("Random")
        self.seed_spin.setToolTip("-1 = random seed")
        numbers_row.addWidget(self.seed_spin)

        numbers_row.addSpacing(20)
        numbers_row.addWidget(QLabel("Face Limit:"))
        self.face_limit_spin = QSpinBox()
        self.face_limit_spin.setRange(0, 1000000)
        self.face_limit_spin.setValue(0)
        self.face_limit_spin.setSpecialValueText("Auto")
        self.face_limit_spin.setToolTip("0 = automatic")
        numbers_row.addWidget(self.face_limit_spin)
        numbers_row.addStretch()
        advanced_layout.addRow(numbers_row)

        layout.addWidget(advanced_group)

        # Generate Button
        self.generate_btn = QPushButton("🚀  Generate 3D Model")
        self.generate_btn.setMinimumHeight(44)
        self.generate_btn.setStyleSheet(
            "QPushButton { background-color: #6c3bd1; color: white; "
            "font-size: 14px; font-weight: bold; border-radius: 4px; }"
            "QPushButton:hover { background-color: #7d4ee0; }"
            "QPushButton:disabled { background-color: #555; color: #999; }"
        )
        self.generate_btn.clicked.connect(self._generate)
        layout.addWidget(self.generate_btn)

        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #aaa; font-size: 12px;")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.hide()
        layout.addWidget(self.status_label)

        # Log
        log_group = QGroupBox("Log")
        log_layout = QVBoxLayout(log_group)
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumHeight(160)
        self.log_output.setStyleSheet(
            "QTextEdit { background-color: #1e1e1e; color: #d4d4d4; "
            "font-family: 'Consolas', monospace; font-size: 12px; }"
        )
        log_layout.addWidget(self.log_output)
        layout.addWidget(log_group)

        self.statusBar().showMessage("Ready")

    def _get_api_key(self):
        key = self.api_key_input.text().strip()
        if not key:
            key = os.environ.get("TRIPO_API_KEY", "")
        return key

    def _toggle_key_visibility(self, checked):
        self.api_key_input.setEchoMode(QLineEdit.Normal if checked else QLineEdit.Password)
        self.show_key_btn.setText("Hide" if checked else "Show")

    def _browse_output(self):
        fmt = self.format_combo.currentText()
        path, _ = QFileDialog.getSaveFileName(self, "Save Output", "", f"3D Model (*.{fmt})")
        if path:
            if not path.lower().endswith(f".{fmt}"):
                path += f".{fmt}"
            self.output_path.setText(path)

    def _clear_multiview(self):
        for img in self.multi_images:
            img.clear_image()

    def _check_balance(self):
        api_key = self._get_api_key()
        if not api_key:
            QMessageBox.warning(self, "No API Key", "Enter your Tripo API key first.")
            return

        self.balance_btn.setEnabled(False)
        threading.Thread(target=self._balance_worker, args=(api_key,), daemon=True).start()

    def _balance_worker(self, api_key):
        try:
            client = TripoClient(api_key)
            balance = client.get_balance()
            self.signals.balance.emit(json.dumps(balance, indent=2))
        except Exception as e:
            self.signals.balance.emit(f"Error: {e}")

    def _on_balance(self, info):
        self.balance_btn.setEnabled(True)
        QMessageBox.information(self, "Tripo Balance", info)

    def _generate(self):
        api_key = self._get_api_key()
        if not api_key:
            QMessageBox.warning(self, "No API Key", "Enter your Tripo API key.")
            return

        output = self.output_path.text().strip()
        if not output:
            QMessageBox.warning(self, "No Output", "Set an output file path.")
            return

        fmt = self.format_combo.currentText()
        if not output.lower().endswith(f".{fmt}"):
            output += f".{fmt}"
            self.output_path.setText(output)

        timeout = self.timeout_spin.value()
        tab = self.input_tabs.currentIndex()

        if tab == 0:  # Single image
            img = self.single_image.image_path
            if not img:
                QMessageBox.warning(self, "No Image", "Select an image first.")
                return
            mode = "single"
            payload = {"image": img}
        elif tab == 1:  # Multiview
            images = [img.image_path for img in self.multi_images if img.image_path]
            if len(images) < 2:
                QMessageBox.warning(self, "Not Enough Images", "Need at least 2 images.")
                return
            mode = "multiview"
            payload = {"images": images}
        elif tab == 2:  # Text
            prompt = self.prompt_input.toPlainText().strip()
            if not prompt:
                QMessageBox.warning(self, "No Prompt", "Enter a text prompt.")
                return
            mode = "text"
            payload = {"prompt": prompt}

        self.log_output.clear()
        self._on_log(f"Mode: {mode}\nOutput: {output}\n\n")

        # Gather advanced options
        gen_options = {
            "model_version": self.model_version_combo.currentData(),
            "texture": self.texture_check.isChecked(),
            "pbr": self.pbr_check.isChecked(),
            "texture_quality": self.texture_quality_combo.currentData(),
            "texture_alignment": self.texture_alignment_combo.currentData(),
            "quad": self.quad_check.isChecked(),
            "auto_size": self.auto_size_check.isChecked(),
            "seed": self.seed_spin.value() if self.seed_spin.value() >= 0 else None,
            "face_limit": self.face_limit_spin.value() if self.face_limit_spin.value() > 0 else None,
        }

        self.generate_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_bar.show()
        self.status_label.show()

        self.worker_thread = threading.Thread(
            target=self._generate_worker,
            args=(api_key, mode, payload, output, fmt, timeout, gen_options),
            daemon=True,
        )
        self.worker_thread.start()
        self._save_settings()

    def _generate_worker(self, api_key, mode, payload, output, fmt, timeout, gen_options=None):
        try:
            opts = gen_options or {}

            # Log everything up front
            self.signals.log.emit(f"=== Tripo Debug Log ===\n")
            self.signals.log.emit(f"Mode: {mode}\n")
            self.signals.log.emit(f"Output: {output} (format: {fmt})\n")
            self.signals.log.emit(f"API Key: {api_key[:8]}...{api_key[-4:]}\n")
            self.signals.log.emit(f"Options: {json.dumps(opts, indent=2)}\n\n")

            if mode == "single":
                self.signals.log.emit(f"Image: {payload['image']}\n")
            elif mode == "multiview":
                self.signals.log.emit(f"Images: {payload['images']}\n")
            elif mode == "text":
                self.signals.log.emit(f"Prompt: {payload['prompt']}\n")

            client = TripoClient(api_key)

            def progress_callback(progress, status):
                self.signals.progress.emit(progress, status)

            if mode == "single":
                self.signals.log.emit("\nStarting image-to-3D...\n")
                client.image_to_3d(payload["image"], output, fmt, progress_callback, **opts)
            elif mode == "multiview":
                self.signals.log.emit(f"\nStarting multiview-to-3D ({len(payload['images'])} images)...\n")
                client.multiview_to_3d(payload["images"], output, fmt, progress_callback, **opts)
            elif mode == "text":
                self.signals.log.emit(f"\nStarting text-to-3D...\n")
                client.text_to_3d(payload["prompt"], output, fmt, progress_callback, **opts)

            self.signals.log.emit(f"\n✓ Saved: {output}\n")
            self.signals.finished.emit(True, output)

        except Exception as e:
            import traceback
            self.signals.log.emit(f"\n✗ ERROR: {e}\n")
            self.signals.log.emit(f"Traceback:\n{traceback.format_exc()}\n")
            self.signals.finished.emit(False, str(e))

    def _on_progress(self, percent, status):
        self.progress_bar.setValue(percent)
        self.status_label.setText(f"{status} — {percent}%")

    def _on_log(self, text):
        self.log_output.moveCursor(QTextCursor.MoveOperation.End)
        self.log_output.insertPlainText(text)
        self.log_output.moveCursor(QTextCursor.MoveOperation.End)

    def _on_finished(self, success, message):
        self.generate_btn.setEnabled(True)
        self.progress_bar.hide()

        if success:
            self.status_label.setText("✓ Complete!")
            self.status_label.setStyleSheet("color: #2d7d46; font-size: 12px; font-weight: bold;")
            self.statusBar().showMessage(f"✓ Saved: {message}")
        else:
            self.status_label.setText(f"✗ {message}")
            self.status_label.setStyleSheet("color: #e55; font-size: 12px;")
            self._on_log(f"\n✗ Error: {message}\n")

    def _save_settings(self):
        key = self.api_key_input.text().strip()
        if key:
            self.settings.setValue("api_key", key)
        self.settings.setValue("model_version", self.model_version_combo.currentIndex())
        self.settings.setValue("texture", self.texture_check.isChecked())
        self.settings.setValue("texture_quality", self.texture_quality_combo.currentIndex())
        self.settings.setValue("texture_alignment", self.texture_alignment_combo.currentIndex())
        self.settings.setValue("pbr", self.pbr_check.isChecked())
        self.settings.setValue("quad", self.quad_check.isChecked())
        self.settings.setValue("auto_size", self.auto_size_check.isChecked())
        self.settings.setValue("seed", self.seed_spin.value())
        self.settings.setValue("face_limit", self.face_limit_spin.value())

    def _load_settings(self):
        key = self.settings.value("api_key", "")
        if key:
            self.api_key_input.setText(key)
        idx = self.settings.value("model_version", 0, type=int)
        if 0 <= idx < self.model_version_combo.count():
            self.model_version_combo.setCurrentIndex(idx)
        self.texture_check.setChecked(self.settings.value("texture", True, type=bool))
        idx = self.settings.value("texture_quality", 0, type=int)
        if 0 <= idx < self.texture_quality_combo.count():
            self.texture_quality_combo.setCurrentIndex(idx)
        idx = self.settings.value("texture_alignment", 0, type=int)
        if 0 <= idx < self.texture_alignment_combo.count():
            self.texture_alignment_combo.setCurrentIndex(idx)
        self.pbr_check.setChecked(self.settings.value("pbr", True, type=bool))
        self.quad_check.setChecked(self.settings.value("quad", False, type=bool))
        self.auto_size_check.setChecked(self.settings.value("auto_size", False, type=bool))
        self.seed_spin.setValue(self.settings.value("seed", -1, type=int))
        self.face_limit_spin.setValue(self.settings.value("face_limit", 0, type=int))


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = TripoGUI()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
