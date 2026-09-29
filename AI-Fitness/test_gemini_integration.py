#!/usr/bin/env python3
"""
Focused integration & regression test suite for Google Gemini API integration (google-genai SDK).
Verifies key loading, SDK client initialization, real API connection, AI assistant Q&A,
offline fallback engine upon API errors, and fitness domain restriction.
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

def run_gemini_tests():
    print("==================================================")
    print("      FITQUEST AI - GEMINI INTEGRATION TEST       ")
    print("==================================================")

    # ----------------------------------------------------
    # TEST 1: Environment API Key Loading
    # ----------------------------------------------------
    print("\n[TEST 1] Verifying environment API key loading...")
    from backend.config import settings
    raw_env_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    effective_key = settings.effective_api_key

    assert raw_env_key is not None and len(raw_env_key.strip()) > 0, "GEMINI_API_KEY is missing from environment/dotenv!"
    assert effective_key is not None and len(effective_key.strip()) > 0, "settings.effective_api_key is empty!"
    print(f"  - GEMINI_API_KEY present: True")
    print(f"  - effective_api_key present: True")
    print("[PASS] Test 1: API key environment loading verified successfully.")

    # ----------------------------------------------------
    # TEST 2: SDK Initialization with google-genai
    # ----------------------------------------------------
    print("\n[TEST 2] Initializing google-genai SDK client...")
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=effective_key)
    assert client is not None, "Failed to instantiate google.genai.Client"
    print("[PASS] Test 2: google-genai Client initialized successfully.")

    # ----------------------------------------------------
    # TEST 3: Minimal Gemini API Request
    # ----------------------------------------------------
    print("\n[TEST 3] Sending minimal test request to Gemini API (gemini-2.5-flash)...")
    test_prompt = "Reply with exactly: GEMINI CONNECTION WORKING"
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=test_prompt
    )
    assert response and response.text, "Gemini API returned an empty response!"
    resp_text = response.text.strip()
    print(f"  - Response snippet: '{resp_text}'")
    assert "GEMINI CONNECTION WORKING" in resp_text.upper(), f"Unexpected API response text: '{resp_text}'"
    print("[PASS] Test 3: Real Gemini API request succeeded with model gemini-2.5-flash.")

    # ----------------------------------------------------
    # TEST 4: AI Fitness Assistant Answer Fitness Question
    # ----------------------------------------------------
    print("\n[TEST 4] Testing AIFitnessAssistant with real fitness question...")
    from assistant import AIFitnessAssistant, UserProfile
    
    assistant = AIFitnessAssistant()
    assert assistant.genai_client is not None, "AIFitnessAssistant client not initialized!"
    
    question = "What are the benefits of squats?"
    profile = UserProfile(fitness_goal="Strength", experience_level="Intermediate")
    answer = assistant.answer_fitness_question(question, profile)
    
    assert answer and len(answer) > 50, f"Assistant returned an insufficient answer: '{answer}'"
    assert any(kw in answer.lower() for kw in ["quad", "glute", "muscle", "strength", "leg", "squat"]), \
        f"Answer missing expected squat benefits keywords: '{answer[:100]}...'"
    print(f"  - Generated Answer Length: {len(answer)} chars")
    print(f"  - Answer snippet: '{answer[:120]}...'")
    print("[PASS] Test 4: AI Fitness Assistant answered fitness question using Gemini API.")

    # ----------------------------------------------------
    # TEST 5: Fallback Behavior On API Failure
    # ----------------------------------------------------
    print("\n[TEST 5] Testing offline rule-based fallback when Gemini fails...")
    fallback_assistant = AIFitnessAssistant(api_key="INVALID_MOCK_KEY_FOR_TESTING")
    
    # Simulate API call failure on invalid client
    fallback_answer = fallback_assistant.answer_fitness_question("What are the benefits of squats?", profile)
    assert fallback_answer and len(fallback_answer) > 50, "Fallback engine returned empty answer!"
    print(f"  - Fallback Answer snippet: '{fallback_answer[:120]}...'")
    print("[PASS] Test 5: Fallback engine produced robust guidance when Gemini was unavailable.")

    # ----------------------------------------------------
    # TEST 6: Out-of-Domain Question Handling
    # ----------------------------------------------------
    print("\n[TEST 6] Testing out-of-domain question restriction...")
    ood_question = "Who was the first president of India?"
    ood_response = assistant.answer_fitness_question(ood_question, profile)
    
    assert ood_response and len(ood_response) > 20, "Out-of-domain response empty!"
    assert any(kw in ood_response.lower() for kw in ["fitness", "specialized", "fitquest ai coach", "off-topic", "unable"]), \
        f"Out-of-domain response did not politely redirect: '{ood_response}'"
    print(f"  - Out-of-domain Response snippet: '{ood_response[:120]}...'")
    print("[PASS] Test 6: Out-of-domain redirection verified.")

    print("\n==================================================")
    print("   [SUCCESS] ALL GEMINI INTEGRATION TESTS PASSED!  ")
    print("==================================================")

if __name__ == "__main__":
    run_gemini_tests()
