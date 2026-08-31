from __future__ import annotations
import argparse
from .live_lab import LAB_PORT,run_live_lab

def main()->int:
    p=argparse.ArgumentParser(description='Run the NiceGUI Base live reference/certification laboratory')
    p.add_argument('--host',default='127.0.0.1');p.add_argument('--port',type=int,default=LAB_PORT);p.add_argument('--root-path',default='');p.add_argument('--show',action='store_true')
    a=p.parse_args();run_live_lab(host=a.host,port=a.port,show=a.show,root_path=a.root_path);return 0

if __name__=='__main__':raise SystemExit(main())
