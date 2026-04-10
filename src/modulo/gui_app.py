from __future__ import annotations

import argparse
import os

from modulo.gui.controller import GuiAppController
from modulo.gui.window import launch_gui


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Launch the Modulo GUI shell.",
    )
    parser.add_argument(
        "--platform-url",
        default=os.getenv("MODULO_PLATFORM_URL", ""),
        help=(
            "Optional shared platform target URL to seed into the GUI Debug target, "
            "for example https://modulo.grinningfrog.com."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    controller = GuiAppController.build_default(
        platform_target_url=args.platform_url,
    )
    raise SystemExit(launch_gui(controller))


if __name__ == "__main__":
    main()
