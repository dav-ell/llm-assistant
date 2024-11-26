# main.py

import sys
import threading
import signal
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from spotlight_window import SpotlightWindow
from hotkey_listener import HotkeyListener
from logger import logger

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