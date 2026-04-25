from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import yaml


def _read_compose(path: str) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def test_dev_and_prod_backend_image_tags_match() -> None:
    dev = _read_compose("infra/dev/docker-compose.yml")
    prod = _read_compose("infra/production/docker-compose.yml")

    dev_backend = dev["services"]["backend"]["image"]
    dev_worker = dev["services"]["worker"]["image"]
    prod_backend = prod["services"]["backend"]["image"]
    prod_worker = prod["services"]["worker"]["image"]

    assert dev_backend == dev_worker
    assert prod_backend == prod_worker
    assert dev_backend == prod_backend


def test_dev_and_prod_dashboard_image_tags_match() -> None:
    prod = _read_compose("infra/production/docker-compose.yml")
    dashboard_image = prod["services"]["dashboard"]["image"]

    assert dashboard_image.startswith("interestriage/dashboard:")


def test_backend_image_id_matches_when_docker_is_available() -> None:
    if shutil.which("docker") is None:
        return

    image_tag = "interestriage/backend:stage0-image-parity"
    subprocess.run(
        ["docker", "build", "-f", "infra/Dockerfile.backend", "-t", image_tag, "."],
        check=True,
    )

    image_id = subprocess.check_output(
        ["docker", "image", "inspect", image_tag, "--format", "{{.Id}}"],
        text=True,
    ).strip()

    assert image_id.startswith("sha256:")


def test_evil_server_is_profile_gated_and_not_exposed() -> None:
    dev = _read_compose("infra/dev/docker-compose.yml")
    evil = dev["services"]["evil-server"]

    assert evil.get("profiles") == ["security-tests"]
    assert "ports" not in evil
