"""
DBLogHandler — a Python logging.Handler that writes records to the
AppLog database table so they appear in the Django admin.

Registered via settings.LOGGING (see project_harvey/settings.py).
Uses a safe try/except to avoid recursive logging loops or crashes
if the DB is unavailable during startup.
"""

import logging
import traceback


class DBLogHandler(logging.Handler):
    """Persists log records to the AppLog model."""

    def emit(self, record: logging.LogRecord):
        # Avoid DB writes before Django is fully ready (e.g. during import)
        try:
            from django.db import connection
            if not connection.vendor:
                return
        except Exception:
            return

        try:
            from core.models.app_log import AppLog

            exc_text = ""
            if record.exc_info:
                exc_text = "".join(traceback.format_exception(*record.exc_info))

            # Try to capture Celery task id if inside a task context
            task_id = ""
            try:
                from celery._state import get_current_task
                task = get_current_task()
                if task and task.request:
                    task_id = task.request.id or ""
            except Exception:
                pass

            AppLog.objects.create(
                level=record.levelname,
                logger_name=record.name,
                message=self.format(record),
                module=record.module or "",
                func_name=record.funcName or "",
                line_no=record.lineno,
                task_id=task_id,
                exc_text=exc_text,
            )
        except Exception:
            # Never let the log handler crash the application
            self.handleError(record)
