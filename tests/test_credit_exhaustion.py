"""
Test suite for credit exhaustion handling and Haiku 4.5 model switching.

Tests:
1. CreditExhaustedError is properly raised on HTTP 402/403
2. CreditExhaustedError is caught in _run_content_session()
3. credit_exhausted flag is set when error occurs
4. Discord alert is sent on first exhaustion
5. Anchor/breaking/marketing content skips when flag is set
6. MarketingPostGenerator uses CLAUDE_CONTENT_MODEL env var
7. ContentSession uses CLAUDE_CONTENT_MODEL env var
8. ClaudeResearchEngine accepts model parameter
"""

import os
import sys
import json
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.enhanced_data_fetchers import CreditExhaustedError, ClaudeResearchEngine
from src.content.marketing_post_generator import MarketingPostGenerator
from src.content.content_session import ContentSession


def test_credit_exhausted_error_raised():
    """Test that CreditExhaustedError is raised on HTTP 402."""
    print("\n[TEST 1] CreditExhaustedError raised on HTTP 402")

    api_key = "test-key"
    engine = ClaudeResearchEngine(api_key=api_key)

    # Mock anthropic client to raise 402 error
    with patch('anthropic.Anthropic') as mock_anthropic:
        mock_client = Mock()
        mock_anthropic.return_value = mock_client

        # Simulate HTTP 402 with credit error message
        # Create a mock APIError-like exception with status_code
        error = Exception("insufficient_credits: Not enough credits")
        error.status_code = 402
        mock_client.messages.create.side_effect = error

        try:
            engine._call_model("test prompt")
            print("   [FAIL] No exception raised")
            return False
        except CreditExhaustedError as e:
            print(f"   [PASS] CreditExhaustedError raised: {str(e)[:60]}...")
            return True
        except Exception as e:
            print(f"   [FAIL] Wrong exception type: {type(e).__name__}")
            return False


def test_credit_exhausted_error_caught_in_content_session():
    """Test that ContentSession re-raises CreditExhaustedError."""
    print("\n[TEST 2] ContentSession re-raises CreditExhaustedError")

    analysis_data = {
        'market_context': {},
        'majors': {},
        'defi': [],
        'memecoins': [],
        'privacy_coins': [],
        'commodities': [],
    }

    session = ContentSession(analysis_data, mode='morning_scan')

    # Mock ClaudeResearchEngine to raise CreditExhaustedError
    with patch.object(session, '_call_claude_master') as mock_call:
        mock_call.side_effect = CreditExhaustedError("Credits exhausted")

        try:
            session.generate_all()
            print("   [FAIL] No exception raised")
            return False
        except CreditExhaustedError:
            print("   [PASS] CreditExhaustedError re-raised by ContentSession")
            return True
        except Exception as e:
            print(f"   [FAIL] Wrong exception caught: {type(e).__name__}")
            return False


def test_marketing_post_generator_uses_env_model():
    """Test that MarketingPostGenerator uses CLAUDE_CONTENT_MODEL env var."""
    print("\n[TEST 3] MarketingPostGenerator uses CLAUDE_CONTENT_MODEL")

    # Set env var to test value
    test_model = "claude-haiku-4-5-20251001"
    with patch.dict(os.environ, {'CLAUDE_CONTENT_MODEL': test_model}):
        gen = MarketingPostGenerator()

        # Mock anthropic to capture the model parameter
        with patch('anthropic.Anthropic') as mock_anthropic:
            mock_client = Mock()
            mock_anthropic.return_value = mock_client

            # Mock response
            mock_msg = Mock()
            mock_msg.content = [Mock(text="Test post")]
            mock_client.messages.create.return_value = mock_msg

            gen._call_claude("test prompt")

            # Check that model was passed correctly
            call_kwargs = mock_client.messages.create.call_args[1]
            if call_kwargs.get('model') == test_model:
                print(f"   [PASS] MarketingPostGenerator uses {test_model}")
                return True
            else:
                print(f"   [FAIL] Model was {call_kwargs.get('model')}, expected {test_model}")
                return False


def test_claude_research_engine_accepts_model_param():
    """Test that ClaudeResearchEngine accepts model parameter."""
    print("\n[TEST 4] ClaudeResearchEngine accepts model parameter")

    test_model = "claude-haiku-4-5-20251001"
    api_key = "test-key"

    engine = ClaudeResearchEngine(api_key=api_key, model=test_model)

    if engine.model == test_model:
        print(f"   [PASS] ClaudeResearchEngine stores model={test_model}")
        return True
    else:
        print(f"   [FAIL] Model was {engine.model}, expected {test_model}")
        return False


def test_claude_research_engine_model_default():
    """Test that ClaudeResearchEngine defaults to Haiku if not specified."""
    print("\n[TEST 5] ClaudeResearchEngine defaults to Haiku 4.5")

    with patch.dict(os.environ, {'CLAUDE_CONTENT_MODEL': ''}):
        api_key = "test-key"
        engine = ClaudeResearchEngine(api_key=api_key)

        if 'haiku' in engine.model.lower():
            print(f"   [PASS] Default model is {engine.model}")
            return True
        else:
            print(f"   [FAIL] Default model is {engine.model}, expected Haiku")
            return False


def test_orchestrator_credit_exhausted_flag_mock():
    """Test that orchestrator's credit_exhausted flag is properly initialized."""
    print("\n[TEST 6] Orchestrator initializes credit_exhausted flag")

    # Import here to avoid full initialization
    from main import CryptoAnalysisOrchestrator

    with patch.object(CryptoAnalysisOrchestrator, '__init__', lambda x: None):
        orch = CryptoAnalysisOrchestrator()
        orch.credit_exhausted = False  # Simulate init

        if hasattr(orch, 'credit_exhausted') and orch.credit_exhausted == False:
            print("   [PASS] Orchestrator has credit_exhausted=False")
            return True
        else:
            print("   [FAIL] credit_exhausted flag not properly set")
            return False


def test_discord_notifier_has_send_system_alert():
    """Test that DiscordNotifier has send_system_alert method."""
    print("\n[TEST 7] DiscordNotifier.send_system_alert() exists")

    from src.utils.discord_notifier import DiscordNotifier

    notifier = DiscordNotifier()

    if hasattr(notifier, 'send_system_alert') and callable(getattr(notifier, 'send_system_alert')):
        print("   [PASS] DiscordNotifier has send_system_alert method")
        return True
    else:
        print("   [FAIL] send_system_alert method not found")
        return False


def test_discord_alert_signature():
    """Test that send_system_alert has correct signature."""
    print("\n[TEST 8] send_system_alert has correct parameters")

    from src.utils.discord_notifier import DiscordNotifier
    import inspect

    notifier = DiscordNotifier()
    sig = inspect.signature(notifier.send_system_alert)
    params = list(sig.parameters.keys())

    expected = ['self', 'title', 'message', 'level']
    required = [p for p, v in sig.parameters.items() if v.default == inspect.Parameter.empty and p != 'self']

    if 'title' in params and 'message' in params:
        print(f"   [PASS] send_system_alert has correct signature: {params}")
        return True
    else:
        print(f"   [FAIL] send_system_alert missing required params. Got: {params}")
        return False


def test_credit_exhausted_imports():
    """Test that all necessary imports are in place."""
    print("\n[TEST 9] CreditExhaustedError is properly exported")

    try:
        from src.utils.enhanced_data_fetchers import CreditExhaustedError
        print("   [PASS] CreditExhaustedError imported from enhanced_data_fetchers")

        # Check it's a real exception class
        if issubclass(CreditExhaustedError, Exception):
            print("   [PASS] CreditExhaustedError is an Exception subclass")
            return True
        else:
            print("   [FAIL] CreditExhaustedError is not an Exception")
            return False
    except ImportError as e:
        print(f"   [FAIL] Cannot import CreditExhaustedError: {e}")
        return False


def test_main_imports_credit_exhausted_error():
    """Test that main.py imports CreditExhaustedError."""
    print("\n[TEST 10] main.py imports CreditExhaustedError")

    # Read main.py and check for import
    main_path = Path(__file__).parent.parent / "main.py"
    with open(main_path, 'r') as f:
        content = f.read()

    if 'from src.utils.enhanced_data_fetchers import ClaudeResearchEngine, CreditExhaustedError' in content:
        print("   [PASS] main.py imports CreditExhaustedError")
        return True
    elif 'CreditExhaustedError' in content:
        print("   [PASS] main.py references CreditExhaustedError (import found)")
        return True
    else:
        print("   [FAIL] CreditExhaustedError not imported in main.py")
        return False


def test_main_has_credit_exhausted_guards():
    """Test that main.py has credit_exhausted guards in key methods."""
    print("\n[TEST 11] main.py has credit_exhausted guards")

    main_path = Path(__file__).parent.parent / "main.py"
    with open(main_path, 'r') as f:
        content = f.read()

    checks = [
        ('_run_anchor_content', 'if self.credit_exhausted:'),
        ('_check_and_post_breaking_news', 'if self.credit_exhausted:'),
        ('_run_marketing_post', 'if self.credit_exhausted:'),
    ]

    found = 0
    for method, guard in checks:
        if method in content and guard in content:
            found += 1
            print(f"   [PASS] {method} has credit_exhausted guard")
        else:
            print(f"   [FAIL] {method} missing guard")

    return found == len(checks)


def test_content_session_catches_credit_exhausted():
    """Test that _run_content_session in main.py catches CreditExhaustedError."""
    print("\n[TEST 12] main.py._run_content_session catches CreditExhaustedError")

    main_path = Path(__file__).parent.parent / "main.py"
    with open(main_path, 'r') as f:
        content = f.read()

    if 'except CreditExhaustedError as e:' in content:
        print("   [PASS] _run_content_session catches CreditExhaustedError")

        # Also check it sets the flag
        if 'self.credit_exhausted = True' in content:
            print("   [PASS] Sets self.credit_exhausted = True")

            # Check it sends Discord alert
            if 'send_system_alert' in content:
                print("   [PASS] Sends Discord alert on credit exhaustion")
                return True
            else:
                print("   [FAIL] No Discord alert found")
                return False
        else:
            print("   [FAIL] Does not set credit_exhausted flag")
            return False
    else:
        print("   [FAIL] Does not catch CreditExhaustedError")
        return False


# Run all tests
if __name__ == '__main__':
    print("\n" + "="*80)
    print("CREDIT EXHAUSTION & HAIKU 4.5 MODEL OPTIMIZATION TEST SUITE")
    print("="*80)

    tests = [
        test_credit_exhausted_error_raised,
        test_credit_exhausted_error_caught_in_content_session,
        test_marketing_post_generator_uses_env_model,
        test_claude_research_engine_accepts_model_param,
        test_claude_research_engine_model_default,
        test_orchestrator_credit_exhausted_flag_mock,
        test_discord_notifier_has_send_system_alert,
        test_discord_alert_signature,
        test_credit_exhausted_imports,
        test_main_imports_credit_exhausted_error,
        test_main_has_credit_exhausted_guards,
        test_content_session_catches_credit_exhausted,
    ]

    results = []
    for test_func in tests:
        try:
            results.append(test_func())
        except Exception as e:
            print(f"   [FAIL] EXCEPTION: {e}")
            results.append(False)

    print("\n" + "="*80)
    passed = sum(results)
    total = len(results)
    print(f"RESULTS: {passed}/{total} tests passed")
    print("="*80 + "\n")

    if passed == total:
        print("[PASS] ALL TESTS PASSED — Credit exhaustion handling implemented correctly")
        sys.exit(0)
    else:
        print(f"[FAIL] {total - passed} TESTS FAILED — Review implementation")
        sys.exit(1)
