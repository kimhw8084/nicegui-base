# NiceGUI Base 1.7.2 — Final Certification and Deployment Contract

NiceGUI Base 1.7.2 freezes the seven-phase v1.7 product revamp. Phase 8 adds no product features; it defines the release, dependency, certification and artifact-integrity contract.

## Production dependency contract

Production deployment is company-index-only and requirements-driven:

```bash
python -m pip install -r requirements.txt
```

`requirements.txt` contains exactly the external runtime dependency required by NiceGUI Base:

```text
nicegui==3.15.0
```

There is no public-PyPI fallback, no bundled NiceGUI runtime wheel and no certification tooling in the production requirements file.

Browser/rendered-product certification is intentionally separate:

```bash
python -m pip install -r requirements-certification.txt
```

That file extends production requirements with the exact Playwright and Pillow versions used by the browser/screenshot certification harness.

## Release proof layers

### Build/source proof

The final source tree must pass:

- Python compilation;
- complete pytest suite;
- certification-app validator with zero errors/warnings;
- component-gallery validator with zero errors/warnings;
- NiceGUI 3.15 tagged-source adapter contract;
- 183/183 public visual-component coverage;
- clean wheel build and isolated `--no-deps` install;
- AI/OpenCode seed installation from the clean wheel;
- SBOM and build provenance generation;
- immutable SHA-256 inventory and ZIP round-trip verification.

### Target-company runtime proof

`setup_linux.sh` must execute, in order:

```text
company-index requirements installation
→ NiceGUI Base wheel installation --no-deps
→ nicegui-base runtime-contract
→ nicegui-base doctor --no-require-browser
→ nicegui-base runtime-smoke
→ SETUP COMPLETE
```

`SETUP COMPLETE` is not printed if the installed NiceGUI API contract or real 22-route server smoke fails.

### Rendered/browser proof

The standard browser matrix covers:

- Chrome desktop: all 22 routes;
- Chrome phone: all 22 routes;
- Chrome tablet: key routes plus all ten canonical reference applications;
- light/dark and density-specific acceptance scenarios;
- Edge desktop/phone compatibility smoke when available.

The exhaustive matrix expands Chrome across desktop/tablet/phone in both light and dark modes.

Browser certification includes the geometry, spacing, responsive navigation, control interaction, overlay, DataTable, analytical chart, image-viewer, RCA and reference-application acceptance rules introduced during v1.7 Phases 1–7.

## Visual baseline

No screenshot baseline is pre-approved. A baseline becomes authoritative only after:

1. a passing browser certification run;
2. human inspection of the actual rendered application and screenshots;
3. explicit execution of `approve_visual_baseline.sh`;
4. a subsequent certification run that verifies the SHA-256 locked baseline.

## Claim boundary

Build/source proof is not a substitute for target-company runtime or browser proof. NiceGUI Base 1.7.2 should be described as a production-certification candidate until the target runtime, browser matrix and human visual baseline gates pass.
