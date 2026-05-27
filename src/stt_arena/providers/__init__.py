from __future__ import annotations

from collections.abc import Callable

from stt_arena.config import Settings
from stt_arena.providers.base import ProviderStatus, STTProvider
from stt_arena.providers.deepgram import DeepgramProvider
from stt_arena.providers.google import GoogleProvider
from stt_arena.providers.openai_whisper import OpenAIWhisperProvider
from stt_arena.providers.whisper_local import WhisperLocalProvider
from stt_arena.providers.xai_grok import XAIGrokProvider

ProviderFactory = Callable[[Settings], STTProvider]

PROVIDER_CLASSES: dict[str, ProviderFactory] = {
    WhisperLocalProvider.id: WhisperLocalProvider,
    DeepgramProvider.id: DeepgramProvider,
    GoogleProvider.id: GoogleProvider,
    OpenAIWhisperProvider.id: OpenAIWhisperProvider,
    XAIGrokProvider.id: XAIGrokProvider,
}


def list_provider_statuses(settings: Settings) -> list[ProviderStatus]:
    statuses: list[ProviderStatus] = []
    seen: set[str] = set()

    for provider_id in settings.enabled_provider_ids:
        cls = PROVIDER_CLASSES.get(provider_id)
        if cls is None:
            continue
        provider = cls(settings)
        statuses.append(provider.status(enabled=True))
        seen.add(provider_id)

    for provider_id, cls in PROVIDER_CLASSES.items():
        if provider_id in seen:
            continue
        statuses.append(cls(settings).status(enabled=False))

    return statuses


def available_providers(settings: Settings) -> list[STTProvider]:
    providers: list[STTProvider] = []
    for provider_id in settings.enabled_provider_ids:
        cls = PROVIDER_CLASSES.get(provider_id)
        if cls is None:
            continue
        provider = cls(settings)
        if provider.is_available():
            providers.append(provider)
    return providers
