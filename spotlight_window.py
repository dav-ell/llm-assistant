# spotlight_window.py

import threading
from PySide6.QtWidgets import (
    QApplication, QLineEdit, QLabel, QVBoxLayout, QWidget, QTextEdit
)
from PySide6.QtCore import Qt, Signal, Slot, QEvent, QTimer
from PySide6.QtGui import QTextCursor
from config import DEFAULT_PROMPT, MULTI_QUERY_INTERVALS, OLLAMA_MODEL_NAME
from database import get_db_connection, fetch_recent_full_texts
from ollama_client import send_to_ollama_stream
from logger import logger


class SpotlightWindow(QWidget):
    assistant_reply_signal = Signal(str)
    assistant_reply_part_signal = Signal(str)
    context_info_signal = Signal(str, int)  # Updated signal for model, context length, and time range

    def __init__(self):
        super().__init__()
        self.init_ui()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)  # Ensure fully opaque background
        self.showing_response = False

        # Connect the signals to the slots
        self.assistant_reply_signal.connect(self.display_response)
        self.assistant_reply_part_signal.connect(self.append_response)
        self.context_info_signal.connect(self.update_context_display)  # Connect new signal

    def init_ui(self):
        # Query Input
        self.query_input = QLineEdit(self)
        self.query_input.setPlaceholderText("Enter your query...")
        self.query_input.returnPressed.connect(self.handle_query)

        # Response Display
        self.response_display = QTextEdit(self)
        self.response_display.setReadOnly(True)
        self.response_display.hide()

        # Single Context Info Label
        self.context_info_label = QLabel(self)
        # **Initial text with model name and default context info**
        self.context_info_label.setText(f"{OLLAMA_MODEL_NAME} -- context from last 30 seconds -- context length 0 words")
        self.context_info_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.context_info_label.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 0, 0, 100);
                color: #00FFFF;
                padding: 5px 10px;
                border-radius: 15px;
                font-size: 12px;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }
        """)
        self.context_info_label.setVisible(False)  # Hidden by default

        # Layout Setup
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)  # Increased padding
        layout.setSpacing(15)  # Increased spacing between widgets
        layout.addWidget(self.query_input)
        layout.addWidget(self.response_display)

        # Add context info label
        layout.addWidget(self.context_info_label)

        self.setLayout(layout)

        # Styling to resemble futuristic Spotlight
        self.setFixedWidth(700)

        # **Adjusted initial size: height enough for QLineEdit and margins**
        self.setMinimumHeight(100)  # Increased from 70 to 100
        self.setMaximumHeight(100)  # Increased from 70 to 100

        # Initial position (will be updated in showEvent)
        self.center_window()

        # Set stylesheets with futuristic colors and fonts
        self.query_input.setStyleSheet("""
            QLineEdit {
                background-color: rgba(255, 255, 255, 30);
                padding: 15px;
                font-size: 18px;
                border: 2px solid #00FFFF;
                border-radius: 10px;
                color: #FFFFFF;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }
            QLineEdit:focus {
                border: 2px solid #00FFFF;
                background-color: rgba(255, 255, 255, 50);
            }
        """)
        self.response_display.setStyleSheet("""
            QTextEdit {
                background-color: rgba(0, 0, 0, 50);
                padding: 15px;
                font-size: 16px;
                border: none;
                border-radius: 10px;
                color: #FFFFFF;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }
        """)

        # Set window background to fully opaque with a dark theme
        self.setStyleSheet("""
            QWidget {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1e1e1e,
                    stop:1 #3e3e3e
                );
                border-radius: 15px;
            }
        """)

    def center_window(self):
        screen_geometry = QApplication.primaryScreen().geometry()
        self.move(
            screen_geometry.center().x() - self.width() // 2,
            screen_geometry.center().y() - self.height() // 2 - 200
        )

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
        self.setMinimumHeight(370)  # 70 (original) + 300
        self.setMaximumHeight(370)

        # Show context info label
        self.context_info_label.setVisible(True)
        # **Initialize with default values**
        self.context_info_label.setText(f"{OLLAMA_MODEL_NAME} -- context from last 30 seconds -- context length 0 words")

        # Fetch context and process the query in a separate thread
        threading.Thread(target=self.process_query, args=(user_query,), daemon=True).start()

    def process_query(self, user_query):
        context_text = ""
        context_length = 0
        time_range = "last 30 seconds"  # Default time range

        # Iterate through the defined intervals
        for interval in MULTI_QUERY_INTERVALS:
            with get_db_connection() as conn:
                entries = fetch_recent_full_texts(conn, interval_seconds=interval)

            if entries:
                # Combine all recent texts into one context
                try:
                    context_text = "\n".join([str(entry[1]) for entry in entries])  # Ensure strings
                except Exception as e:
                    logger.error(f"Error concatenating context texts: {e}")
                    context_text = ""
                context_length = len(context_text.split())

                # Set time range as "last {interval} seconds"
                time_range = f"last {interval} seconds"

                logger.info(f"Using context from the last {interval} seconds with length {context_length} words.")
                self.context_info_signal.emit(time_range, context_length)  # Emit time range and context length
                break
            else:
                logger.info(f"No context found for interval {interval} seconds.")
                self.context_info_signal.emit(f"last {interval} seconds", 0)  # Emit time range and zero context length

        if not context_text:
            logger.info("No recent context found after all attempts.")
            context_text = ""
            time_range = "last 0 seconds"

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

    @Slot(str, int)
    def update_context_display(self, time_range, length):
        """
        Update the context_info_label with the format:
        <model> -- context from <time_range> -- context length <length> words
        """
        self.context_info_label.setText(f"{OLLAMA_MODEL_NAME} -- context from {time_range} -- context length {length} words")

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
        self.center_window()

    def toggle_visibility(self):
        if self.isVisible():
            self.hide_window()
        else:
            self.show()

    def hide_window(self):
        # Do not clear the fields; retain the last conversation
        # Only adjust window height based on current content
        if self.response_display.toPlainText().strip():
            self.setMinimumHeight(370)  # Maintain the height for responses
            self.setMaximumHeight(370)
        else:
            self.setMinimumHeight(100)  # Reset to the new minimum height
            self.setMaximumHeight(100)
        self.hide()