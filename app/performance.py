"""Low-overhead request profiling and background-job registry."""

import time

from flask import Flask, g, request


def init_performance(app: Flask):
    @app.before_request
    def start_timer():
        g.request_started_at = time.perf_counter()

    @app.after_request
    def finish(response):
        elapsed = (
            time.perf_counter() - g.get("request_started_at", time.perf_counter())
        ) * 1000
        response.headers.setdefault("X-Response-Time", f"{elapsed:.1f}ms")
        if elapsed > app.config.get("SLOW_REQUEST_MS", 500):
            app.logger.warning("Slow request %s %.1fms", request.path, elapsed)
        if request.endpoint == "static":
            response.cache_control.public = True
            response.cache_control.max_age = 604800
        return response


class JobRegistry:
    """Synchronous foundation that can later be backed by Celery/RQ."""

    def __init__(self):
        self._jobs = {}

    def register(self, name, callback):
        self._jobs[name] = callback

    def run(self, name):
        if name not in self._jobs:
            raise KeyError(name)
        return self._jobs[name]()

    @property
    def names(self):
        return tuple(sorted(self._jobs))


jobs = JobRegistry()
