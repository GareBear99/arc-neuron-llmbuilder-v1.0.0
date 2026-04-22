from __future__ import annotations

import pytest

from self_improve.candidates import _normalize_validation_command


def test_normalize_validation_command_from_string():
    assert _normalize_validation_command('python -c "print(123)"') == ['python', '-c', 'print(123)']


def test_normalize_validation_command_from_sequence():
    assert _normalize_validation_command(['python', '-c', 'print(123)']) == ['python', '-c', 'print(123)']


def test_normalize_validation_command_rejects_empty():
    with pytest.raises(ValueError):
        _normalize_validation_command('')
