import asyncio
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock

from transcription import (
    MAX_AUDIO_BYTES,
    AudioTooLargeError,
    create_transcription_client,
    transcribe_voice,
    transcription_settings,
)


def fake_client(text="  ideia ficticia  "):
    create = AsyncMock(return_value=SimpleNamespace(text=text))
    return SimpleNamespace(audio=SimpleNamespace(transcriptions=SimpleNamespace(create=create))), create


class TranscriptionTests(unittest.TestCase):
    def test_default_uses_openrouter(self):
        settings = transcription_settings({})
        self.assertEqual(settings.provider, "openrouter")
        self.assertEqual(settings.model, "openai/gpt-4o-mini-transcribe")
        self.assertEqual(settings.api_key_env, "OPENROUTER_API_KEY")
        self.assertEqual(settings.base_url, "https://openrouter.ai/api/v1")

    def test_switching_provider_requires_model(self):
        with self.assertRaises(ValueError):
            transcription_settings({"TRANSCRIPTION_PROVIDER": "openai"})
        settings = transcription_settings(
            {"TRANSCRIPTION_PROVIDER": "openai", "TRANSCRIPTION_MODEL": "gpt-4o-mini-transcribe"}
        )
        self.assertEqual(settings.api_key_env, "OPENAI_API_KEY")
        with self.assertRaises(ValueError):
            transcription_settings({"TRANSCRIPTION_PROVIDER": "groq"})

    def test_missing_key_has_no_fallback(self):
        env = {"OPENAI_API_KEY": "chave-ficticia"}
        with self.assertRaises(RuntimeError) as error:
            create_transcription_client(env)
        self.assertIn("OPENROUTER_API_KEY", str(error.exception))
        self.assertNotIn("chave-ficticia", str(error.exception))

    def test_transcribe_sends_ogg_with_configured_model(self):
        client, create = fake_client()
        settings = transcription_settings({})
        text = asyncio.run(transcribe_voice(client, settings, b"OggS ficticio"))
        self.assertEqual(text, "ideia ficticia")
        kwargs = create.await_args.kwargs
        self.assertEqual(kwargs["model"], "openai/gpt-4o-mini-transcribe")
        self.assertEqual(kwargs["language"], "pt")
        self.assertEqual(kwargs["file"].name, "voice.ogg")

    def test_audio_over_limit_is_not_sent(self):
        client, create = fake_client()
        with self.assertRaises(AudioTooLargeError):
            asyncio.run(transcribe_voice(client, transcription_settings({}), b"0" * (MAX_AUDIO_BYTES + 1)))
        create.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
