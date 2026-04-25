from __future__ import annotations

import json
import subprocess
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "dist" / "sbom"


def load_uv_components() -> list[dict[str, str]]:
    lock_data = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    components: list[dict[str, str]] = []

    for package in lock_data.get("package", []):
        components.append(
            {
                "name": package["name"],
                "version": package["version"],
                "type": "python",
            }
        )

    return components


def load_npm_components() -> list[dict[str, str]]:
    lock_data = json.loads((ROOT / "package-lock.json").read_text(encoding="utf-8"))
    keyed: dict[tuple[str, str], dict[str, str]] = {}

    for package_path, meta in lock_data.get("packages", {}).items():
        if package_path == "":
            continue

        name = meta.get("name") or package_path.rsplit("node_modules/", maxsplit=1)[-1]
        version = meta.get("version", "unknown")
        key = ("npm", name)
        current = keyed.get(key)

        if current is None or (current["version"] == "unknown" and version != "unknown"):
            keyed[key] = {"name": name, "version": version, "type": "npm"}

    return list(keyed.values())


def git_commit() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    document = {
        "schema": "interestriage-stage0-sbom-v1",
        "generated_from_commit": git_commit(),
        "components": sorted(
            [*load_uv_components(), *load_npm_components()],
            key=lambda component: (component["type"], component["name"]),
        ),
    }

    (OUT_DIR / "sbom.json").write_text(json.dumps(document, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
