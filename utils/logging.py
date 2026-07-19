"""
utils/logging.py — SSE log queue management
"""

import time
import queue

# ── Log Queue (SSE) ──────────────────────────────────────────
log_queues: dict = {}


def emit_log(session_id: str, log_type: str, message: str):
    """Send a log message to the frontend SSE stream."""
    if session_id in log_queues:
        log_queues[session_id].put({
            "type":      log_type,
            "message":   message,
            "timestamp": time.time(),
        })


def create_session(session_id: str):
    log_queues[session_id] = queue.Queue()


def cleanup_session(session_id: str):
    log_queues.pop(session_id, None)
