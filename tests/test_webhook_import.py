from unittest.mock import patch
import importlib
import sys


def test_webhook_import_does_not_init_database(monkeypatch):
    sys.modules.pop('webhook', None)
    with patch('database.Database', side_effect=AssertionError('Database should not initialize on import')):
        module = importlib.import_module('webhook')

    assert hasattr(module, 'app')
    assert module.app is not None
