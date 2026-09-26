"""Running blocking service calls off the GUI thread."""

import threading

from PyQt6.QtCore import QObject, pyqtSignal

from songclash.services.errors import FetchCancelled


class Task(QObject):
    """Runs a blocking function on a daemon thread and reports back via signals.

    Daemon threads never block app exit, and signals emitted from them are
    delivered on the GUI thread.
    """

    succeeded = pyqtSignal(object)
    failed = pyqtSignal(str)
    progress = pyqtSignal(str, int)
    done = pyqtSignal()

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn, self.args, self.kwargs = fn, args, kwargs
        self.cancel_event = threading.Event()

    def with_progress(self):
        """Pass ``progress`` and ``cancel`` kwargs, for long service calls."""
        self.kwargs["progress"] = self.progress.emit
        self.kwargs["cancel"] = self.cancel_event
        return self

    def start(self):
        threading.Thread(target=self._run, daemon=True).start()

    def cancel(self):
        self.cancel_event.set()

    @property
    def cancelled(self):
        return self.cancel_event.is_set()

    def _run(self):
        try:
            result = self.fn(*self.args, **self.kwargs)
        except FetchCancelled:
            pass
        except Exception as e:
            if not self.cancelled:
                self.failed.emit(str(e) or type(e).__name__)
        else:
            if not self.cancelled:
                self.succeeded.emit(result)
        finally:
            self.done.emit()


class TaskRunner:
    """Starts tasks and keeps them alive (and cancellable) until done."""

    def __init__(self):
        self._tasks = set()

    def run(self, task, on_success, on_failure=None):
        self._tasks.add(task)
        task.succeeded.connect(on_success)
        if on_failure:
            task.failed.connect(on_failure)
        task.done.connect(lambda: self._tasks.discard(task))
        task.start()
        return task

    def cancel_all(self):
        for task in list(self._tasks):
            task.cancel()
