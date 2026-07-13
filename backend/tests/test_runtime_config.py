import os
import unittest
from unittest.mock import patch


class RuntimeConfigTest(unittest.TestCase):
    def test_production_rejects_missing_or_default_secrets(self):
        from backend.services.runtime_config import load_runtime_config

        cases = (
            {"JWT_SECRET": "", "MATHMIND_IP_HASH_SECRET": "ip-secret", "ADMIN_PASS": "secure-admin-pass"},
            {"JWT_SECRET": "mathmind-dev-secret-key-change-in-prod", "MATHMIND_IP_HASH_SECRET": "ip-secret", "ADMIN_PASS": "secure-admin-pass"},
            {"JWT_SECRET": "jwt-secret", "MATHMIND_IP_HASH_SECRET": "", "ADMIN_PASS": "secure-admin-pass"},
            {"JWT_SECRET": "jwt-secret", "MATHMIND_IP_HASH_SECRET": "ip-secret", "ADMIN_PASS": "admin123"},
        )
        for overrides in cases:
            with self.subTest(overrides=overrides):
                with patch.dict(os.environ, {"MATHMIND_ENV": "production", **overrides}, clear=True):
                    with self.assertRaises(RuntimeError):
                        load_runtime_config()

    def test_development_uses_explicit_fallbacks_and_warns(self):
        from backend.services.runtime_config import (
            DEFAULT_ADMIN_PASS,
            DEFAULT_JWT_SECRET,
            load_runtime_config,
        )

        with patch.dict(os.environ, {"MATHMIND_ENV": "development"}, clear=True):
            with self.assertLogs("backend.services.runtime_config", level="WARNING") as logs:
                config = load_runtime_config()

        self.assertEqual(config.jwt_secret, DEFAULT_JWT_SECRET)
        self.assertEqual(config.admin_pass, DEFAULT_ADMIN_PASS)
        self.assertIsNone(config.ip_hash_secret)
        self.assertIn("development fallback", "\n".join(logs.output))


if __name__ == "__main__":
    unittest.main()
