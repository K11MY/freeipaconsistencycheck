"""
Loading indicator utilities.

This module provides a simple animated loading indicator to show users
that the application is working during long-running operations.
"""

import sys
import threading
import time
import itertools


class LoadingIndicator:
    """
    A simple loading indicator that shows animated dots in the terminal.

    This provides a visual cue to the user that the application is working
    while performing long-running operations like connecting to servers.
    """

    def __init__(self, message="Working", delay=0.2):
        """
        Initialize the loading indicator.

        Args:
            message: The message to display before the dots
            delay: The delay between animation frames in seconds
        """
        self.message = message
        self.delay = delay
        self.spinner = itertools.cycle([".", "..", "..."])
        self.running = False
        self.thread = None

    def start(self):
        """Start displaying the loading animation."""
        self.running = True
        self.thread = threading.Thread(target=self._animate)
        self.thread.daemon = True
        self.thread.start()

    def stop(self):
        """Stop the loading animation and clean up the line."""
        if self.running:
            self.running = False
            if self.thread:
                self.thread.join()
            # Clear the line
            sys.stdout.write("\r" + " " * (len(self.message) + 10) + "\r")
            sys.stdout.flush()

    def _animate(self):
        """Display the animated dots."""
        while self.running:
            sys.stdout.write("\r" + self.message + next(self.spinner) + " ")
            sys.stdout.flush()
            time.sleep(self.delay)
