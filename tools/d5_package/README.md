# NiceGUI Base @D5_PACKAGE_ID@ Team Package

This compact package is the teammate distribution for the immutable NiceGUI
Base @RC_CANDIDATE_ID@ release candidate. It contains the exact wheel,
production dependency pin, launch/setup scripts, integrity identity, and the
acceptance verifier. It does not require the development repository.

## Install

Use Python 3.11, 3.12, or 3.13 in this directory:

```sh
./install_d5.sh
```

The installer preserves an unmanaged `.venv` by moving it to a timestamped
`.venv.rollback.*` directory. It never changes another project or Python
environment.

## Launch

```sh
NGB_D5_PORT=8091 ./launch_d5.sh
```

The terminal prints both the team-package ID and the immutable RC ID.

## Verify

```sh
./verify_d5.sh
```

Verification checks the candidate identity and SHA-256 manifest, site-packages
import provenance, health/readiness, a focused Workbench browser path, project
save/reopen, real chart/table composition, generated ZIP integrity, and an
independent generated-app install/start. It writes one small `D5_RESULT.json`
evidence ZIP to a temporary directory. If Playwright is not available, set
`NGB_D5_BROWSER_PYTHON` to a Python 3.11–3.13 interpreter that has Playwright
and a local Chromium browser.

## Uninstall / recovery

Stop the server, then run:

```sh
./uninstall_d5.sh
```

Only the D5-owned virtual environment is moved out of the active package
directory. The timestamped backup is recoverable, and rerunning
`./install_d5.sh` reinstalls the candidate. An unowned `.venv` is refused.

For a failure, upload the evidence ZIP path printed by `verify_d5.sh` and
classify it as product defect, packaging defect, environment/company
dependency, or user/setup error. Do not treat informational warnings as
blockers unless they affect correctness, security, installability, or this
acceptance path.
