"""Env-var precedence: MATHMIND_LLM_API_KEY / DEEPSEEK_API_KEY must
override the SQLite UserSettings row.
"""

import os
import unittest
from unittest import mock

from backend.routers.upload import _get_llm_config, _has_user_model_config


class LlmEnvOverrideTest(unittest.TestCase):
    def test_platform_env_model_allows_new_student_without_personal_config(self):
        """A production-wide model key must be usable by newly registered students."""
        with mock.patch.dict(
            os.environ,
            {"MATHMIND_LLM_API_KEY": "sk-platform"},
            clear=False,
        ):
            self.assertTrue(_has_user_model_config("u_new_student"))

    def test_env_key_wins_over_db(self):
        with mock.patch.dict(
            os.environ,
            {
                "MATHMIND_LLM_API_KEY": "sk-env",
                "MATHMIND_LLM_PROVIDER": "deepseek",
                "MATHMIND_LLM_MODEL": "deepseek-chat",
                "MATHMIND_LLM_BASE_URL": "https://example/v1",
            },
            clear=False,
        ):
            ok, cfg = _get_llm_config("u_default")
        self.assertTrue(ok)
        self.assertEqual(cfg["api_key"], "sk-env")
        self.assertEqual(cfg["model_provider"], "deepseek")
        self.assertEqual(cfg["model_name"], "deepseek-chat")
        self.assertEqual(cfg["base_url"], "https://example/v1")

    def test_deepseek_alias(self):
        env = {
            k: v for k, v in os.environ.items()
            if k not in {"MATHMIND_LLM_API_KEY", "MATHMIND_LLM_PROVIDER",
                         "MATHMIND_LLM_MODEL", "MATHMIND_LLM_BASE_URL",
                         "DEEPSEEK_API_KEY"}
        }
        env["DEEPSEEK_API_KEY"] = "sk-alias"
        with mock.patch.dict(os.environ, env, clear=True):
            ok, cfg = _get_llm_config("u_default")
        self.assertTrue(ok)
        self.assertEqual(cfg["api_key"], "sk-alias")
        self.assertEqual(cfg["model_provider"], "deepseek")


if __name__ == "__main__":
    unittest.main()
