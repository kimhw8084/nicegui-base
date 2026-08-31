# NiceGUI Base v1.7 Product Constitution — Phase 1

## Reference DNA

NiceGUI Base uses Apple × Linear as the default product foundation, Stripe for information architecture, Raycast for interaction discipline, and Robinhood/Datadog only where analytical direct manipulation benefits engineering work.

This is a principle reference, not a visual clone. NiceGUI is the Python runtime/state/event transport. NiceGUI Base owns visible geometry, styling, responsive behavior, icons, interaction anatomy, and application identity.

## Non-negotiable shell laws

1. Application identity and current-view identity are separate. The fixed header owns the application title; `PageHeader` owns the current view.
2. There is one responsive navigation state machine: expanded desktop, icon-only desktop, or temporary mobile overlay.
3. Desktop has one collapse control, inside the navigation rail. No desktop menu button is rendered beside the application title.
4. Below 900px the desktop rail becomes non-interactive and one navigation trigger appears in the header action cluster.
5. The mobile navigation overlay is Company-owned DOM; it does not use Quasar drawer geometry.
6. Resizing back to desktop automatically closes temporary mobile navigation and restores the persisted desktop rail state.
7. Compact sidebar footer controls are fixed icon-only targets with hover/native hints; labels never squeeze into compact width.
8. Main content occupies exactly the viewport width not owned by the desktop rail. Page gutters provide breathing room; shell offsets never do.
9. The view title begins exactly one page gutter below the application header boundary.
10. Settings and profile triggers expose structured application/user surfaces. Visible shell controls must not exist solely to produce a toast.

## Phase 1 geometry

- Header height: 60px
- Expanded sidebar: 256px
- Compact sidebar: 64px
- Desktop page gutter: 20px
- Mobile page gutter: 16px
- Responsive navigation breakpoint: 900px

These values are governed tokens, not per-page choices.

## Environment badges

Environment labels use a neutral readable surface and semantic status dot. Development, staging and production do not place low-contrast colored text over saturated backgrounds.

## Dependency / deployment law

Production deployment is requirements-driven and company-index-only.

`requirements.txt` contains production runtime dependencies only. Browser certification dependencies are isolated in `requirements-certification.txt`. Setup installs `requirements.txt` first, then installs the NiceGUI Base wheel with `--no-deps`, preventing the wheel from silently selecting another package source or optional dependency set.

No production/public-PyPI fallback is part of the deployment path.
