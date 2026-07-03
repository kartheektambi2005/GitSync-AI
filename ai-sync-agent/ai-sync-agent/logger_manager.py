"""
logger_manager.py
Centralized logging configuration using loguru. Provides separate log
streams for general activity, detected changes, commits, pushes and
failures, plus a console sink for live feedback.
"""

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger

from settings import settings

_CONFIGURED = False


def configure_logging() -> None:
    """Configure loguru sinks. Safe to call multiple times (idempotent)."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    logger.remove()  # remove default handler

    # Console sink - human friendly
    logger.add(
        sys.stdout,
        level=settings.LOG_LEVEL,
        colorize=True,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{extra[component]}</cyan> - <level>{message}</level>"
        ),
    )

    log_dir: Path = settings.LOG_DIR

    # General agent activity
    logger.add(
        log_dir / "agent.log",
        level=settings.LOG_LEVEL,
        rotation=settings.LOG_ROTATION,
        retention=settings.LOG_RETENTION,
        enqueue=True,
        encoding="utf-8",
    )

    # Detected file/folder changes
    logger.add(
        log_dir / "changes.log",
        level="INFO",
        rotation=settings.LOG_ROTATION,
        retention=settings.LOG_RETENTION,
        enqueue=True,
        encoding="utf-8",
        filter=lambda record: record["extra"].get("component") == "watcher",
    )

    # Commits
    logger.add(
        log_dir / "commits.log",
        level="INFO",
        rotation=settings.LOG_ROTATION,
        retention=settings.LOG_RETENTION,
        enqueue=True,
        encoding="utf-8",
        filter=lambda record: record["extra"].get("component") == "git.commit",
    )

    # Pushes
    logger.add(
        log_dir / "pushes.log",
        level="INFO",
        rotation=settings.LOG_ROTATION,
        retention=settings.LOG_RETENTION,
        enqueue=True,
        encoding="utf-8",
        filter=lambda record: record["extra"].get("component") == "git.push",
    )

    # Failures only (any component, WARNING+)
    logger.add(
        log_dir / "failures.log",
        level="WARNING",
        rotation=settings.LOG_ROTATION,
        retention=settings.LOG_RETENTION,
        enqueue=True,
        encoding="utf-8",
    )

    _CONFIGURED = True


def get_logger(component: str):
    """Return a logger bound to a component name for filtered log routing."""
    configure_logging()
    return logger.bind(component=component)
