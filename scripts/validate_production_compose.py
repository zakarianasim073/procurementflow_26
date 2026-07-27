"""Fail closed when production Compose exposes private services or mutable images."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: validate_production_compose.py <compose-config.json>")

    config = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    services = config.get("services", {})
    errors: list[str] = []

    for name, service in services.items():
        ports = service.get("ports") or []
        if name != "nginx" and ports:
            errors.append(f"{name} publishes host ports: {ports}")
        if name == "nginx":
            published = {
                (int(item["published"]), int(item["target"]))
                for item in ports
            }
            if published != {(80, 80), (443, 443)}:
                errors.append(f"nginx public ports are {sorted(published)}")

        image = str(service.get("image") or "")
        if image.endswith(":latest") or (image and ":" not in image.rsplit("/", 1)[-1]):
            errors.append(f"{name} uses a mutable image reference: {image}")

    if errors:
        raise SystemExit("\n".join(errors))

    print("Production Compose exposure and image-pin policy passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
