from __future__ import annotations

import argparse
from .mac_lab import LAB_PORT, run_mac_lab


def main() -> int:
    p=argparse.ArgumentParser(description='Run the NiceGUI Base Mac live reference/certification application')
    p.add_argument('--host',default='127.0.0.1')
    p.add_argument('--port',type=int,default=LAB_PORT)
    p.add_argument('--show',action='store_true',help='Ask NiceGUI to open the browser automatically')
    a=p.parse_args()
    run_mac_lab(host=a.host,port=a.port,show=a.show)
    return 0

if __name__=='__main__': raise SystemExit(main())
