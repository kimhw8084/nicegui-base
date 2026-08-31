# NiceGUI Base 2.0.0rc2 — Source Completion Report

RC2 closes the remaining source-level blockers identified after `2.0.0rc1`. It does not redefine the v1.7.3 product/runtime constitution and does not claim target-runtime or visual certification that cannot be executed in the build sandbox.

## Completed in RC2

| Area | RC2 result | Release effect |
|---|---|---|
| Typography/motion | Font size, line height, weight, duration and easing scales are token-governed; ECharts uses the Python authority | Screenshot/hotfix typography and animation drift becomes machine-detectable |
| Geometry/density | Core shell/layout/control/table/density variables are generated from one token authority | Downstream CSS load order can no longer silently redefine the primary constitution |
| Effective geometry preservation | 60px header, 256/64px rail, 20→16px gutter behavior and approved compact control geometry retained | Refactor changes authority, not the approved visual result |
| Release synchronization | Current RC identities synchronize across manifests/docs/AI guides/platform bundles | Release version drift becomes a release failure |
| Stable target preservation | RC-sync only replaces `2.0.0rcN`; intentional final target `2.0.0` is immutable | Final-promotion language cannot be accidentally rewritten to an RC |
| Runtime identifiers | Lab version, storage-secret namespace and smoke user-agent derive from `FRAMEWORK_VERSION` | No hidden historical release strings in runtime behavior |
| Source evidence | Packaged certification manifest is refreshed before pytest and source certification | Certification metadata is checked as part of the exact tree it describes |
| Regression suite | 601 tests | All inherited and new source contracts pass |
| Governance | 0 errors / 0 warnings | Release/design/API/accessibility contracts are internally consistent |
| Visual coverage | 183/183 | Every public visual integration remains accounted for in the live lab |

## Intentionally pending target gates

The build sandbox has no NiceGUI installation and cannot substitute source inspection for a production target. Final `2.0.0` still requires:

- exact installed NiceGUI 3.15.0 runtime contract;
- real 22-route server smoke;
- Chrome/Edge browser matrix at 390/430/768/1024/1280/1440 plus required states;
- zero NiceGUI Base browser-console errors/unhandled promise failures;
- geometry/interaction/overlay/table/chart and 14 historical screenshot-regression certification;
- human visual-baseline review and hash lock;
- required company target-platform evidence.

Any target failure remains a release blocker and must be fixed systemically with regression coverage before the stable `2.0.0` stamp.
