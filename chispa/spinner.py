"""Simple spinner for progress indication."""

import sys
import threading
import time

CLEAR_WIDTH = 80


class Spinner:
    """A simple terminal spinner."""

    FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self, message: str = ""):
        self.message = message
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def _spin(self) -> None:
        idx = 0
        while not self._stop_event.is_set():
            frame = self.FRAMES[idx % len(self.FRAMES)]
            sys.stdout.write(f"\r  {frame} {self.message}")
            sys.stdout.flush()
            idx += 1
            time.sleep(0.08)

    def start(self) -> None:
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=0.5)
        sys.stdout.write("\r" + " " * CLEAR_WIDTH + "\r")
        sys.stdout.flush()
