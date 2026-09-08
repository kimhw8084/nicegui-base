<!-- G25_CANONICAL_HUMAN_LAUNCHER -->
# Start NiceGUI Base

For a company source checkout, there is one human starting command:

```bash
python run_nicegui_base.py
```

That file launches the **NiceGUI Base Reference Explorer**. It does not contain a second
copy of the application; it delegates to the canonical `nicegui_base.workbench.app.run_workbench`
authority.

Default URL: `http://127.0.0.1:8091`

Before handing the repository to another environment, you can verify the interpreter and
runtime contract without starting a server:

```bash
python run_nicegui_base.py --check
```

Supported environment variables:

- `NICEGUI_BASE_HOST` — default `127.0.0.1`
- `NICEGUI_BASE_PORT` — default `8091`
- `NICEGUI_BASE_SHOW` — `true/false`, default `false`
- `NICEGUI_BASE_STORAGE_SECRET` — optional stable NiceGUI storage secret

The launcher uses the **same `python` interpreter you invoke**. It never creates a virtual
environment, installs packages, changes interpreters, or silently modifies the repository.
It requires Python `>=3.11,<3.14` and exactly `nicegui==3.15.0`.

---

# NiceGUI Base v3.0.0a8 — Wave 77 Authoritative Source

This is the authoritative source tree for **Wave 77 — Final Release-Candidate Consolidation, Authority Audit & Stable Qualification Handoff**.

## Authority

`source/` remains the only code authority. Waves 59–76 retain every existing data, analysis, semiconductor, certification, promotion, publication, stability, rollback, renewal, longitudinal and review truth boundary. Wave 77 creates no parallel evidence authority.

Read before qualification:
1. `RELEASE_MANIFEST.json`
2. `PHASE_77_V300A8_FINAL_RELEASE_CANDIDATE_CONSOLIDATION_AUTHORITY_AUDIT_STABLE_QUALIFICATION_HANDOFF_REPORT.json`
3. `FINAL_RELEASE_CANDIDATE_AUDIT.json`
4. `STABLE_QUALIFICATION_HANDOFF.json`
5. `PUBLIC_API_COMPATIBILITY_WAVE77.json`
6. `CERTIFICATION_REPORT.json`
7. `WHEEL_INTEGRITY.json`
8. `docs/FINAL_RELEASE_CANDIDATE_STABLE_QUALIFICATION_HANDOFF.md`

`SOURCE_COMPLETE` is not stable `3.0.0` certification. Installed target runtime, real server/WebSocket, approved company provider/data benchmark, corporate browser/publisher, human visual baseline, reviewer authority and real deployment/publication/operations evidence remain PENDING until actually executed and verified.
