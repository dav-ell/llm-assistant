# main.py

import sys
import threading
import signal  # Imported for signal handling
from PySide6.QtWidgets import (
    QApplication, QLineEdit, QLabel, QVBoxLayout, QWidget, QTextEdit
)
from PySide6.QtCore import Qt, Signal, QObject, Slot, QEvent, QTimer
from PySide6.QtGui import QTextCursor
from pynput import keyboard
from config import DEFAULT_PROMPT
from database import get_db_connection, fetch_recent_full_texts
from ollama_client import send_to_ollama, send_to_ollama_stream
from logger import logger


class HotkeyListener(QObject):
    hotkey_pressed = Signal()

    def __init__(self):
        super().__init__()
        self.listener = None

    def start(self):
        def on_activate():
            logger.info("Hotkey pressed")
            self.hotkey_pressed.emit()

        # Define the hotkey (adjust according to your OS if needed)
        with keyboard.GlobalHotKeys({
                '<cmd>+<ctrl>+<shift>+o': on_activate  # Modify as per your OS
        }) as self.listener:
            self.listener.join()


class SpotlightWindow(QWidget):
    assistant_reply_signal = Signal(str)
    assistant_reply_part_signal = Signal(str)

    def __init__(self):
        super().__init__()
        self.init_ui()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.showing_response = False

        # Connect the signals to the slots
        self.assistant_reply_signal.connect(self.display_response)
        self.assistant_reply_part_signal.connect(self.append_response)

    def init_ui(self):
        self.query_input = QLineEdit(self)
        self.query_input.setPlaceholderText("Enter your query...")
        self.query_input.returnPressed.connect(self.handle_query)

        self.response_display = QTextEdit(self)
        self.response_display.setReadOnly(True)
        self.response_display.hide()

        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)  # Add some padding
        layout.setSpacing(10)  # Add spacing between widgets
        layout.addWidget(self.query_input)
        layout.addWidget(self.response_display)
        self.setLayout(layout)

        # Styling to resemble Spotlight
        self.setFixedWidth(600)

        # Initial size: height enough for QLineEdit only
        self.setMinimumHeight(60)
        self.setMaximumHeight(60)

        # Initial position (will be updated in showEvent)
        self.move(
            QApplication.primaryScreen().geometry().center().x() - self.width() // 2,
            QApplication.primaryScreen().geometry().center().y() - self.height() // 2 - 200
        )

        # Set stylesheets with visible text color
        self.query_input.setStyleSheet("""
            QLineEdit {
                background-color: white;
                padding: 10px;
                font-size: 18px;
                border-radius: 10px;
                color: black;
            }
        """)
        self.response_display.setStyleSheet("""
            QTextEdit {
                background-color: white;
                padding: 10px;
                font-size: 16px;
                border-radius: 10px;
                color: black;
            }
        """)

        # Set window background color if needed
        self.setStyleSheet("""
            QWidget {
                background-color: transparent;
            }
        """)

    def show(self):
        super().show()
        # Use a single-shot timer to set focus after the window is shown
        QTimer.singleShot(100, self.focus_query_input)

    def focus_query_input(self):
        self.raise_()  # Ensure the window is on top
        self.activateWindow()  # Activate the window
        self.query_input.setFocus(Qt.ActiveWindowFocusReason)  # Set focus to the input
        self.query_input.selectAll()  # Optional: Select all text for easy overwriting

    def handle_query(self):
        user_query = self.query_input.text().strip()
        if not user_query:
            logger.info("No query entered.")
            self.hide_window()
            return

        # Clear previous query and response to start a new conversation
        self.query_input.clear()
        self.response_display.clear()

        # Show the response display and prepare for streaming
        self.response_display.show()
        self.showing_response = True

        # Adjust window height to accommodate the response
        self.setMinimumHeight(60 + 240)  # QLineEdit height + QTextEdit height + margins
        self.setMaximumHeight(60 + 240)

        # Fetch context and process the query in a separate thread
        threading.Thread(target=self.process_query, args=(user_query,), daemon=True).start()

    def process_query(self, user_query):
        # Fetch recent context
        with get_db_connection() as conn:
            entries = fetch_recent_full_texts(conn)

        if not entries:
            logger.info("No recent context found.")
            context_text = ""
        else:
            # Combine all recent texts into one context
            context_text = "\n".join([entry[2] for entry in entries])

        # Prepare the prompt
        prompt = f"{DEFAULT_PROMPT}\n\nContext:\n{context_text}\n\nUser Query:\n{user_query}"
        logger.debug(f"Prompt: {prompt}")

        # Use the streaming function
        try:
            for assistant_part in send_to_ollama_stream(prompt):
                if assistant_part:
                    logger.info(f"Received part from LLM: {assistant_part}")
                    # Emit signal with assistant reply part
                    self.assistant_reply_part_signal.emit(assistant_part)
        except Exception as e:
            logger.error(f"Error during streaming: {e}")
            self.assistant_reply_signal.emit("Error communicating with the assistant.")

    @Slot(str)
    def display_response(self, response):
        self.response_display.setText(response)
        # Allow the layout to adjust the window size
        self.adjustSize()

    @Slot(str)
    def append_response(self, part):
        self.response_display.moveCursor(QTextCursor.End)
        self.response_display.insertPlainText(part)
        self.response_display.ensureCursorVisible()

    def closeEvent(self, event):
        # Instead of closing the window, hide it
        event.ignore()
        self.hide_window()

    def event(self, event):
        if event.type() == QEvent.WindowDeactivate:
            self.hide_window()
        return super().event(event)

    def showEvent(self, event):
        super().showEvent(event)
        # Position the window at the center-top
        self.move(
            QApplication.primaryScreen().geometry().center().x() - self.width() // 2,
            QApplication.primaryScreen().geometry().center().y() - self.height() // 2 - 200
        )

    def toggle_visibility(self):
        if self.isVisible():
            self.hide_window()
        else:
            self.show()

    def hide_window(self):
        # Do not clear the fields; retain the last conversation
        # Only adjust window height based on current content
        if self.response_display.toPlainText().strip():
            self.setMinimumHeight(60 + 240)
            self.setMaximumHeight(60 + 240)
        else:
            self.setMinimumHeight(60)
            self.setMaximumHeight(60)
        self.hide()


def main():
    logger.info("Starting LLM Assistant with PySide6 GUI.")

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # Ensure the app doesn't quit when the window is hidden

    # **Signal Handling for Ctrl+C (SIGINT)**
    def signal_handler(sig, frame):
        logger.info("SIGINT received. Exiting application.")
        app.quit()

    signal.signal(signal.SIGINT, signal_handler)

    window = SpotlightWindow()

    # Set up the hotkey listener
    hotkey_listener = HotkeyListener()

    # Connect the hotkey signal to toggle window visibility
    hotkey_listener.hotkey_pressed.connect(window.toggle_visibility)

    # Start the hotkey listener in a separate daemon thread
    threading.Thread(target=hotkey_listener.start, daemon=True).start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
    