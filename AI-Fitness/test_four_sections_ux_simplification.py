"""
Test Suite: Four Analytical Sections UX Simplification & Information Density Audit
Tests DOM element IDs, plain language labels, progressive disclosure toggles,
and responsive design rules across Movement DNA, BODY SIM, Adaptive AI, and Evolution views.
"""

import os
import re
import unittest

WORKSPACE_DIR = os.path.abspath(os.path.dirname(__file__))
INDEX_HTML = os.path.join(WORKSPACE_DIR, 'frontend', 'index.html')
STYLE_CSS = os.path.join(WORKSPACE_DIR, 'frontend', 'style.css')
DNA_JS = os.path.join(WORKSPACE_DIR, 'frontend', 'movement_dna.js')
ADAPTIVE_JS = os.path.join(WORKSPACE_DIR, 'frontend', 'adaptive_training.js')
EVOLUTION_JS = os.path.join(WORKSPACE_DIR, 'frontend', 'movement_evolution.js')


class TestFourSectionsUXSimplification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(INDEX_HTML, 'r', encoding='utf-8') as f:
            cls.html_content = f.read()
        with open(STYLE_CSS, 'r', encoding='utf-8') as f:
            cls.css_content = f.read()
        with open(DNA_JS, 'r', encoding='utf-8') as f:
            cls.dna_js_content = f.read()
        with open(ADAPTIVE_JS, 'r', encoding='utf-8') as f:
            cls.adaptive_js_content = f.read()
        with open(EVOLUTION_JS, 'r', encoding='utf-8') as f:
            cls.evolution_js_content = f.read()

    # ==========================================
    # 1. MOVEMENT DNA TESTS
    # ==========================================
    def test_movement_dna_elements_preserved(self):
        """All critical Movement DNA IDs must be preserved in HTML."""
        required_ids = [
            'movementDnaView',
            'dnaExerciseSelect',
            'dnaOverallScore',
            'dnaTrendBadge',
            'dnaTrendDelta',
            'dnaStrongestTrait',
            'dnaStrongestScore',
            'dnaPrimaryLimiter',
            'dnaLimiterScore',
            'dnaSessionsCount',
            'dnaConfidencePill',
            'dnaConfidenceReason',
            'dnaDimensionGrid',
            'dnaGenerateBtn',
            'dnaDetailsToggle',
            'dnaDetailsContent',
            'dnaRadarCanvas',
            'dnaTimelineCanvas',
            'dnaTimelineFilters',
            'dnaLimiterCard',
            'dnaReportGrid',
            'dnaVelocityText',
        ]
        for elem_id in required_ids:
            self.assertIn(f'id="{elem_id}"', self.html_content, f"Missing Movement DNA element: #{elem_id}")

    def test_movement_dna_progressive_disclosure(self):
        """Movement DNA details container must default to hidden and have toggle handler."""
        self.assertIn('toggleDNADetails()', self.html_content)
        self.assertIn('function toggleDNADetails', self.dna_js_content)
        self.assertIn('dnaDetailsContent', self.dna_js_content)

    # ==========================================
    # 2. BODY SIM REMOVAL TESTS
    # ==========================================
    def test_body_sim_elements_completely_removed(self):
        """All BODY SIM IDs must be completely removed from HTML."""
        removed_ids = [
            'bodySimView',
            'bodySimCurrentDnaScore',
            'bodySimProjectedDnaScore',
            'bodySimDeltaPill',
            'bodySimConfidencePill',
            'bodySimSummaryText',
            'bodySimLimiterLabel',
            'bodySimLimiterTier',
            'bodySimLimiterScore',
            'bodySimLimiterRisk',
            'bodySimLaunchWorkoutBtn',
            'bodySimDetailsToggle',
            'bodySimDetailsContent',
            'bodySimTrajectoryCanvas',
            'bodySimDimensionsGrid',
            'bodySimSimulatedStratName',
            'bodySimSimulatedDnaScore',
            'bodySimNetGainPill',
            'bodySimLimiterResSessions',
            'bodySimSimulationInsights',
        ]
        for elem_id in removed_ids:
            self.assertNotIn(f'id="{elem_id}"', self.html_content, f"BODY SIM element still present: #{elem_id}")

    def test_body_sim_nav_and_script_removed(self):
        """BODY SIM nav tab and script must be absent."""
        self.assertNotIn('data-view="bodySimView"', self.html_content)
        self.assertNotIn('src="body_sim.js"', self.html_content)

    # ==========================================
    # 3. ADAPTIVE AI TESTS
    # ==========================================
    def test_adaptive_ai_elements_preserved(self):
        """All critical Adaptive AI IDs must be preserved in HTML."""
        required_ids = [
            'adaptiveTrainingView',
            'adaptConfidencePill',
            'adaptSessionsCount',
            'adaptPrimaryFocus',
            'adaptSecondaryFocus',
            'adaptConfidenceReason',
            'adaptiveDimensionGrid',
            'adaptInsightBody',
            'adaptResponseBody',
            'generateAdaptiveBtn',
            'adaptivePlanContainer',
        ]
        for elem_id in required_ids:
            self.assertIn(f'id="{elem_id}"', self.html_content, f"Missing Adaptive AI element: #{elem_id}")

    def test_adaptive_ai_plain_language(self):
        """Adaptive AI headings should be plain, user-friendly language."""
        self.assertIn('Your Workout, Adapted to You', self.html_content)
        self.assertIn('YOUR MOVEMENT STATUS', self.html_content)
        self.assertIn('ADAPTIVE TRAINING PLAN', self.html_content)

    # ==========================================
    # 4. EVOLUTION TESTS
    # ==========================================
    def test_evolution_elements_preserved(self):
        """All critical Evolution IDs must be preserved in HTML."""
        required_ids = [
            'evolutionView',
            'evolutionExerciseSelect',
            'evoExerciseTitle',
            'evoSessionsCount',
            'evoCurrentQualityScore',
            'evoQualityChangePill',
            'evoAIInsightText',
            'evolutionMetricCardsGrid',
            'evoRecommendationsList',
            'evolutionDetailsToggle',
            'evolutionDetailsContent',
            'evolutionRadarCanvas',
            'evolutionHistoryCanvas',
        ]
        for elem_id in required_ids:
            self.assertIn(f'id="{elem_id}"', self.html_content, f"Missing Evolution element: #{elem_id}")

    def test_evolution_progressive_disclosure(self):
        """Evolution details toggle must be present and wired up."""
        self.assertIn('toggleEvolutionDetails()', self.html_content)
        self.assertIn('function toggleEvolutionDetails', self.evolution_js_content)

    # ==========================================
    # 5. CSS RESPONSIVE INTEGRITY
    # ==========================================
    def test_css_rules_and_responsiveness(self):
        """Verify CSS contains action bars, compact rows, details content, and media queries."""
        self.assertIn('.section-action-bar', self.css_content)
        self.assertIn('.section-details-toggle-btn', self.css_content)
        self.assertIn('.section-details-content', self.css_content)
        self.assertIn('.dna-dim-compact-row', self.css_content)
        self.assertIn('.adapt-dim-compact-row', self.css_content)

        # Responsive queries
        self.assertIn('@media (max-width: 1024px)', self.css_content)
        self.assertIn('@media (max-width: 768px)', self.css_content)
        self.assertIn('@media (max-width: 480px)', self.css_content)


if __name__ == '__main__':
    unittest.main()
