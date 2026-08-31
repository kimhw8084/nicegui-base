# NiceGUI Base 1.7.2 — Setup Gate Hotfix

NiceGUI Base 1.7.2 separates production-runtime readiness from browser-certification readiness. `setup.sh` uses the runtime profile: Playwright and Pillow are optional and a busy 8080 does not block setup because runtime smoke chooses an ephemeral free port. `run_lab.sh` still requires 8080 to be free because it binds that port. Full `certify.sh` remains strict and requires Playwright 1.62.0, Pillow 12.3.0, supported browser discovery, and a free certification port.
