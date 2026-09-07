# NiceGUI Base @CANDIDATE_ID@

This is a self-contained release-candidate bundle. It contains the exact
NiceGUI Base wheel built from the authoritative source tree, production dependency
pinning, integrity manifests, provenance, and the qualification evidence.

## Install and run

From this directory, in a clean shell:

```sh
./install_rc.sh
./run_rc.sh
```

The normal Reference Explorer port is 8091. Set `NGB_RC_PORT` or pass launch options to
choose another free port. The scripts never kill an existing process and the
state/storage contract remains owned by NiceGUI Base.

## Recovery / rollback

Stop the running server, then run:

```sh
./rollback_rc.sh
```

That command only moves the RC-owned virtual environment to a timestamped
`.venv.rollback.*` directory. Re-run `./install_rc.sh` to recreate the RC
environment. No repository or unrelated user data is modified.

## Evidence

`SHA256SUMS.txt`, `BUILD_PROVENANCE.json`, `SOURCE_PACKAGE_SHA256.json`,
`WHEEL_SOURCE_VERIFICATION.json`, and `QUALIFICATION_SUMMARY.json` are the
current candidate authority. Browser screenshots and logs are kept in the
adjacent evidence directory named in `QUALIFICATION_SUMMARY.json`.
