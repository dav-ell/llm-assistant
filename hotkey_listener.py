# hotkey_listener.py

import threading
from PySide6.QtCore import QObject, Signal
from pynput import keyboard
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
        # Example for Windows/Linux: '<ctrl>+<alt>+<shift>+o'
        # For macOS, it might be '<cmd>+<ctrl>+<shift>+o'
        hotkey_combination = '<cmd>+<ctrl>+<shift>+o'  # Modify as per your OS

        with keyboard.GlobalHotKeys({
                hotkey_combination: on_activate
        }) as self.listener:
            self.listener.join()
            