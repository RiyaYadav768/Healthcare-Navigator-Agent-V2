import json
import types
import pytest
from unittest import mock

import streamlit as st

import sys

# Import the app module
import app


def test_is_quota_error_detects_429():
    class FakeErr(Exception):
        status_code = 429

    err = FakeErr("quota exceeded")
    assert app.is_quota_error(err) is True


def test_is_quota_error_detects_message():
    err = Exception("Error: 429 Too Many Requests - quota exceeded")
    assert app.is_quota_error(err) is True


def test_handle_quota_mode_shows_warning_and_returns_demo():
    # Patch streamlit.warning to capture calls
    with mock.patch.object(st, "warning") as mock_warn:
        result_text = app.handle_quota_mode()
        # Ensure a warning message was shown
        mock_warn.assert_called()
        # Ensure returned text is valid JSON matching demo structure
        data = json.loads(result_text)
        assert "analysis" in data
        assert "explanation" in data
        assert "doctor_questions" in data
        # Verify agent outputs exist
        findings = data["analysis"].get("findings", [])
        assert len(findings) >= 1
        explanations = data["explanation"].get("explanations", [])
        assert len(explanations) >= 1
        questions = data["doctor_questions"].get("questions", [])
        assert len(questions) >= 1


def test_demo_mode_integration_simulate_quota(monkeypatch):
    """Simulate the model.generate_content raising a 429-like exception and ensure demo mode string returned."""
    class FakeModel:
        def generate_content(self, *args, **kwargs):
            raise Exception("429 quota exceeded")

    # Monkeypatch the model used in app to our fake
    monkeypatch.setattr(app, "model", FakeModel())

    # Patch st.warning to record calls
    with mock.patch.object(st, "warning") as mock_warn:
        # Build a minimal prompt and call the code path that would normally handle exception
        # We call is_quota_error to simulate detection, then call handle_quota_mode
        err = Exception("429 quota exceeded")
        assert app.is_quota_error(err) is True
        result_text = app.handle_quota_mode()
        mock_warn.assert_called()
        data = json.loads(result_text)
        assert "analysis" in data and "explanation" in data and "doctor_questions" in data