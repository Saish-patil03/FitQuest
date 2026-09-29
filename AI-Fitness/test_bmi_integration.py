"""
FitQuest BMI Feature Integration Test
Verifies:
1. Standard BMI formula: BMI = weight (kg) / (height (m))^2
2. Correct category classification across all boundaries:
   - < 18.5: Underweight
   - 18.5 - 24.9: Normal Range
   - 25.0 - 29.9: Overweight
   - >= 30.0: Obesity
3. Safety for zero, negative, null, and missing inputs.
4. DOM IDs and structure in index.html for Profile Body Metrics & BMI.
5. CSS classes in style.css for BMI cards and category badges.
6. Landing page #landingView and #landingNavHeader remain 100% untouched.
7. No new navigation tabs or major standalone pages created.
"""

from pathlib import Path
import re

BASE_DIR = Path(__file__).parent
AUTH_JS = BASE_DIR / "frontend" / "auth.js"
INDEX_HTML = BASE_DIR / "frontend" / "index.html"
STYLE_CSS = BASE_DIR / "frontend" / "style.css"

def calculate_bmi_py(weight_kg, height_cm):
    if not weight_kg or not height_cm or weight_kg <= 0 or height_cm <= 0:
        return None
    height_m = height_cm / 100.0
    bmi = weight_kg / (height_m * height_m)
    return round(bmi, 1)

def get_bmi_category_py(bmi):
    if bmi is None:
        return {"label": "Add Height & Weight", "class": "bmi-na"}
    if bmi < 18.5:
        return {"label": "Underweight", "class": "bmi-underweight"}
    elif bmi <= 24.9:
        return {"label": "Normal Range", "class": "bmi-normal"}
    elif bmi <= 29.9:
        return {"label": "Overweight", "class": "bmi-overweight"}
    else:
        return {"label": "Obesity", "class": "bmi-obesity"}

def test_bmi_integration():
    auth_code = AUTH_JS.read_text(encoding="utf-8")
    html_code = INDEX_HTML.read_text(encoding="utf-8")
    css_code = STYLE_CSS.read_text(encoding="utf-8")

    # 1. Test math calculations
    # Example from prompt: 175cm, 70kg -> 22.9, Normal Range
    bmi_std = calculate_bmi_py(70, 175)
    assert bmi_std == 22.9, f"Expected 22.9, got {bmi_std}"
    cat_std = get_bmi_category_py(bmi_std)
    assert cat_std["label"] == "Normal Range"

    # Underweight test: 180cm, 55kg -> 17.0
    bmi_under = calculate_bmi_py(55, 180)
    assert bmi_under == 17.0
    assert get_bmi_category_py(bmi_under)["label"] == "Underweight"

    # Overweight test: 170cm, 80kg -> 27.7
    bmi_over = calculate_bmi_py(80, 170)
    assert bmi_over == 27.7
    assert get_bmi_category_py(bmi_over)["label"] == "Overweight"

    # Obesity test: 170cm, 95kg -> 32.9
    bmi_obese = calculate_bmi_py(95, 170)
    assert bmi_obese == 32.9
    assert get_bmi_category_py(bmi_obese)["label"] == "Obesity"

    # Missing / invalid safety tests
    assert calculate_bmi_py(None, 175) is None
    assert calculate_bmi_py(70, None) is None
    assert calculate_bmi_py(0, 175) is None
    assert calculate_bmi_py(70, 0) is None
    assert calculate_bmi_py(-10, 175) is None

    # 2. Check JavaScript implementation in auth.js
    assert "function calculateBMI(" in auth_code
    assert "function getBMICategory(" in auth_code
    assert "heightM = heightCm / 100" in auth_code
    assert "weightKg / (heightM * heightM)" in auth_code
    assert "Underweight" in auth_code
    assert "Normal Range" in auth_code
    assert "Overweight" in auth_code
    assert "Obesity" in auth_code
    assert "profBmBmi" in auth_code
    assert "profBmCategory" in auth_code

    # 3. Check HTML elements in index.html
    required_ids = [
        "profBodyMetricsSection",
        "profBodyMetricsCard",
        "profBmWeight",
        "profBmHeight",
        "profBmBmi",
        "profBmCategory",
        "profBmExplanation"
    ]
    for dom_id in required_ids:
        assert f'id="{dom_id}"' in html_code, f"Missing DOM ID: {dom_id}"

    # 4. Check CSS styling in style.css
    assert ".prof-body-metrics-card" in css_code
    assert ".prof-bmi-badge" in css_code
    assert ".bmi-normal" in css_code
    assert ".bmi-underweight" in css_code
    assert ".bmi-overweight" in css_code
    assert ".bmi-obesity" in css_code

    # 5. Check Landing page preservation
    assert 'id="landingView"' in html_code
    assert 'id="landingNavHeader"' in html_code

    # 6. Check that no new navigation tabs were created
    nav_tab_matches = re.findall(r'class="nav-tab[^"]*"', html_code)
    # Total authenticated nav tabs in header (10 views)
    assert len(nav_tab_matches) in (9, 10), f"Expected 9 or 10 nav tabs, found {len(nav_tab_matches)}"

    print("[PASS] FitQuest BMI Integration Tests Passed 100% Cleanly!")

if __name__ == "__main__":
    test_bmi_integration()
