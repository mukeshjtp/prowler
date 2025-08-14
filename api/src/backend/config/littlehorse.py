"""
LittleHorse configuration for Prowler API.

This module configures LittleHorse workflows to replace Celery tasks.
"""
import logging
import os
from typing import Any, Dict, Optional

from config.env import env

logger = logging.getLogger(__name__)

# LittleHorse server configuration
LITTLEHORSE_API_HOST = env("LITTLEHORSE_API_HOST", default="localhost")
LITTLEHORSE_API_PORT = env.int("LITTLEHORSE_API_PORT", default=2023)
LITTLEHORSE_CA_CERT = env("LITTLEHORSE_CA_CERT", default=None)
LITTLEHORSE_CLIENT_CERT = env("LITTLEHORSE_CLIENT_CERT", default=None)
LITTLEHORSE_CLIENT_KEY = env("LITTLEHORSE_CLIENT_KEY", default=None)

# LittleHorse configuration
LITTLEHORSE_CONFIG = {
    "bootstrap_host": LITTLEHORSE_API_HOST,
    "bootstrap_port": LITTLEHORSE_API_PORT,
}

# Add TLS configuration if certificates are provided
if LITTLEHORSE_CA_CERT and LITTLEHORSE_CLIENT_CERT and LITTLEHORSE_CLIENT_KEY:
    LITTLEHORSE_CONFIG.update({
        "ca_cert": LITTLEHORSE_CA_CERT,
        "client_cert": LITTLEHORSE_CLIENT_CERT,
        "client_key": LITTLEHORSE_CLIENT_KEY,
    })

# Task execution configuration
LITTLEHORSE_TASK_TIMEOUT_MS = env.int("LITTLEHORSE_TASK_TIMEOUT_MS", default=3600000)  # 1 hour
LITTLEHORSE_WORKFLOW_TIMEOUT_MS = env.int("LITTLEHORSE_WORKFLOW_TIMEOUT_MS", default=7200000)  # 2 hours

# Migration compatibility settings
LITTLEHORSE_DEADLOCK_ATTEMPTS = env.int("LITTLEHORSE_DEADLOCK_ATTEMPTS", default=5)