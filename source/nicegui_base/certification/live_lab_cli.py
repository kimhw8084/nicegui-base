from __future__ import annotations

import argparse

from nicegui_base.workbench.app import WORKBENCH_TITLE, run_workbench

LAB_PORT = 8080


def main() -> int:
    p = argparse.ArgumentParser(description=f'Run the {WORKBENCH_TITLE}')
    p.add_argument('--host', default='127.0.0.1')
    p.add_argument('--port', type=int, default=LAB_PORT)
    p.add_argument('--root-path', default='')
    p.add_argument('--show', action='store_true')
    a = p.parse_args()
    run_workbench(host=a.host, port=a.port, show=a.show, root_path=a.root_path)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
