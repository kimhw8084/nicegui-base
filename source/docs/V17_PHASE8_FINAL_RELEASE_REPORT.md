# Phase 8 — NiceGUI Base 1.7.1 Final Certification & Production Packaging

Phase 8 freezes the seven-phase v1.7 product revamp and converts it into one production/certification handoff. No new product behavior is introduced in this phase.

## Frozen product surface

- Framework: NiceGUI Base 1.7.1
- Runtime contract: NiceGUI 3.15.0
- Live routes: 22
- Canonical reference applications: 10
- Public visual integrations: 183/183
- Public root API entries: 748
- Governed CSS: 224,789 bytes
- Semantic icons / illustrations: 143 / 12

## Source/build proof

- 544/544 automated tests pass.
- Python compilation passes.
- Certification application: 0 errors / 0 warnings.
- Component gallery: 0 errors / 0 warnings.
- Offline certification: 12 PASS / 1 expected runtime-unavailable warning / 0 FAIL.
- NiceGUI source-contract issues: 0.
- Exact wheel clean install: 10 PASS / 1 expected runtime-unavailable warning / 0 FAIL.
- AI/OpenCode seed installation from the clean wheel succeeds.

## Production dependency model

Production deployment resolves only `requirements.txt` through the company-approved package index. The file contains exactly `nicegui==3.15.0`. NiceGUI Base itself is installed from the bundled internal wheel with `--no-deps`; no public-PyPI or bundled NiceGUI fallback is allowed.

Browser certification dependencies are isolated in `requirements-certification.txt` and are not part of the production runtime contract.

## Runtime and browser boundary

The build sandbox does not contain NiceGUI or a supported browser runtime. This is recorded explicitly rather than treated as a pass. In the company environment, setup must pass the installed NiceGUI API contract and a real browserless 22-route server smoke before printing `SETUP COMPLETE`.

Rendered-product certification remains a later gate: supported-browser matrix, human screenshot review and explicit SHA-256 locked baseline approval.
