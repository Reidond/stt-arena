"""Build production assets."""

from stt_arena_tooling.project import VITE_ASSETS


def main() -> None:
    VITE_ASSETS.build()


if __name__ == "__main__":
    main()
