"""
PySide6 GUI for Tripo AI 3D generation.
Supports single image, multiview turnaround, and text-to-3D.

Requirements:
    pip install PySide6 requests

Usage:
    python tripo_gui.py
"""

import sys
import os
import json
import threading
from pathlib import Path
from PySide6.QtCore import Qt, QSettings, Signal, QObject
from PySide6.QtGui import QTextCursor, QPixmap, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QTextEdit, QFileDialog,
    QGroupBox, QFormLayout, QProgressBar, QMessageBox, QScrollArea,
    QFrame, QTabWidget, QSpinBox, QSizePolicy, QGridLayout,
)

SCRIPT_DIR = Path(__file__).parent

OUTPUT_FORMATS = ["glb", "fbx", "obj", "stl", "usdz"]

SUPPORTED_IMAGES = "Images (*.png *.jpg *.jpeg *.webp *.bmp);;All Files (*)"


# ============================================================
# Worker signals (thread-safe GUI updates)
# ============================================================

class WorkerSignals(QObject):
    progress = Signal(int, str)       # percent, status text
    log = Signal(str)                 # log message
    finished = Signal(bool, str)      # success, message
    balance = Signal(str)             # balance info


# ============================================================
# Image Drop Label
# ============================================================

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
            path, _ = QFileDialog.getOpenFileName(
                self, "Select Image", "", SUPPORTED_IMAGES
            )
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


# ============================================================
# Main GUI
# ============================================================

class TripoGUI(QMainWindow):
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

        self._build_ui()
        self._load_settings()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(8)

        # --- API Key ---
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

        # --- Input Tabs ---
        self.input_tabs = QTabWidget()

        # Tab 1: Single Image
        single_tab = QWidget()
        single_layout = QVBoxLayout(single_tab)
        self.single_image = ImageDropLabel("Drop image here\nor click to browse")
        single_layout.addWidget(self.single_image)
        self.input_tabs.addTab(single_tab, "📷 Single Image")

        # Tab 2: Multiview Turnaround
        multi_tab = QWidget()
        multi_layout = QVBoxLayout(multi_tab)

        multi_desc = QLabel(
            "Add 2-6 turnaround images from different angles.\n"
            "Best results: even spacing around the object at roughly eye level."
        )
        multi_desc.setStyleSheet("color: #888; font-size: 11px;")
        multi_desc.setWordWrap(True)
        multi_layout.addWidget(multi_desc)

        # Grid of image drop slots
        self.multi_images = []
        grid = QGridLayout()
        grid.setSpacing(8)
        view_labels = ["Front", "Back", "Left", "Right"]

        for i, label in enumerate(view_labels):
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

        multi_btn_row = QHBoxLayout()
        clear_multi_btn = QPushButton("Clear All")
        clear_multi_btn.clicked.connect(self._clear_multiview)
        multi_btn_row.addStretch()
        multi_btn_row.addWidget(clear_multi_btn)
        multi_layout.addLayout(multi_btn_row)

        self.input_tabs.addTab(multi_tab, "🔄 Multiview Turnaround")

        # Tab 3: Text Prompt
        text_tab = QWidget()
        text_layout = QVBoxLayout(text_tab)
        self.prompt_input = QTextEdit()
        self.prompt_input.setPlaceholderText(
            "Describe the 3D object you want to generate...\n\n"
            'e.g., "A weathered wooden barrel with iron bands, '
            'medieval fantasy style"'
        )
        self.prompt_input.setMaximumHeight(120)
        text_layout.addWidget(self.prompt_input)
        self.input_tabs.addTab(text_tab, "✍️ Text Prompt")

        layout.addWidget(self.input_tabs)

        # --- Output Settings ---
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
        self.timeout_spin.setSingleStep(60)
        options_row.addWidget(self.timeout_spin)

        options_row.addStretch()
        output_layout.addRow(options_row)

        layout.addWidget(output_group)

        # --- Generate Button ---
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

        # --- Progress ---
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #aaa; font-size: 12px;")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.hide()
        layout.addWidget(self.status_label)

        # --- Log ---
        log_group = QGroupBox("Log")
        log_layout = QVBoxLayout(log_group)
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumHeight(160)
        self.log_output.setStyleSheet(
            "QTextEdit { background-color: #1e1e1e; color: #d4d4d4; "
            "font-family: 'Consolas', 'Courier New', monospace; font-size: 12px; }"
        )
        log_layout.addWidget(self.log_output)
        layout.addWidget(log_group)

        self.statusBar().showMessage("Ready")

    # --------------------------------------------------------- Actions
    def _get_api_key(self):
        key = self.api_key_input.text().strip()
        if not key:
            key = os.environ.get("TRIPO_API_KEY", "")
        return key

    def _toggle_key_visibility(self, checked):
        self.api_key_input.setEchoMode(
            QLineEdit.Normal if checked else QLineEdit.Password
        )
        self.show_key_btn.setText("Hide" if checked else "Show")

    def _browse_output(self):
        fmt = self.format_combo.currentText()
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Output", "",
            f"3D Model (*.{fmt});;All Files (*)"
        )
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
        threading.Thread(target=self._balance_worker, args=(api_key,),
                         daemon=True).start()

    def _balance_worker(self, api_key):
        try:
            from tripo_generate import TripoClient
            client = TripoClient(api_key)
            balance = client.get_balance()
            self.signals.balance.emit(json.dumps(balance, indent=2))
        except Exception as e:
            self.signals.balance.emit(f"Error: {e}")

    def _on_balance(self, info):
        self.balance_btn.setEnabled(True)
        QMessageBox.information(self, "Tripo Balance", info)

    # --------------------------------------------------------- Generate
    def _generate(self):
        api_key = self._get_api_key()
        if not api_key:
            QMessageBox.warning(self, "No API Key",
                                "Enter your Tripo API key or set TRIPO_API_KEY.")
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

        # Determine mode
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
                QMessageBox.warning(self, "Not Enough Images",
                                    "Multiview needs at least 2 images.")
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

        # Go
        self.log_output.clear()
        self._log(f"Mode: {mode}\nOutput: {output}\nFormat: {fmt}\n\n")

        self.generate_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_bar.show()
        self.status_label.show()
        self.statusBar().showMessage("Generating...")

        self.worker_thread = threading.Thread(
            target=self._generate_worker,
            args=(api_key, mode, payload, output, fmt, timeout),
            daemon=True,
        )
        self.worker_thread.start()
        self._save_settings()

    def _generate_worker(self, api_key, mode, payload, output, fmt, timeout):
        """Run generation in background thread."""
        try:
            from tripo_generate import TripoClient

            client = TripoClient(api_key)

            if mode == "single":
                self.signals.log.emit("Uploading image...\n")
                image_token = client.upload_image(payload["image"])

                self.signals.log.emit("Creating image-to-3D task...\n")
                params = {
                    "file": {"type": "image_token", "file_token": image_token},
                }
                task_id = client.create_task("image_to_model", params)

            elif mode == "multiview":
                self.signals.log.emit(f"Uploading {len(payload['images'])} images...\n")
                tokens = []
                for i, img_path in enumerate(payload["images"]):
                    self.signals.log.emit(f"  Uploading {i+1}/{len(payload['images'])}: {os.path.basename(img_path)}\n")
                    token = client.upload_image(img_path)
                    tokens.append(token)

                self.signals.log.emit("Creating multiview-to-3D task...\n")
                files = [{"type": "image_token", "file_token": t} for t in tokens]
                params = {"files": files}
                task_id = client.create_task("multiview_to_model", params)

            elif mode == "text":
                self.signals.log.emit(f"Creating text-to-3D task...\n")
                self.signals.log.emit(f"  Prompt: {payload['prompt']}\n")
                params = {"prompt": payload["prompt"]}
                task_id = client.create_task("text_to_model", params)

            # Poll
            self.signals.log.emit(f"Task ID: {task_id}\nWaiting for generation...\n\n")
            import time
            import requests
            start = time.time()

            while True:
                elapsed = time.time() - start
                if elapsed > timeout:
                    self.signals.finished.emit(False, f"Timed out after {timeout}s")
                    return

                resp = client.session.get(
                    f"https://api.tripo3d.ai/v2/openapi/task/{task_id}"
                )
                resp.raise_for_status()
                data = resp.json()

                if data.get("code") != 0:
                    self.signals.finished.emit(False, f"Poll error: {data.get('message')}")
                    return

                task_data = data["data"]
                status = task_data.get("status", "unknown")
                progress = task_data.get("progress", 0)

                self.signals.progress.emit(progress, status)

                if status == "success":
                    self.signals.log.emit("\nGeneration complete! Downloading...\n")
                    client.download_model(task_data, output, fmt)
                    self.signals.log.emit(f"\n✓ Saved: {output}\n")
                    self.signals.finished.emit(True, output)
                    return

                if status in ("failed", "cancelled", "unknown"):
                    msg = task_data.get("message", "No details")
                    self.signals.finished.emit(False, f"Task {status}: {msg}")
                    return

                time.sleep(3)

        except Exception as e:
            self.signals.finished.emit(False, str(e))

    # --------------------------------------------------------- Callbacks
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
            self.statusBar().showMessage("✗ Generation failed")
            self._on_log(f"\n✗ Error: {message}\n")

    # --------------------------------------------------------- Settings
    def _save_settings(self):
        # Save key only if user explicitly typed one
        key = self.api_key_input.text().strip()
        if key:
            self.settings.setValue("api_key", key)

    def _load_settings(self):
        key = self.settings.value("api_key", "")
        if key:
            self.api_key_input.setText(key)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = TripoGUI()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
