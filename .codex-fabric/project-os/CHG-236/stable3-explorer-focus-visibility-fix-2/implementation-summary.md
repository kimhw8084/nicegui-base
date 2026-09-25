# CHG-236 FIX-2 implementation

The Workbench singleton responsive synchronizer now uses native focus scrolling and a bounded reveal repair for the actual visual target (`.q-field` when present). It measures focus-ring clearance, uses nearest scrolling, corrects only the needed viewport delta, accounts for fixed/sticky occlusion, and schedules four animation-frame checks for breakpoint reflow. Pointer, wheel, touch, and key activity cancels deferred reveal so user-owned movement/focus is preserved. No route-specific scripts or duplicate refinement subtree were introduced.

Product files changed relative to FIX-1: `source/nicegui_base/workbench/app.py`, `source/tests/test_workbench_chg106.py`, and `source/tests/test_workbench_chg236.py`. FIX-1 search/no-results implementation and semantics remain unchanged.
