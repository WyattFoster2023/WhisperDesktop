import os
import sys
import logging
import traceback
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta
import threading
import glob
import shutil

# Optional: Only import PyQt5 if available (for error dialogs)
try:
    from PyQt5.QtWidgets import QApplication, QMessageBox
    PYQT5_AVAILABLE = True
except ImportError:
    PYQT5_AVAILABLE = False

# EventBus import (assume exists)
try:
    from whisperdesktop.event_bus.event_bus import EventBus, EventType
except ImportError:
    EventBus = None
    EventType = None

# === Logger Configuration ===
# These can be set via environment variables or config file
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()  # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_MAX_BYTES = int(os.getenv('LOG_MAX_BYTES', 10 * 1024 * 1024))  # 10MB default
LOG_BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', 5))
LOG_RETENTION_DAYS = int(os.getenv('LOG_RETENTION_DAYS', 30))  # days

class ErrorReporter:
    """
    Collects error events from EventBus and displays notifications for critical errors.
    """
    def __init__(self, event_bus):
        self._event_bus = event_bus
        self._errors = []  # List of dicts: {timestamp, message, severity, traceback}
        if self._event_bus:
            self._event_bus.subscribe(EventType.ERROR, self._on_error_event)

    def _on_error_event(self, data):
        error = {
            'timestamp': datetime.now().isoformat(),
            'message': data.get('message', ''),
            'severity': 'CRITICAL' if data.get('critical') else 'ERROR',
            'traceback': data.get('traceback', None)
        }
        self._errors.append(error)
        # Show notification for critical errors
        if data.get('critical') and PYQT5_AVAILABLE:
            try:
                if QApplication.instance():
                    QMessageBox.critical(None, "Critical Error", f"{error['message']}\n\nSee logs for details.")
            except Exception:
                pass

    def get_recent_errors(self, limit=10):
        return self._errors[-limit:]

class Logger:
    _instance = None
    _lock = threading.Lock()
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(Logger, cls).__new__(cls)
            cls._instance._initialize_logger()
        return cls._instance

    def _initialize_logger(self):
        self.logger = logging.getLogger("whisperdesktop")
        self.logger.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def info(self, message):
        self.logger.info(message)

    def error(self, message):
        self.logger.error(message)

    def debug(self, message):
        self.logger.debug(message)

    def warning(self, message):
        self.logger.warning(message)

    def archive_old_logs(self):
        """
        Move rotated log files (app.log.1, app.log.2, ...) to logs/archive/ with timestamped names.
        """
        for i in range(1, LOG_BACKUP_COUNT + 1):
            rotated_log = f'logs/app.log.{i}'
            if os.path.exists(rotated_log):
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                archive_name = f'logs/archive/app_{timestamp}_{i}.log'
                try:
                    shutil.move(rotated_log, archive_name)
                except Exception as e:
                    self.logger.error(f"Failed to archive log {rotated_log}: {e}")

    def cleanup_old_logs(self):
        """
        Delete archived logs older than LOG_RETENTION_DAYS.
        """
        now = datetime.now()
        archive_dir = 'logs/archive'
        for log_file in glob.glob(os.path.join(archive_dir, 'app_*.log')):
            try:
                mtime = datetime.fromtimestamp(os.path.getmtime(log_file))
                if (now - mtime).days > LOG_RETENTION_DAYS:
                    os.remove(log_file)
            except Exception as e:
                self.logger.error(f"Failed to cleanup log {log_file}: {e}")

# Global exception handler
def global_exception_handler(exctype, value, tb):
    logger = Logger()
    tb_str = ''.join(traceback.format_exception(exctype, value, tb))
    logger.logger.critical(f"Uncaught exception: {value}", exc_info=(exctype, value, tb))
    # Create crash report
    try:
        os.makedirs('crash_reports', exist_ok=True)
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        crash_path = f'crash_reports/crash_{timestamp}.txt'
        with open(crash_path, 'w', encoding='utf-8') as f:
            f.write(f"Crash Report - {timestamp}\n\n")
            f.write(f"Exception: {exctype.__name__}: {value}\n\n")
            f.write(f"Traceback:\n{tb_str}\n")
    except Exception as e:
        logger.logger.error(f"Failed to create crash report: {e}")
    # Show error dialog if possible
    try:
        if PYQT5_AVAILABLE and QApplication.instance():
            QMessageBox.critical(None, "Critical Error", \
                f"The application encountered a critical error and needs to close.\n\n"
                f"Error: {value}\n\n"
                f"A crash report has been saved to the crash_reports directory.")
    except Exception as e:
        logger.logger.error(f"Failed to show error dialog: {e}")

# Register the global exception handler
sys.excepthook = global_exception_handler 