from __future__ import annotations

import argparse
from pathlib import Path
from nicegui_base.ai.scaffold import install_ai_materials


def main(argv: list[str] | None = None) -> int:
    parser=argparse.ArgumentParser(description='Install NiceGUI Base Gemma/OpenCode guidance into an application workspace.')
    parser.add_argument('path', nargs='?', default='.')
    parser.add_argument('--overwrite', action='store_true')
    args=parser.parse_args(argv)
    written=install_ai_materials(Path(args.path), overwrite=args.overwrite)
    print(f'NiceGUI Base AI materials: {len(written)} files written.')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
