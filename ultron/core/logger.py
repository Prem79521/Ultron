"""
ULTRON Central Logging Framework — Handles file, console, and SQLite-backed log routing.
"""

import os
import json
import time
import logging
import threading
from logging.handlers import RotatingFileHandler
from typing import Dict, Any, List, Optional

# Track start of logger initialization to compute boot elapsed time
logger_boot_start = time.time()

class UltronFormatter(logging.Formatter):
    """Custom formatter displaying Timestamp, Subsystem, Thread, Level, and Boot Elapsed Time."""
    def __init__(self):
        super().__init__()

    def format(self, record):
        timestamp = time.strftime('%H:%M:%S', time.localtime(record.created))
        millis = int((record.created - int(record.created)) * 1000)
        elapsed = record.created - logger_boot_start
        
        # Extract custom fields or default to SYSTEM
        subsystem = getattr(record, "subsystem", "SYSTEM").upper()
        thread_name = threading.current_thread().name
        level = record.levelname
        message = record.getMessage()
        
        return f"[{timestamp}.{millis:03d}] [{subsystem}] [{thread_name}] [{level}] [Elapsed: {elapsed:.3f}s] {message}"

import queue

class SQLiteLogHandler(logging.Handler):
    """Custom logging handler writing structured log records directly to UME SQLite store asynchronously."""
    def __init__(self, memory_manager):
        super().__init__()
        self.memory = memory_manager
        self.log_queue = queue.Queue()
        self.worker_thread = threading.Thread(target=self._log_worker, name="SQLiteLogHandlerWorker", daemon=True)
        self.worker_thread.start()

    def _log_worker(self):
        while True:
            try:
                record = self.log_queue.get()
                if record is None:
                    break
                log_data = {
                    "message": record.getMessage(),
                    "level": record.levelname,
                    "logger": record.name,
                    "subsystem": getattr(record, "subsystem", "SYSTEM"),
                    "service": getattr(record, "service", "None"),
                    "provider": getattr(record, "provider", "None"),
                    "plugin": getattr(record, "plugin", "None"),
                    "timestamp": record.created
                }
                # Write to UME database log domain
                self.memory.create_record(
                    memory_type="log",
                    title=f"log_{record.levelname}_{record.name}",
                    content=json.dumps(log_data),
                    tags=[record.levelname.lower(), getattr(record, "subsystem", "SYSTEM").lower()]
                )
            except Exception:
                pass

    def emit(self, record):
        try:
            self.log_queue.put(record)
        except Exception:
            pass

class UltronLogger:
    """Wrapper class facilitating event-based publishing and structured subsystems logging."""
    def __init__(self):
        self.logger = logging.getLogger("ultron-agent")
        self.events = None

    def set_event_bus(self, events):
        self.events = events

    def log(self, level: int, subsystem: str, message: str):
        # Inject custom subsystem attribute
        record = self.logger.makeRecord(
            name=self.logger.name,
            level=level,
            fn="",
            lno=0,
            msg=message,
            args=(),
            exc_info=None
        )
        record.subsystem = subsystem
        self.logger.handle(record)

        if self.events:
            self.events.publish("LOG_EMITTED", {
                "level": logging.getLevelName(level),
                "subsystem": subsystem.upper(),
                "message": message,
                "timestamp": time.time()
            })

    def info(self, subsystem: str, message: str):
        self.log(logging.INFO, subsystem, message)

    def warning(self, subsystem: str, message: str):
        self.log(logging.WARNING, subsystem, message)

    def error(self, subsystem: str, message: str):
        self.log(logging.ERROR, subsystem, message)

    def debug(self, subsystem: str, message: str):
        self.log(logging.DEBUG, subsystem, message)

    def critical(self, subsystem: str, message: str):
        self.log(logging.CRITICAL, subsystem, message)

    def health(self) -> dict:
        return {"status": "healthy"}

# Global instances
ultron_logger = UltronLogger()

def setup_logging(memory_manager=None, log_dir: str = "logs", log_level=logging.INFO):
    """Initializes Rotating File, Console, and SQLite database logging with custom Formatter."""
    if not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir)
        except Exception:
            pass

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear existing handlers
    root_logger.handlers = []

    formatter = UltronFormatter()

    # 1. Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 2. Rotating File Handler
    file_path = os.path.join(log_dir, "ultron.log")
    try:
        file_handler = RotatingFileHandler(file_path, maxBytes=10*1024*1024, backupCount=5, encoding="utf-8")
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    except Exception:
        pass

    # 3. SQLite Handler (if memory manager is provided)
    if memory_manager:
        db_handler = SQLiteLogHandler(memory_manager)
        db_handler.setLevel(log_level)
        root_logger.addHandler(db_handler)

    logging.getLogger("ultron-agent").info("Unified Logging Framework initialized.")

def export_logs(memory_manager, output_filepath: str) -> bool:
    """Exports structured SQLite logs to an external JSON/text file."""
    try:
        records = memory_manager.list_records("log", limit=1000)
        logs = []
        for r in records:
            try:
                logs.append(json.loads(r["content"]))
            except Exception:
                logs.append({"raw": r["content"]})
        with open(output_filepath, "w", encoding="utf-8") as f:
            json.dump(logs, f, indent=4)
        return True
    except Exception:
        return False
