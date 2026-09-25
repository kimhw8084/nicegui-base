from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright


BASE_URL = "http://127.0.0.1:49762"
OUT = Path("/tmp/chg236-fix2-evidence")
SCREENSHOTS = OUT / "screenshots"
SCRIPT_SOURCE = (Path.cwd() / "source/nicegui_base/workbench/app.py").read_text(encoding="utf-8")
SCRIPT_START = SCRIPT_SOURCE.index("_EXPLORER_REFINE_RESPONSIVE_SCRIPT = r'''<script>")
SCRIPT_START = SCRIPT_SOURCE.index("<script>", SCRIPT_START) + len("<script>")
SCRIPT_END = SCRIPT_SOURCE.index("</script>'''", SCRIPT_START)
RESPONSIVE_SCRIPT = SCRIPT_SOURCE[SCRIPT_START:SCRIPT_END]

VISIBILITY_READY = r"""() => {
  const element=document.activeElement;
  const details=document.querySelector('.cui-explorer-refine');
  if (!element || !details || !details.contains(element)) return false;
  const visual=element.closest('.q-field') || element;
  const rect=element.getBoundingClientRect();
  const visible=visual.getBoundingClientRect();
  const style=getComputedStyle(visual);
  const clearance=style.outlineStyle==='none' ? 0 :
    Math.max(0,parseFloat(style.outlineWidth)||0)+Math.max(0,parseFloat(style.outlineOffset)||0);
  const tolerance=1;
  const hit=document.elementFromPoint(visible.left+visible.width/2,visible.top+visible.height/2);
  const ownsCenter=Boolean(hit && (hit===visual || visual.contains(hit)));
  const indicator=element.matches(':focus-visible') &&
    ((style.outlineStyle!=='none' && parseFloat(style.outlineWidth)>0) || style.boxShadow!=='none');
  const eligible=element.isConnected && !element.disabled &&
    !element.matches(':disabled,[disabled]') &&
    !element.closest('[hidden],[inert],[aria-hidden="true"],[aria-disabled="true"],.q-field--disabled') &&
    getComputedStyle(element).display!=='none' && getComputedStyle(element).visibility!=='hidden' &&
    element.getClientRects().length>0;
  return eligible && rect.right>0 && rect.bottom>0 && rect.left<innerWidth && rect.top<innerHeight &&
    visible.left>=clearance-tolerance && visible.top>=clearance-tolerance && visible.right<=innerWidth-clearance+tolerance && visible.bottom<=innerHeight-clearance+tolerance &&
    ownsCenter && indicator && document.documentElement.scrollWidth<=innerWidth;
}"""

VISIBILITY_DIAGNOSTIC = r"""() => {
  const element=document.activeElement, details=document.querySelector('.cui-explorer-refine');
  const visual=element.closest('.q-field')||element, rect=element.getBoundingClientRect(), visible=visual.getBoundingClientRect();
  const style=getComputedStyle(visual), activeStyle=getComputedStyle(element);
  const clearance=style.outlineStyle==='none'?0:(parseFloat(style.outlineWidth)||0)+(parseFloat(style.outlineOffset)||0);
  const hit=document.elementFromPoint(visible.left+visible.width/2,visible.top+visible.height/2);
  return {tag:element.tagName,id:element.id,label:element.getAttribute('aria-label'),connected:element.isConnected,disabled:element.disabled,hidden:element.closest('[hidden],[inert],[aria-hidden="true"],[aria-disabled="true"],.q-field--disabled')?.className||null,display:activeStyle.display,visibility:activeStyle.visibility,clientRects:element.getClientRects().length,rect:{top:rect.top,right:rect.right,bottom:rect.bottom,left:rect.left},visible:{top:visible.top,right:visible.right,bottom:visible.bottom,left:visible.left},clearance,hit:hit?{tag:hit.tagName,id:hit.id,cls:hit.className}:null,owns:Boolean(hit&&(hit===visual||visual.contains(hit))),focusVisible:element.matches(':focus-visible'),outline:style.outline,shadow:style.boxShadow,scroll:{x:scrollX,y:scrollY},viewport:{width:innerWidth,height:innerHeight},scrollWidth:document.documentElement.scrollWidth,detailsOpen:details?.open};
}"""

FOCUS_EVIDENCE = r"""(before) => {
  const element=document.activeElement;
  const details=document.querySelector('.cui-explorer-refine');
  const summary=details.querySelector(':scope > summary');
  const visual=element.closest('.q-field') || element;
  const rect=element.getBoundingClientRect();
  const visualRect=visual.getBoundingClientRect();
  const summaryRect=summary.getBoundingClientRect();
  const style=getComputedStyle(visual);
  const activeStyle=getComputedStyle(element);
  const clearance=style.outlineStyle==='none' ? 0 :
    Math.max(0,parseFloat(style.outlineWidth)||0)+Math.max(0,parseFloat(style.outlineOffset)||0);
  const tolerance=1;
  const cx=visualRect.left+visualRect.width/2;
  const cy=visualRect.top+visualRect.height/2;
  const hit=document.elementFromPoint(cx,cy);
  const eligible=element.isConnected && !element.disabled &&
    !element.matches(':disabled,[disabled]') &&
    !element.closest('[hidden],[inert],[aria-hidden="true"],[aria-disabled="true"],.q-field--disabled') &&
    activeStyle.display!=='none' && activeStyle.visibility!=='hidden' && element.getClientRects().length>0;
  return {
    url:location.href,
    viewport:{width:innerWidth,height:innerHeight},
    scroll:{x:scrollX,y:scrollY},
    beforeTransition:before,
    scrollDelta:{x:scrollX-before.scrollX,y:scrollY-before.scrollY},
    active:{tag:element.tagName,id:element.id,role:element.getAttribute('role'),ariaLabel:element.getAttribute('aria-label'),text:(element.innerText||element.textContent||'').trim(),rect:{top:rect.top,right:rect.right,bottom:rect.bottom,left:rect.left,width:rect.width,height:rect.height}},
    visualRect:{top:visualRect.top,right:visualRect.right,bottom:visualRect.bottom,left:visualRect.left,width:visualRect.width,height:visualRect.height},
    viewportChecks:{eligible,intersects:rect.right>0&&rect.bottom>0&&rect.left<innerWidth&&rect.top<innerHeight,fullyVisible:rect.left>=-tolerance&&rect.top>=-tolerance&&rect.right<=innerWidth+tolerance&&rect.bottom<=innerHeight+tolerance,visualFullyVisible:visualRect.left>=clearance-tolerance&&visualRect.top>=clearance-tolerance&&visualRect.right<=innerWidth-clearance+tolerance&&visualRect.bottom<=innerHeight-clearance+tolerance,centerOwned:Boolean(hit&&(hit===visual||visual.contains(hit))),horizontalOverflow:document.documentElement.scrollWidth>innerWidth,documentScrollWidth:document.documentElement.scrollWidth,tolerancePx:tolerance},
    focusIndicator:{keyboardVisible:element.matches(':focus-visible'),outline:style.outline,boxShadow:style.boxShadow,outlineOffset:style.outlineOffset,clearance},
    shellHeader:(()=>{const header=document.querySelector('.q-header,header,[role="banner"]');if(!header)return null;const r=header.getBoundingClientRect();return{tag:header.tagName,id:header.id,className:header.className,top:r.top,bottom:r.bottom,position:getComputedStyle(header).position}})(),
    centerPoint:{x:cx,y:cy,hit:hit?{tag:hit.tagName,id:hit.id,className:typeof hit.className==='string'?hit.className:'',ariaLabel:hit.getAttribute('aria-label')}:null},
    refinement:{open:details.open,summaryRect:{top:summaryRect.top,right:summaryRect.right,bottom:summaryRect.bottom,left:summaryRect.left,width:summaryRect.width,height:summaryRect.height},summaryVisible:getComputedStyle(summary).display!=='none'&&summary.getClientRects().length>0}
  };
}"""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def ready_gallery(page, route: str) -> None:
    page.goto(f"{BASE_URL}{route}", wait_until="domcontentloaded", timeout=30000)
    page.wait_for_selector(".cui-explorer-controls", timeout=30000)
    page.wait_for_function("Boolean(window.__niceguiBaseExplorerRefineResponsive)", timeout=10000)


def wait_visible_handoff(page, *, expected_tag: str, expected_id: str | None = None) -> None:
    page.wait_for_function(
        f"({VISIBILITY_READY})() && document.activeElement.tagName === {json.dumps(expected_tag)} && "
        + (f"document.activeElement.id === {json.dumps(expected_id)}" if expected_id else "true"),
        timeout=10000,
    )
    page.evaluate("() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))")
    try:
        page.wait_for_function(f"({VISIBILITY_READY})()", timeout=5000)
    except Exception as error:
        diagnostic = page.evaluate(f"({VISIBILITY_DIAGNOSTIC})()")
        raise AssertionError(f"handoff failed after settle: {diagnostic}") from error
    require(page.evaluate(f"({VISIBILITY_READY})()"), "handoff target did not become fully perceivable")


def focus_record(page, *, before: dict, expected_open: bool, screenshot: str | None = None) -> dict:
    result = page.evaluate(FOCUS_EVIDENCE, before)
    require(result["viewportChecks"]["eligible"], "active element is hidden or ineligible")
    require(result["viewportChecks"]["intersects"], "active element is outside the CSS viewport")
    require(result["viewportChecks"]["fullyVisible"], "active focus rect is clipped")
    require(result["viewportChecks"]["visualFullyVisible"], "visible focus authority or ring is clipped")
    require(result["viewportChecks"]["centerOwned"], "focus authority center is occluded")
    require(not result["viewportChecks"]["horizontalOverflow"], "document has horizontal overflow")
    require(result["focusIndicator"]["keyboardVisible"], "browser does not report keyboard focus-visible")
    require(bool(result["focusIndicator"]["outline"] != "none" or result["focusIndicator"]["boxShadow"] != "none"), "visible focus indicator is missing")
    require(result["refinement"]["open"] is expected_open, "Refine disclosure state is incorrect")
    if screenshot:
        path = SCREENSHOTS / screenshot
        page.screenshot(path=str(path), full_page=False)
        result["screenshot"] = {"name": screenshot, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    return result


def gallery_projection(page) -> dict:
    return page.evaluate(r"""() => {
  const section=document.querySelector('.cui-explorer-controls');
  const search=section?.querySelector('[data-explorer-search]');
  const details=section?.querySelector('.cui-explorer-refine');
  const inputs=section?.querySelectorAll('input[aria-label="Search"]')||[];
  const cards=[...document.querySelectorAll('.cui-explorer-card[data-entry-key]')];
  const empty=document.querySelector('.cui-workbench-preview-empty[role="status"][aria-live="polite"]');
  const status=[...document.querySelectorAll('.cui-workbench-note')].map(e=>e.textContent.trim()).find(t=>/^\d+ of \d+ visible/.test(t))||null;
  return {url:location.href,searchCount:inputs.length,searchOutsideRefine:Boolean(search&&details&&!details.contains(search)),refineCount:document.querySelectorAll('.cui-explorer-refine').length,cardCount:cards.length,entryKeys:cards.map(e=>e.getAttribute('data-entry-key')),status,emptyStatus:empty?empty.textContent.trim():null,emptyRole:empty?.getAttribute('role')||null,emptyAriaLive:empty?.getAttribute('aria-live')||null,viewport:{width:innerWidth,height:innerHeight},scroll:{x:scrollX,y:scrollY},horizontalOverflow:document.documentElement.scrollWidth>innerWidth};
}""")


def record_scenario(results: list[dict], name: str, action) -> None:
    try:
        detail = action()
        results.append({"scenario": name, "status": "PASS", "evidence": detail})
    except Exception as error:
        results.append({"scenario": name, "status": "FAIL", "error": f"{type(error).__name__}: {error}"})
        raise


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    SCREENSHOTS.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []
    focus_records: dict[str, dict] = {}
    runtime_errors: list[str] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900}, reduced_motion="reduce")
        context.add_init_script(r"""(() => {
  const original=MediaQueryList.prototype.addEventListener;
  window.__refineChangeListeners=0;
  MediaQueryList.prototype.addEventListener=function(type,listener,options){
    if(type==='change'&&this.media==='(max-width: 680px)')window.__refineChangeListeners+=1;
    return original.call(this,type,listener,options);
  };
  const NativeObserver=window.MutationObserver;
  window.__observerCreations=0;
  window.MutationObserver=class extends NativeObserver{constructor(callback){super(callback);window.__observerCreations+=1;}};
})();""")
        page = context.new_page()
        page.on("pageerror", lambda error: runtime_errors.append(str(error)))
        page.on("console", lambda message: runtime_errors.append(message.text) if message.type == "error" else None)
        ready_gallery(page, "/components")
        page.keyboard.press("Tab")
        family = page.locator('.cui-explorer-refine__body .q-select__focus-target[aria-label="Family"]')
        summary = page.locator(".cui-explorer-refine > summary")

        def mobile_handoff() -> dict:
            require(page.locator(".cui-explorer-refine").evaluate("e=>e.open"), "desktop Refine did not start open")
            require(not summary.is_visible(), "desktop summary unexpectedly visible")
            family.focus()
            page.evaluate("window.scrollTo(0,0)")
            before = page.evaluate("({scrollX,scrollY,viewport:{width:innerWidth,height:innerHeight},familyTop:document.activeElement.getBoundingClientRect().top,detailsOpen:document.querySelector('.cui-explorer-refine').open})")
            require(before["familyTop"] > before["viewport"]["height"], "precondition failed: Family remained in mobile viewport")
            page.set_viewport_size({"width": 390, "height": 844})
            page.wait_for_function("!document.querySelector('.cui-explorer-refine').open && document.activeElement.tagName==='SUMMARY'", timeout=10000)
            wait_visible_handoff(page, expected_tag="SUMMARY")
            return focus_record(page, before=before, expected_open=False, screenshot="explorer-fix-breakpoint-mobile-summary-focused.png")

        record_scenario(results, "FOCUS_VISIBILITY_MOBILE_HANDOFF", mobile_handoff)
        focus_records["desktop_to_mobile"] = results[-1]["evidence"]

        def desktop_handoff() -> dict:
            summary.click()
            page.wait_for_function("document.querySelector('.cui-explorer-refine').open", timeout=5000)
            family.focus()
            page.evaluate("window.scrollTo(0,0)")
            before = page.evaluate("({scrollX,scrollY,viewport:{width:innerWidth,height:innerHeight},familyTop:document.activeElement.getBoundingClientRect().top,detailsOpen:document.querySelector('.cui-explorer-refine').open})")
            require(before["familyTop"] > before["viewport"]["height"], "precondition failed: Family remained in desktop viewport")
            page.set_viewport_size({"width": 1440, "height": 900})
            page.wait_for_function("!matchMedia('(max-width: 680px)').matches && document.querySelector('.cui-explorer-refine').open && document.activeElement.getAttribute('aria-label')==='Family'", timeout=10000)
            wait_visible_handoff(page, expected_tag="INPUT", expected_id=family.get_attribute("id"))
            return focus_record(page, before=before, expected_open=True, screenshot="explorer-fix-breakpoint-desktop-family-restored.png")

        record_scenario(results, "FOCUS_VISIBILITY_DESKTOP_HANDOFF", desktop_handoff)
        focus_records["mobile_to_desktop"] = results[-1]["evidence"]

        def repeat_and_external() -> dict:
            page.evaluate("window.__fix2OriginalState=window.__niceguiBaseExplorerRefineResponsive")
            responsive = page.evaluate("({identity:window.__niceguiBaseExplorerRefineResponsive,listeners:window.__refineChangeListeners,observers:window.__observerCreations})")
            page.add_script_tag(content=RESPONSIVE_SCRIPT)
            require(page.evaluate("window.__niceguiBaseExplorerRefineResponsive === window.__fix2OriginalState"), "responsive synchronizer identity changed on reinjection")
            cycles = []
            for index in range(3):
                family.focus()
                page.evaluate("window.scrollTo(0,0)")
                before_mobile = page.evaluate("({scrollX,scrollY})")
                page.set_viewport_size({"width": 390, "height": 844})
                page.wait_for_function("!document.querySelector('.cui-explorer-refine').open && document.activeElement.tagName==='SUMMARY'", timeout=10000)
                wait_visible_handoff(page, expected_tag="SUMMARY")
                mobile = focus_record(page, before=before_mobile, expected_open=False)
                summary.click()
                family.focus()
                page.evaluate("window.scrollTo(0,0)")
                before_desktop = page.evaluate("({scrollX,scrollY})")
                page.set_viewport_size({"width": 1440, "height": 900})
                page.wait_for_function("document.querySelector('.cui-explorer-refine').open && document.activeElement.getAttribute('aria-label')==='Family'", timeout=10000)
                wait_visible_handoff(page, expected_tag="INPUT", expected_id=family.get_attribute("id"))
                desktop = focus_record(page, before=before_desktop, expected_open=True)
                cycles.append({"cycle": index + 1, "mobile": mobile, "desktop": desktop})
            mobile_y = [item["mobile"]["scroll"]["y"] for item in cycles]
            desktop_y = [item["desktop"]["scroll"]["y"] for item in cycles]
            require(max(mobile_y)-min(mobile_y) <= 1, "mobile focus/scroll drift across repeated cycles")
            require(max(desktop_y)-min(desktop_y) <= 1, "desktop focus/scroll drift across repeated cycles")

            page.set_viewport_size({"width": 390, "height": 844})
            page.wait_for_function("!document.querySelector('.cui-explorer-refine').open", timeout=10000)
            page.locator('.cui-explorer-refine > summary').click()
            family.evaluate("element=>{element.disabled=true;element.closest('.q-field')?.classList.add('q-field--disabled')}")
            page.locator('.cui-explorer-refine > summary').focus()
            before_fallback = page.evaluate("({scrollX,scrollY,viewport:{width:innerWidth,height:innerHeight}})")
            page.set_viewport_size({"width": 1440, "height": 900})
            page.wait_for_function("document.querySelector('.cui-explorer-refine').open && document.activeElement.textContent.includes('Favorites')", timeout=10000)
            wait_visible_handoff(page, expected_tag="BUTTON")
            fallback = focus_record(page, before=before_fallback, expected_open=True)
            require("Favorites" in fallback["active"]["text"], "disabled Family did not use Favorites fallback")
            family.evaluate("element=>{element.disabled=false;element.closest('.q-field')?.classList.remove('q-field--disabled')}")

            search = page.get_by_role("textbox", name="Search")
            search.focus()
            page.evaluate("window.scrollTo(0,0)")
            before_external = page.evaluate("({scrollX,scrollY})")
            page.set_viewport_size({"width": 390, "height": 844})
            page.wait_for_function("matchMedia('(max-width: 680px)').matches", timeout=5000)
            external_mobile = page.evaluate("({activeId:document.activeElement.id,activeLabel:document.activeElement.getAttribute('aria-label'),scrollX,scrollY})")
            require(external_mobile["activeLabel"] == "Search", "breakpoint stole external Search focus")
            require(external_mobile["scrollX"] == before_external["scrollX"] and external_mobile["scrollY"] == before_external["scrollY"], "breakpoint stole external Search scroll")
            page.set_viewport_size({"width": 1440, "height": 900})
            page.wait_for_function("!matchMedia('(max-width: 680px)').matches", timeout=5000)
            external_desktop = page.evaluate("({activeId:document.activeElement.id,activeLabel:document.activeElement.getAttribute('aria-label'),scrollX,scrollY})")
            require(external_desktop["activeLabel"] == "Search", "desktop breakpoint stole external Search focus")
            require(external_desktop["scrollX"] == before_external["scrollX"] and external_desktop["scrollY"] == before_external["scrollY"], "desktop breakpoint stole external Search scroll")
            after = page.evaluate("({identity:window.__niceguiBaseExplorerRefineResponsive,listeners:window.__refineChangeListeners,observers:window.__observerCreations})")
            require(after["identity"] == responsive["identity"], "responsive singleton identity changed")
            require(after["listeners"] == responsive["listeners"] == 1, "breakpoint listener count changed")
            require(after["observers"] == responsive["observers"], "MutationObserver count grew after reinjection/cycles")
            return {"cycles": cycles, "mobileScrollRange": max(mobile_y)-min(mobile_y), "desktopScrollRange": max(desktop_y)-min(desktop_y), "fallback": fallback, "externalSearchMobile": external_mobile, "externalSearchDesktop": external_desktop, "listenersBeforeAfter": [responsive["listeners"], after["listeners"]], "observerCountBeforeAfter": [responsive["observers"], after["observers"]], "singletonStable": True}

        record_scenario(results, "FOCUS_VISIBILITY_REPEAT_AND_EXTERNAL", repeat_and_external)

        def search_freeze() -> dict:
            ready_gallery(page, "/components")
            projections = []
            if page.get_by_role("button", name="All references").count():
                page.get_by_role("button", name="All references").click()
            family_combo = page.get_by_role("combobox", name="Family")
            family_control = page.locator('.cui-explorer-refine .q-field').filter(has=family_combo)
            family_control.click()
            page.get_by_role("option", name="All families", exact=True).click()
            page.wait_for_function("document.querySelectorAll('.cui-explorer-card[data-entry-key]').length===34", timeout=10000)
            search = page.get_by_role("textbox", name="Search")
            search.fill("MultiSelect")
            page.wait_for_function("document.querySelectorAll('.cui-explorer-card[data-entry-key]').length===1", timeout=10000)
            known = gallery_projection(page)
            require(known["entryKeys"] == ["component:multi_select"], "known search match is incorrect")
            projections.append({"step": "known_match", **known})
            search.fill("zzzz-no-such-component-2026")
            page.wait_for_function("document.querySelectorAll('.cui-explorer-card[data-entry-key]').length===0 && document.querySelector('.cui-workbench-preview-empty[role=status][aria-live=polite]')", timeout=10000)
            no_match = gallery_projection(page)
            require(no_match["status"].startswith("0 of 34 visible"), "no-match status is untruthful")
            require(no_match["emptyRole"] == "status" and no_match["emptyAriaLive"] == "polite", "no-match state is not live")
            projections.append({"step": "strict_no_match", **no_match})
            search.fill("")
            page.wait_for_function("document.querySelectorAll('.cui-explorer-card[data-entry-key]').length===34", timeout=10000)
            cleared = gallery_projection(page)
            require(cleared["status"].startswith("34 of 34 visible"), "clear did not restore all 34 cards")
            projections.append({"step": "clear", **cleared})

            card = page.locator('.cui-explorer-card[data-entry-key="component:multi_select"]')
            if card.get_by_role("button", name="☆ Favorite").count():
                card.get_by_role("button", name="☆ Favorite").click()
                page.wait_for_function("document.querySelector('[data-entry-key=\"component:multi_select\"]')?.innerText.includes('★ Saved')", timeout=10000)
            family_combo = page.get_by_role("combobox", name="Family")
            family_control = page.locator('.cui-explorer-refine .q-field').filter(has=family_combo)
            family_control.click()
            page.get_by_role("option", name="Inputs", exact=True).click()
            page.get_by_role("button", name="Favorites only").click()
            page.wait_for_function("document.querySelectorAll('.cui-explorer-card[data-entry-key]').length===1", timeout=10000)
            combined = gallery_projection(page)
            require(combined["entryKeys"] == ["component:multi_select"], "Family/Favorites composition changed the expected matching item")
            require(combined["status"].startswith("1 of 34 visible · 1 saved"), "Family/Favorites count is inconsistent")
            projections.append({"step": "family_favorites_composition", **combined})

            page.set_viewport_size({"width": 390, "height": 844})
            search = page.get_by_role("textbox", name="Search")
            search.fill("zzzz-no-such-component-2026")
            page.wait_for_function("document.querySelectorAll('.cui-explorer-card[data-entry-key]').length===0", timeout=10000)
            mobile_empty = gallery_projection(page)
            require(mobile_empty["emptyRole"] == "status" and mobile_empty["emptyAriaLive"] == "polite", "mobile no-match state regressed")
            require(not mobile_empty["horizontalOverflow"], "mobile search causes horizontal overflow")
            projections.append({"step": "mobile_no_match", **mobile_empty})
            return {"projections": projections, "searchCount": page.locator('.cui-explorer-controls input[aria-label="Search"]').count(), "refineCount": page.locator('.cui-explorer-refine').count()}

        record_scenario(results, "FOCUS_VISIBILITY_SEARCH_FREEZE", search_freeze)

        def shared_gallery() -> dict:
            routes = []
            for route in ("/components", "/analytics", "/recipes"):
                ready_gallery(page, route)
                projection = gallery_projection(page)
                require(projection["searchCount"] == 1, f"{route} does not have exactly one Search")
                require(projection["searchOutsideRefine"], f"{route} Search is inside Refine")
                require(projection["refineCount"] == 1, f"{route} does not have exactly one Refine")
                routes.append(projection)
            return {"routes": routes}

        record_scenario(results, "FOCUS_VISIBILITY_SHARED_GALLERY", shared_gallery)

        def patterns_identity() -> dict:
            page.goto(f"{BASE_URL}/patterns", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_selector("[data-unified-pattern-explorer]", timeout=20000)
            identity = page.evaluate(r"""() => ({url:location.href,identityCount:document.querySelectorAll('[data-unified-pattern-explorer]').length,sharedGalleryCount:document.querySelectorAll('.cui-explorer-controls').length,refineCount:document.querySelectorAll('.cui-explorer-refine').length,hasPatternCatalog:document.body.innerText.includes('Application Patterns')})""")
            require(identity["identityCount"] == 1 and identity["sharedGalleryCount"] == 0 and identity["refineCount"] == 0, "/patterns identity collapsed into shared galleries")
            return identity

        record_scenario(results, "FOCUS_VISIBILITY_PATTERNS_IDENTITY", patterns_identity)

        environment = {
            "browser": "Playwright Chromium",
            "playwrightVersion": importlib.metadata.version("playwright"),
            "browserVersion": browser.version,
            "executablePath": playwright.chromium.executable_path,
            "python": sys.version,
            "platform": platform.platform(),
            "reducedMotion": "reduce",
            "baseUrl": BASE_URL,
            "serverIdentity": "exact FIX-2 candidate e95cc5472351ccfbde70e28b73380aeb8196fb09",
        }
        (OUT / "browser-environment.json").write_text(json.dumps(environment, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (OUT / "scenario-results.json").write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (OUT / "focus-visibility-evidence.json").write_text(json.dumps(focus_records, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (OUT / "browser-errors.json").write_text(json.dumps(runtime_errors, indent=2) + "\n", encoding="utf-8")
        context.close()
        browser.close()
    if runtime_errors:
        print(json.dumps({"status": "FAIL", "errors": runtime_errors, "results": results}, indent=2))
        return 1
    print(json.dumps({"status": "PASS", "results": results, "browserEnvironment": environment}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
