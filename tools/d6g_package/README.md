# NiceGUI Base @D6G_ID@ team distribution

This is the compact golden-reference distribution for `@D6G_ID@`. It is
self-contained: use it from this directory, a clean directory, or a teammate
machine without the development checkout.

## Install and launch

```bash
./install.sh
./launch.sh
```

The default Workbench port is 8091. Set `NGB_D6G_PORT` to choose another
available port. The launch banner prints the candidate identity.

## Verify

```bash
./verify.sh
```

Verification checks hashes, installed import provenance, pip consistency,
health/readiness, graceful shutdown, the Reference Explorer surface, and
independently gates/starts one canonical pattern app and one semiconductor
recipe app. It writes one small evidence archive and returns nonzero on any
failure. If Playwright is not installed, set
`NGB_D6G_BROWSER_PYTHON` to a Python 3.11–3.13 interpreter that has the
approved browser test tooling.

## Rollback / uninstall

Stop `launch.sh`, then run:

```bash
./rollback.sh
```

Only the D6G-owned `.venv` is moved to a timestamped recovery directory.
Rerun `./install.sh` to reinstall. Unowned environments are refused and no
other NiceGUI project or user file is touched.

See `ACCEPTANCE_CHECKLIST.md`, `DESIGN_AGENT_QUICKSTART.md`,
`RC_IDENTITY.json`, `BUILD_PROVENANCE.json`, and `SHA256SUMS.txt` for the
candidate contract and exact hashes.
