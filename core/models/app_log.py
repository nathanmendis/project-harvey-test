from django.db import models


LEVEL_CHOICES = [
    ("DEBUG", "Debug"),
    ("INFO", "Info"),
    ("WARNING", "Warning"),
    ("ERROR", "Error"),
    ("CRITICAL", "Critical"),
]


class AppLog(models.Model):
    """
    Stores application log records in the database so they can be
    viewed and filtered in the Django admin interface.

    Populated by core.logging.DBLogHandler, which is attached to the
    'harvey' logger via settings.LOGGING.
    """

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, db_index=True)
    logger_name = models.CharField(max_length=200, db_index=True)
    message = models.TextField()
    # Optional extras (module / function / line where the log was emitted)
    module = models.CharField(max_length=200, blank=True)
    func_name = models.CharField(max_length=200, blank=True)
    line_no = models.PositiveIntegerField(null=True, blank=True)
    # If the log was emitted from a Celery task, capture the task id
    task_id = models.CharField(max_length=200, blank=True, db_index=True)
    # Full exception traceback if any
    exc_text = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "App Log"
        verbose_name_plural = "App Logs"

    def __str__(self):
        return f"[{self.level}] {self.created_at:%Y-%m-%d %H:%M:%S} — {self.message[:80]}"
