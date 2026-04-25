from __future__ import annotations

import os
import socket

import pytest

pytestmark = pytest.mark.integration


@pytest.mark.skipif(not os.getenv("RUN_SSRF_TESTS"), reason="SSRF harness is not enabled")
def test_evil_server_profile_is_intentional() -> None:
    # This test intentionally uses an env-gate to ensure the hostile service is never
    # started by default workflows.
    hostname = os.getenv("EVIL_SERVER_HOST", "evil-server")
    port = int(os.getenv("EVIL_SERVER_PORT", "8081"))

    with socket.create_connection((hostname, port), timeout=3):
        assert True
