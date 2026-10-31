import unittest

from llm_config import create_chat_model, llm_settings


class LLMConfigTests(unittest.TestCase):
    def test_defaults_use_openrouter_for_every_role(self):
        for role in ("router", "chat", "triage"):
            settings = llm_settings(role, {})
            self.assertEqual(settings.provider, "openrouter")
            self.assertEqual(settings.api_key_env, "OPENROUTER_API_KEY")
            self.assertEqual(settings.base_url, "https://openrouter.ai/api/v1")
        self.assertEqual(llm_settings("triage", {}).model, "openai/gpt-5.4")

    def test_role_can_switch_provider_with_explicit_model(self):
        env = {"LLM_TRIAGE_PROVIDER": "OpenAI", "LLM_TRIAGE_MODEL": "gpt-5.4"}
        settings = llm_settings("triage", env)
        self.assertEqual(settings.provider, "openai")
        self.assertEqual(settings.model, "gpt-5.4")
        self.assertEqual(settings.api_key_env, "OPENAI_API_KEY")
        self.assertEqual(settings.base_url, "https://api.openai.com/v1")

    def test_switching_provider_without_model_is_rejected(self):
        with self.assertRaises(ValueError):
            llm_settings("triage", {"LLM_TRIAGE_PROVIDER": "openai"})

    def test_unknown_provider_and_role_are_rejected(self):
        with self.assertRaises(ValueError):
            llm_settings("triage", {"LLM_TRIAGE_PROVIDER": "anthropic"})
        with self.assertRaises(ValueError):
            llm_settings("voz", {})

    def test_missing_key_has_no_fallback_to_other_provider(self):
        # Chave da OpenAI presente não pode cobrir a falta da chave da OpenRouter.
        env = {"OPENAI_API_KEY": "chave-ficticia", "OPENROUTER_API_KEY": "  "}
        with self.assertRaises(RuntimeError) as error:
            create_chat_model("triage", env)
        self.assertIn("OPENROUTER_API_KEY", str(error.exception))
        self.assertNotIn("chave-ficticia", str(error.exception))


if __name__ == "__main__":
    unittest.main()
