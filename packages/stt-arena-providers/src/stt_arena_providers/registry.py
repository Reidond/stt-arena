from __future__ import annotations

import logging
from collections.abc import Callable

from stt_arena_providers.base import ProviderStatus, STTProvider
from stt_arena_providers.providers.deepgram import DeepgramProvider
from stt_arena_providers.providers.google import GoogleProvider
from stt_arena_providers.providers.openai_whisper import OpenAIWhisperProvider
from stt_arena_providers.providers.xai_grok import XAIGrokProvider
from stt_arena_providers.settings import ProviderSettings

ProviderFactory = Callable[[ProviderSettings], STTProvider]
logger = logging.getLogger(__name__)

PROVIDER_CLASSES: dict[str, ProviderFactory] = {
    DeepgramProvider.id: DeepgramProvider,
    GoogleProvider.id: GoogleProvider,
    OpenAIWhisperProvider.id: OpenAIWhisperProvider,
    XAIGrokProvider.id: XAIGrokProvider,
}


def list_provider_statuses(settings: ProviderSettings) -> list[ProviderStatus]:
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


def available_providers(settings: ProviderSettings) -> list[STTProvider]:
    providers: list[STTProvider] = []
    for provider_id in settings.enabled_provider_ids:
        cls = PROVIDER_CLASSES.get(provider_id)
        if cls is None:
            logger.error("Unknown enabled provider id=%s", provider_id)
            continue
        provider = cls(settings)
        if provider.is_available():
            providers.append(provider)
        else:
            logger.error(
                "Enabled provider %s is unavailable: %s",
                provider.id,
                provider.unavailable_reason(),
            )
    return providers
