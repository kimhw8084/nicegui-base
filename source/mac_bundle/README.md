# NiceGUI Base 3.0.0a8 — macOS Runtime & Browser Certification

Run `./setup_mac.sh` for production-runtime installation/proof and `./run_lab.sh` for the manual lab. Setup intentionally does not require Playwright/Pillow or a free fixed port.

Install browser-only dependencies with `./install_certification_deps.sh`, then run `./certify_mac.sh` (optionally `--exhaustive`). Human-review screenshots before `./approve_visual_baseline.sh`. Stable 3.0.0 promotion requires these live gates; source tests alone are insufficient.
