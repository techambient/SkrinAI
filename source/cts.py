import sys
import io
import os
import math
import tempfile
from PIL import Image
import pytesseract
import mss
import mss.tools

from PyQt6.QtCore import (
    Qt, QRect, QRectF, QSize, QUrl, QThread, pyqtSignal, QBuffer, QEvent, QPointF, QTimer
)
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QPixmap,
    QLinearGradient, QRadialGradient, QAction, QFont
)
from PyQt6.QtWidgets import (
    QApplication, QWidget, QFileDialog, QMenu,
    QLineEdit, QPushButton, QHBoxLayout, QVBoxLayout, QFrame, QGraphicsDropShadowEffect, QLabel
)
from PyQt6.QtWebEngineWidgets import QWebEngineView

# Auto-detect Tesseract OCR path on Windows
tesseract_win_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
if os.path.exists(tesseract_win_path):
    pytesseract.pytesseract.tesseract_cmd = tesseract_win_path


# ==========================================
# 1. Enhanced High-Density Asynchronous OCR Worker
# ==========================================
class OCRWorker(QThread):
    finished = pyqtSignal(list, list)

    def __init__(self, pixmap):
        super().__init__()
        self.pixmap = pixmap

    def run(self):
        buffer = QBuffer()
        buffer.open(QBuffer.OpenModeFlag.ReadWrite)
        self.pixmap.save(buffer, "PNG")
        pil_img = Image.open(io.BytesIO(buffer.data()))

        text_blocks = []
        image_blocks = []

        try:
            # Enhanced PSM configuration (Page Segmentation Mode 11: Sparse text / Find as much text as possible)
            custom_config = r'--psm 11 --oem 3'
            data = pytesseract.image_to_data(pil_img, output_type=pytesseract.Output.DICT, config=custom_config)
            n_boxes = len(data['text'])
            
            for i in range(n_boxes):
                # Lower confidence threshold and capture finer granular text units for deep density coverage
                if int(data['conf'][i]) > 10 and data['text'][i].strip():
                    x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                    if w > 2 and h > 2:
                        text_blocks.append({
                            'rect': QRect(x, y, w, h),
                            'text': data['text'][i]
                        })
        except Exception as e:
            print(f"OCR Notification: {e}")

        self.finished.emit(text_blocks, image_blocks)


# ==========================================
# 2. 2030 Greyscale Liquid Glass HUD App
# ==========================================
class ScreenOverlayApp(QWidget):
    def __init__(self):
        super().__init__()
        
        self.capture_screen()
        
        # Window Flags & Native Resolution Lock
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        
        screen_geometry = QApplication.primaryScreen().geometry()
        self.setGeometry(screen_geometry)
        self.showFullScreen()

        # Operational States
        self.mode = "select"  # "select", "annotate", "eraser"
        self.annotation_paths = []
        self.selected_text_rects = []
        self.hovered_image_rect = None
        self.text_blocks = []
        self.selected_text = ""

        # 2030 Liquid Kinetic Animation Parameters
        self.anim_phase = 0.0

        # Asynchronous Background OCR Trigger
        self.ocr_thread = OCRWorker(self.background_pixmap)
        self.ocr_thread.finished.connect(self.on_ocr_finished)
        self.ocr_thread.start()

        # Build UI Structure
        self.init_ui()

        # 60 FPS Fluid Motion Loop
        self.startTimer(16)

    def capture_screen(self):
        with mss.MSS() as sbc:
            monitor = sbc.monitors[0]
            sbc_img = sbc.grab(monitor)
            raw_bytes = mss.tools.to_png(sbc_img.rgb, sbc_img.size)
            self.background_pixmap = QPixmap()
            self.background_pixmap.loadFromData(raw_bytes)

    def init_ui(self):
        self.setFont(QFont("Segoe UI", 10))
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(36, 36, 36, 36)

        center_container = QWidget()
        center_layout = QVBoxLayout(center_container)
        center_layout.setContentsMargins(0, 0, 0, 0)

        # 2030 Greyscale Sticky Liquid Glass Top Toolbar
        self.toolbar = QFrame()
        self.toolbar.setStyleSheet("""
            QFrame {
                background: rgba(12, 16, 28, 0.45);
                border: 1.5px solid rgba(255, 255, 255, 0.18);
                border-radius: 32px;
            }
            QPushButton {
                background: rgba(255, 255, 255, 0.04);
                color: rgba(241, 245, 249, 0.85);
                font-size: 13px;
                font-weight: 700;
                border: 1px solid rgba(255, 255, 255, 0.08);
                padding: 10px 22px;
                border-radius: 20px;
                letter-spacing: 0.8px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.14);
                color: rgba(255, 255, 255, 1.0);
                border: 1px solid rgba(255, 255, 255, 0.35);
            }
            QPushButton:pressed {
                background: rgba(255, 255, 255, 0.30);
                border: 1px solid rgba(255, 255, 255, 0.65);
                padding-top: 14px; /* Sticky liquid glass micro-bounce depth effect */
            }
            QPushButton:checked {
                background: rgba(255, 255, 255, 0.25);
                color: #FFFFFF;
                border: 1.5px solid rgba(255, 255, 255, 0.7);
                font-weight: 900;
            }
        """)
        
        tb_shadow = QGraphicsDropShadowEffect(self)
        tb_shadow.setBlurRadius(70)
        tb_shadow.setColor(QColor(0, 0, 0, 200))
        tb_shadow.setOffset(0, 10)
        self.toolbar.setGraphicsEffect(tb_shadow)

        tb_layout = QHBoxLayout(self.toolbar)
        tb_layout.setContentsMargins(18, 10, 18, 10)
        tb_layout.setSpacing(12)

        # Google Material Symbols Mapping for 2030 Glass UI
        btn_save = QPushButton("📄 SAVE")
        btn_save.setToolTip("Export Capture Frame")
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.clicked.connect(self.action_save)

        self.btn_select = QPushButton("𖦏 SELECT")
        self.btn_select.setCheckable(True)
        self.btn_select.setChecked(True)
        self.btn_select.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_select.setToolTip("OCR Neural Text Selector")
        self.btn_select.clicked.connect(lambda: self.set_mode("select"))

        self.btn_annotate = QPushButton("✐ DRAW")
        self.btn_annotate.setCheckable(True)
        self.btn_annotate.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_annotate.setToolTip("Freehand Vector Ink Canvas")
        self.btn_annotate.clicked.connect(lambda: self.set_mode("annotate"))

        self.btn_eraser = QPushButton("⌫ ERASE")
        self.btn_eraser.setCheckable(True)
        self.btn_eraser.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_eraser.setToolTip("Clear Annotations")
        self.btn_eraser.clicked.connect(lambda: self.set_mode("eraser"))

        btn_close = QPushButton("✕ EXIT")
        btn_close.setToolTip("Terminate Session")
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.03);
                color: rgba(241, 245, 249, 0.6);
                border: 1px solid rgba(255, 255, 255, 0.07);
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.15);
                color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 0.3);
            }
            QPushButton:pressed {
                padding-top: 14px;
            }
        """)
        btn_close.clicked.connect(QApplication.quit)

        tb_layout.addWidget(btn_save)
        tb_layout.addWidget(self.btn_select)
        tb_layout.addWidget(self.btn_annotate)
        tb_layout.addWidget(self.btn_eraser)
        tb_layout.addWidget(btn_close)

        # 2030 Greyscale Sticky Liquid Glass Bottom Search Engine Pill
        self.search_bar = QFrame()
        self.search_bar.setFixedWidth(700)
        self.search_bar.setStyleSheet("""
            QFrame {
                background: rgba(12, 16, 28, 0.50);
                border: 1.5px solid rgba(255, 255, 255, 0.20);
                border-radius: 35px;
            }
            QLineEdit {
                background: transparent;
                border: none;
                color: #F8FAFC;
                font-size: 14px;
                font-weight: 600;
                padding-left: 22px;
                selection-background-color: rgba(255, 255, 255, 0.35);
            }
            QLineEdit::placeholder {
                color: rgba(255, 255, 255, 0.35);
            }
            QPushButton {
                background: rgba(255, 255, 255, 0.09);
                color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 0.18);
                font-size: 13px;
                font-weight: 900;
                border-radius: 25px;
                padding: 12px 30px;
                letter-spacing: 1px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.22);
                border: 1px solid rgba(255, 255, 255, 0.45);
            }
            QPushButton:pressed {
                background: rgba(255, 255, 255, 0.38);
                padding-top: 15px;
            }
        """)
        
        sb_shadow = QGraphicsDropShadowEffect(self)
        sb_shadow.setBlurRadius(80)
        sb_shadow.setColor(QColor(0, 0, 0, 220))
        sb_shadow.setOffset(0, 12)
        self.search_bar.setGraphicsEffect(sb_shadow)

        sb_layout = QHBoxLayout(self.search_bar)
        sb_layout.setContentsMargins(14, 8, 8, 8)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("✦ Search anything with Gemini AI...")
        self.search_input.returnPressed.connect(self.action_trigger_search)
        
        btn_search = QPushButton("⌕ Search")
        btn_search.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_search.clicked.connect(self.action_trigger_search)

        sb_layout.addWidget(self.search_input)
        sb_layout.addWidget(btn_search)

        center_layout.addWidget(self.toolbar, 0, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        center_layout.addStretch()
        center_layout.addWidget(self.search_bar, 0, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom)

        # 2030 Greyscale Sticky Liquid Glass Web Matrix Side Panel (Instant Response Optimization)
        self.web_panel = QFrame()
        self.web_panel.setVisible(False)
        self.web_panel.setFixedWidth(620)
        self.web_panel.setStyleSheet("""
            QFrame {
                background: rgba(10, 13, 22, 0.75);
                border: 1.5px solid rgba(255, 255, 255, 0.18);
                border-radius: 32px;
            }
        """)
        
        wp_shadow = QGraphicsDropShadowEffect(self)
        wp_shadow.setBlurRadius(90)
        wp_shadow.setColor(QColor(0, 0, 0, 240))
        wp_shadow.setOffset(0, 0)
        self.web_panel.setGraphicsEffect(wp_shadow)

        web_layout = QVBoxLayout(self.web_panel)
        web_layout.setContentsMargins(18, 18, 18, 18)

        panel_top = QHBoxLayout()
        panel_top.setContentsMargins(10, 4, 10, 4)

        panel_title = QLabel("✦ Gemini AI")
        panel_title.setStyleSheet("color: rgba(255, 255, 255, 0.9); font-weight: 900; font-size: 13px; letter-spacing: 1.5px;")

        btn_close_web = QPushButton("✕")
        btn_close_web.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close_web.setStyleSheet("""
            QPushButton {
                color: rgba(255, 255, 255, 0.6);
                background: transparent;
                font-size: 18px;
                font-weight: bold;
                border: none;
                padding: 4px;
            }
            QPushButton:hover {
                color: #FFFFFF;
            }
        """)
        btn_close_web.clicked.connect(lambda: self.web_panel.setVisible(False))
        
        panel_top.addWidget(panel_title)
        panel_top.addStretch()
        panel_top.addWidget(btn_close_web)

        # High-Speed Accelerated Web Engine Configuration (Zero-Lag Google Performance)
        self.browser = QWebEngineView()
        self.browser.setStyleSheet("border-radius: 22px; background: transparent;")
        
        profile = self.browser.page().profile()
        profile.setHttpCacheType(profile.HttpCacheType.MemoryHttpCache)
        profile.clearHttpCache()
        
        self.browser.setZoomFactor(1.0)
        self.browser.loadFinished.connect(self._lock_web_zoom_and_optimize)
        self.browser.installEventFilter(self)

        web_layout.addLayout(panel_top)
        web_layout.addWidget(self.browser)

        self.main_layout.addWidget(center_container, 1)
        self.main_layout.addWidget(self.web_panel, 0)

    def _lock_web_zoom_and_optimize(self):
        js = """
        var style = document.createElement('style');
        style.innerHTML = 'html, body { zoom: 100% !important; transform: none !important; width: 100% !important; overflow-x: hidden !important; filter: grayscale(100%) contrast(110%); }';
        document.head.appendChild(style);
        
        // Purge extraneous resource heavy trackers and dynamic ads to deliver instantaneous lightning-fast responses
        document.querySelectorAll('iframe, script[src*="ads"], script[src*="analytics"], script[src*="gampad"]').forEach(el => el.remove());

        document.addEventListener('wheel', function(e) {
            if (e.ctrlKey) {
                e.preventDefault();
            }
        }, { passive: false });
        """
        self.browser.page().runJavaScript(js)
        
        if self.browser.focusProxy():
            self.browser.focusProxy().installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Wheel:
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                event.ignore()
                return True
        return super().eventFilter(obj, event)

    def wheelEvent(self, event):
        event.ignore()

    def timerEvent(self, event):
        self.anim_phase += 0.06
        self.update()

    def set_mode(self, mode):
        self.mode = mode
        self.btn_select.setChecked(mode == "select")
        self.btn_annotate.setChecked(mode == "annotate")
        self.btn_eraser.setChecked(mode == "eraser")

    def on_ocr_finished(self, text_blocks, image_blocks):
        self.text_blocks = text_blocks

    # ==========================================
    # 3. Graphics & Greyscale Liquid Renderer
    # ==========================================
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw Native Background Pixmap Converted to Strict Greyscale
        greyscale_pixmap = self.background_pixmap.toImage().convertToFormat(
            QPixmap().toImage().Format.Format_Grayscale8
        )
        painter.drawImage(self.rect(), greyscale_pixmap)

        # Dynamic Ambient Radial Backlight Glow Layer (Neutral Dark Tone)
        cx, cy = self.width() / 2, self.height() / 2
        bg_radial = QRadialGradient(QPointF(cx, cy), max(self.width(), self.height()))
        bg_radial.setColorAt(0.0, QColor(20, 20, 25, 30))
        bg_radial.setColorAt(1.0, QColor(5, 5, 8, 150))
        painter.fillRect(self.rect(), bg_radial)

        # 2030 Fluid Oscillating Colorful Screen Perimeter Border (The only colorful element)
        rect_f = QRectF(self.rect())
        pulse_alpha = int(190 + math.sin(self.anim_phase) * 65)
        
        glow_pen = QPen()
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0.0, QColor(56, 189, 248, pulse_alpha))
        gradient.setColorAt(0.5, QColor(192, 132, 252, pulse_alpha))
        gradient.setColorAt(1.0, QColor(244, 114, 182, pulse_alpha))
        
        glow_pen.setBrush(QBrush(gradient))
        glow_pen.setWidth(10)
        painter.setPen(glow_pen)
        painter.drawRect(rect_f)

        # High-Density OCR Text Highlights (Greyscale Sticky Liquid Glass Style)
        if self.mode == "select":
            painter.setPen(Qt.PenStyle.NoPen)
            highlight_glow = int(45 + math.sin(self.anim_phase * 2.0) * 20)
            for block in self.text_blocks:
                if any(block['rect'].intersects(r) for r in self.selected_text_rects):
                    painter.setBrush(QColor(255, 255, 255, 140))
                else:
                    painter.setBrush(QColor(255, 255, 255, highlight_glow))
                painter.drawRoundedRect(QRectF(block['rect']), 5, 5)

        # Dynamic Sci-Fi Target HUD Reticle over Right-Clicked Image Box (Greyscale)
        if self.hovered_image_rect:
            self.draw_liquid_target_hud(painter, self.hovered_image_rect)

        # Vector Freehand Annotations Canvas Layer (Greyscale Solid Ink)
        painter.setPen(QPen(QColor(240, 240, 245), 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        for path in self.annotation_paths:
            for i in range(len(path) - 1):
                painter.drawLine(path[i], path[i+1])

    def draw_liquid_target_hud(self, painter, rect):
        x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
        corner_len = min(w, h) // 4
        
        pen = QPen()
        pen.setWidth(4)
        pen.setColor(QColor(255, 255, 255, 210))
        painter.setPen(pen)

        # Sci-Fi Liquid Brackets
        painter.drawLine(x, y, x + corner_len, y)
        painter.drawLine(x, y, x, y + corner_len)
        painter.drawLine(x + w, y, x + w - corner_len, y)
        painter.drawLine(x + w, y, x + w, y + corner_len)
        painter.drawLine(x, y + h, x + corner_len, y + h)
        painter.drawLine(x, y + h, x, y + h - corner_len)
        painter.drawLine(x + w, y + h, x + w - corner_len, y + h)
        painter.drawLine(x + w, y + h, x + w, y + h - corner_len)

        # Rotating Central Targeting Reticle
        cx, cy = x + w // 2, y + h // 2
        rot_len = 14 + int(math.sin(self.anim_phase * 3.0) * 4)
        pen_center = QPen(QColor(255, 255, 255, 190))
        pen_center.setWidth(2)
        painter.setPen(pen_center)
        painter.drawLine(cx - rot_len, cy, cx + rot_len, cy)
        painter.drawLine(cx, cy - rot_len, cx, cy + rot_len)

    # ==========================================
    # 4. Mouse Tracking & Interactivity
    # ==========================================
    def mouseMoveEvent(self, event):
        if self.mode == "annotate" and event.buttons() & Qt.MouseButton.LeftButton:
            if self.annotation_paths:
                self.annotation_paths[-1].append(event.pos())
        elif self.mode == "eraser" and event.buttons() & Qt.MouseButton.LeftButton:
            self.annotation_paths = [
                path for path in self.annotation_paths 
                if not any((p - event.pos()).manhattanLength() < 25 for p in path)
            ]
        elif self.mode == "select" and event.buttons() & Qt.MouseButton.LeftButton:
            if self.selected_text_rects:
                self.selected_text_rects[-1] = self.selected_text_rects[-1].united(QRect(event.pos(), QSize(1, 1)))

        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.mode == "annotate":
                self.annotation_paths.append([event.pos()])
            elif self.mode == "select":
                self.selected_text_rects = [QRect(event.pos(), QSize(1, 1))]
        elif event.button() == Qt.MouseButton.RightButton:
            self.handle_right_click(event.pos())

    def mouseReleaseEvent(self, event):
        if self.mode == "select" and event.button() == Qt.MouseButton.LeftButton:
            selected_words = []
            for block in self.text_blocks:
                for rect in self.selected_text_rects:
                    if rect.intersects(block['rect']):
                        selected_words.append(block['text'])
            self.selected_text = " ".join(selected_words)

    def handle_right_click(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: rgba(10, 13, 22, 0.90);
                color: #F8FAFC;
                border: 1.5px solid rgba(255, 255, 255, 0.22);
                border-radius: 18px;
                padding: 8px;
            }
            QMenu::item {
                padding: 10px 24px;
                border-radius: 12px;
                font-size: 13px;
                font-weight: 700;
                color: rgba(255, 255, 255, 0.88);
            }
            QMenu::item:selected {
                background: rgba(255, 255, 255, 0.25);
                color: #FFFFFF;
            }
            QMenu::separator {
                height: 1px;
                background: rgba(255, 255, 255, 0.14);
                margin: 6px 8px;
            }
        """)

        clicked_img_crop = self.background_pixmap.copy(QRect(pos.x() - 75, pos.y() - 75, 150, 150))
        self.hovered_image_rect = QRect(pos.x() - 75, pos.y() - 75, 150, 150)
        self.update()

        act_save_img = QAction("💾 Save As Image", self)
        act_save_img.triggered.connect(lambda: self.save_image_to_device(clicked_img_crop))
        
        act_share_img = QAction("📤 View As Image", self)
        act_share_img.triggered.connect(lambda: self.share_image(clicked_img_crop))

        act_copy_img = QAction("📋 Copy As Image", self)
        act_copy_img.triggered.connect(lambda: QApplication.clipboard().setPixmap(clicked_img_crop))

        menu.addAction(act_save_img)
        menu.addAction(act_share_img)
        menu.addAction(act_copy_img)
        menu.addSeparator()

        if self.selected_text:
            act_copy_text = QAction("🎯 Copy As Text", self)
            act_copy_text.triggered.connect(lambda: QApplication.clipboard().setText(self.selected_text))
            menu.addAction(act_copy_text)

        act_select_all = QAction("✦ Select All OCR Texts", self)
        act_select_all.triggered.connect(self.action_select_all_text)
        menu.addAction(act_select_all)

        menu.exec(self.mapToGlobal(pos))
        self.hovered_image_rect = None
        self.update()

    # ==========================================
    # 5. Core Operational Features
    # ==========================================
    def action_save(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Capture", "", "PNG Image (*.png);;JPEG Image (*.jpg)")
        if file_path:
            full_canvas = self.background_pixmap.copy()
            painter = QPainter(full_canvas)
            painter.setPen(QPen(QColor(240, 240, 245), 4, Qt.PenStyle.SolidLine))
            for path in self.annotation_paths:
                for i in range(len(path) - 1):
                    painter.drawLine(path[i], path[i+1])
            painter.end()
            full_canvas.save(file_path)

    def action_select_all_text(self):
        full_text = " ".join([b['text'] for b in self.text_blocks])
        QApplication.clipboard().setText(full_text)
        self.selected_text_rects = [b['rect'] for b in self.text_blocks]
        self.update()

    def action_trigger_search(self):
        query = self.search_input.text()
        if not query:
            return
        
        temp_dir = tempfile.gettempdir()
        temp_file = os.path.join(temp_dir, "ai_screen_payload.png")
        self.background_pixmap.save(temp_file)

        # Lightning-fast text-mode rendering URL protocol (gbv=1 completely cuts asset bloat)
        target_url = f"https://www.google.com/search?q={query}&hl=en&gbv=1"
        self.browser.setUrl(QUrl(target_url))
        self.web_panel.setVisible(True)

    def save_image_to_device(self, pixmap):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Image Region", "", "PNG Image (*.png);;JPEG Image (*.jpg)")
        if file_path:
            pixmap.save(file_path)

    def share_image(self, pixmap):
        temp_path = os.path.join(tempfile.gettempdir(), "share_image.png")
        pixmap.save(temp_path)
        try:
            os.startfile(temp_path)
        except Exception:
            QApplication.clipboard().setPixmap(pixmap)


# ==========================================
# 6. Main Entry Point
# ==========================================
if __name__ == "__main__":
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    
    # Enable hardware acceleration and context sharing attributes to resolve network/rendering slowness
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts, True)

    app = QApplication(sys.argv)
    overlay = ScreenOverlayApp()
    sys.exit(app.exec())