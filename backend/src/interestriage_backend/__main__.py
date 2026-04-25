from __future__ import annotations

import uvicorn
from interestriage_backend.app import create_app
from interestriage_backend.config import load_config


def main() -> None:
    config = load_config()
    uvicorn.run(create_app(config), host=config.bind_host, port=config.port)


if __name__ == "__main__":
    main()
