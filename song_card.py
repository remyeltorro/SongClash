class SongCard(QFrame):
    clicked = pyqtSignal()

    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFrameShape(QFrame.Shape.StyledPanel)

        # Layout to center label
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        self.label = QLabel(text)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setWordWrap(True)
        # Inherit font style from stylesheet or set explicitly if needed
        # We start with transparent bg so the Frame bg shows
        self.label.setStyleSheet("background: transparent; border: none;")

        layout.addWidget(self.label)

        # Styles
        # Note: We use ID selector or just class selector logic if we could,
        # but here we update the whole sheet.
        self.default_style = """
            SongCard {
                background-color: #1e1e1e; 
                border-radius: 12px;
                border: 2px solid #333;
            }
            QLabel {
                font-size: 26px; 
                font-weight: bold; 
                color: #e0e0e0;
                background: transparent;
                border: none;
            }
        """
        self.hover_style = """
            SongCard {
                background-color: #2a2a2a;
                border-radius: 12px;
                border: 2px solid #e67e22;
            }
            QLabel {
                font-size: 26px; 
                font-weight: bold; 
                color: white;
                background: transparent;
                border: none;
            }
        """
        self.pressed_style = """
            SongCard {
                background-color: #121212;
                border-radius: 12px;
                border: 2px solid #d35400;
            }
            QLabel {
                font-size: 26px; 
                font-weight: bold; 
                color: white;
                background: transparent;
                border: none;
            }
        """
        self.disabled_style = """
            SongCard {
                background-color: #121212;
                border-radius: 12px;
                border: 2px solid #222;
            }
            QLabel {
                font-size: 26px; 
                font-weight: bold; 
                color: #444;
            }
        """

        self.setStyleSheet(self.default_style)

    def setText(self, text):
        self.label.setText(text)

    def enterEvent(self, event):
        if self.isEnabled():
            self.setStyleSheet(self.hover_style)
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self.isEnabled():
            self.setStyleSheet(self.default_style)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if self.isEnabled() and event.button() == Qt.MouseButton.LeftButton:
            self.setStyleSheet(self.pressed_style)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self.isEnabled() and event.button() == Qt.MouseButton.LeftButton:
            if self.rect().contains(event.pos()):
                self.clicked.emit()
                self.setStyleSheet(self.hover_style)
            else:
                self.setStyleSheet(self.default_style)
        super().mouseReleaseEvent(event)

    def setEnabled(self, validate):
        super().setEnabled(validate)
        if validate:
            self.setStyleSheet(self.default_style)
        else:
            self.setStyleSheet(self.disabled_style)
