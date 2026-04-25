from __future__ import annotations

from os import getenv


def describe_limits() -> dict[str, str]:
    return {
        "cpu_quota": getenv("PARSER_CPU_QUOTA", "0.50"),
        "memory_limit": getenv("PARSER_MEMORY_LIMIT", "256m"),
        "max_output_bytes": getenv("PARSER_MAX_OUTPUT_BYTES", "2000000"),
    }


if __name__ == "__main__":
    limits = describe_limits()
    print(
        "parser-sandbox ready "
        f"cpu={limits['cpu_quota']} mem={limits['memory_limit']} "
        f"output={limits['max_output_bytes']}"
    )
