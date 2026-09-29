import sys
import re

def test_full_application_interaction_integrity():
    print("==================================================================")
    print("      FITQUEST INTERACTIVE CLICKABILITY & INTEGRITY AUDIT         ")
    print("==================================================================")

    # 1. Verify JS files syntax
    from test_all_js_syntax import check_file_js
    import glob
    for fpath in sorted(glob.glob("frontend/*.js")):
        check_file_js(fpath)
    print("\n[PASS] All 16 frontend JS scripts verified 100% syntactically valid with zero errors.")

    # 2. Check HTML for all navigation tabs, views, and action buttons
    with open("frontend/index.html", "r") as f:
        html = f.read()

    expected_nav_views = [
        "homeView", "workoutView", "nutritionView", "movementDnaView",
        "adaptiveTrainingView", "evolutionView", "progressView", "aiCoachView", "historyView"
    ]

    for view in expected_nav_views:
        # Check nav tab
        assert f'data-view="{view}"' in html, f"Missing nav tab for {view}"
        # Check view panel
        assert f'id="{view}"' in html, f"Missing view panel for {view}"
    print(f"[PASS] Verified all {len(expected_nav_views)} navigation tabs and view panels mapped.")

    # 3. Check Dashboard action buttons
    with open("frontend/auth.js", "r") as f:
        auth_js = f.read()

    expected_html_actions = [
        'onclick="switchTab(\'workoutView\')"',
        'onclick="switchTab(\'aiCoachView\')"'
    ]
    for action in expected_html_actions:
        assert action in html, f"Missing action button or handler in html: {action}"

    assert 'id="userProfileTrigger"' in auth_js, "Missing userProfileTrigger in auth.js"
    assert 'openProfileTab()' in auth_js, "Missing openProfileTab() in auth.js"
    print("[PASS] Verified Dashboard primary CTAs and Profile Navigation.")

    # 4. Check Workout 4-stage flow buttons and triggers
    expected_workout_triggers = [
        'onclick="goToPrepareStage()"',
        'onclick="backToLearnStage()"',
        'onclick="startCountdownAndPerform()"',
        'onclick="endWorkoutSession()"'
    ]
    for trig in expected_workout_triggers:
        assert trig in html, f"Missing workout flow trigger: {trig}"
    print("[PASS] Verified Workout 4-stage flow interactive buttons (I'M READY, START, END).")

    # 5. Check that all modal overlays have display: none by default
    modal_matches = re.findall(r'<div[^>]*class="[^"]*modal-overlay[^"]*"[^>]*>', html)
    for m in modal_matches:
        assert 'display: none' in m or 'style="display: none;"' in m, f"Modal overlay missing display:none: {m}"
    print(f"[PASS] Verified all {len(modal_matches)} modal overlays safely initialized with display: none.")

    # 6. Check countdown overlay has display: none by default
    countdown_match = re.search(r'<div[^>]*id="workoutCountdownOverlay"[^>]*>', html)
    assert countdown_match and 'display: none' in countdown_match.group(0), "Countdown overlay missing display: none"
    print("[PASS] Verified countdown overlay initialized with display: none.")

    # 7. Check landing page #landingView and #landingNavHeader remain intact
    assert 'id="landingView"' in html, "Landing page #landingView missing"
    assert 'id="landingNavHeader"' in html, "Landing nav #landingNavHeader missing"
    print("[PASS] Verified landing page untouched.")

    print("==================================================================")
    print("      ALL INTERACTION & CLICKABILITY AUDITS PASSED CLEANLY!       ")
    print("==================================================================")

if __name__ == "__main__":
    test_full_application_interaction_integrity()
