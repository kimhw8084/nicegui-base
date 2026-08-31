# NiceGUI Base 3.0.0a8 — Linux Runtime & Browser Certification

Run `./setup_linux.sh` to install through the configured company Python index, install the NiceGUI Base wheel with `--no-deps`, verify the exact runtime contract and smoke-test all 22 routes. Setup intentionally excludes browser-certification dependencies and fixed-port requirements.

Use `./run_lab.sh` for the manual lab. Install browser-only dependencies with `./install_certification_deps.sh`, then run `./certify_linux.sh`. Human-review screenshots before `./approve_visual_baseline.sh`.

Stable 3.0.0 promotion requires the exact installed-runtime contract, real 22-route smoke, supported-browser certification and human visual-baseline approval; source tests alone are insufficient.
