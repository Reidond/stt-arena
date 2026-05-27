"""Supported transcription languages and per-provider code normalization."""

from __future__ import annotations

from dataclasses import dataclass

PROVIDER_IDS = (
    "openai_whisper",
    "deepgram",
    "google",
    "xai_grok",
)


@dataclass(frozen=True, slots=True)
class LanguageOption:
    code: str
    label: str


# Canonical BCP-47 codes aligned with Google Chirp 3 GA locales where possible.
LANGUAGE_OPTIONS: tuple[LanguageOption, ...] = (
    LanguageOption("en-US", "English (United States)"),
    LanguageOption("en-GB", "English (United Kingdom)"),
    LanguageOption("en-AU", "English (Australia)"),
    LanguageOption("en-IN", "English (India)"),
    LanguageOption("es-ES", "Spanish (Spain)"),
    LanguageOption("es-US", "Spanish (United States)"),
    LanguageOption("fr-FR", "French (France)"),
    LanguageOption("fr-CA", "French (Canada)"),
    LanguageOption("de-DE", "German (Germany)"),
    LanguageOption("it-IT", "Italian (Italy)"),
    LanguageOption("pt-BR", "Portuguese (Brazil)"),
    LanguageOption("pt-PT", "Portuguese (Portugal)"),
    LanguageOption("nl-NL", "Dutch (Netherlands)"),
    LanguageOption("pl-PL", "Polish (Poland)"),
    LanguageOption("ru-RU", "Russian (Russia)"),
    LanguageOption("uk-UA", "Ukrainian (Ukraine)"),
    LanguageOption("tr-TR", "Turkish (Turkey)"),
    LanguageOption("sv-SE", "Swedish (Sweden)"),
    LanguageOption("da-DK", "Danish (Denmark)"),
    LanguageOption("fi-FI", "Finnish (Finland)"),
    LanguageOption("no-NO", "Norwegian (Norway)"),
    LanguageOption("ro-RO", "Romanian (Romania)"),
    LanguageOption("hr-HR", "Croatian (Croatia)"),
    LanguageOption("ca-ES", "Catalan (Spain)"),
    LanguageOption("el-GR", "Greek (Greece)"),
    LanguageOption("hi-IN", "Hindi (India)"),
    LanguageOption("ja-JP", "Japanese (Japan)"),
    LanguageOption("ko-KR", "Korean (Korea)"),
    LanguageOption("cmn-Hans-CN", "Chinese (Simplified, China)"),
    LanguageOption("cmn-Hant-TW", "Chinese (Traditional, Taiwan)"),
    LanguageOption("vi-VN", "Vietnamese (Vietnam)"),
    LanguageOption("id-ID", "Indonesian (Indonesia)"),
    LanguageOption("th-TH", "Thai (Thailand)"),
    LanguageOption("ar-SA", "Arabic (Saudi Arabia)"),
    LanguageOption("he-IL", "Hebrew (Israel)"),
)

_ISO_OVERRIDES: dict[str, str] = {
    "cmn-Hans-CN": "zh",
    "cmn-Hant-TW": "zh",
    "he-IL": "he",
    "ar-SA": "ar",
    "no-NO": "no",
}

_GOOGLE_OVERRIDES: dict[str, str] = {
    "he-IL": "iw-IL",
}


def list_language_options() -> list[dict[str, object]]:
    return [
        {
            "code": option.code,
            "label": option.label,
            "providers": provider_language_map(option.code),
        }
        for option in LANGUAGE_OPTIONS
    ]


def resolve_canonical_language(language: str | None) -> str | None:
    if language is None:
        return None
    normalized = language.strip()
    if not normalized:
        return None
    valid = {option.code for option in LANGUAGE_OPTIONS}
    if normalized not in valid:
        msg = f"Unsupported language code: {normalized}"
        raise ValueError(msg)
    return normalized


def provider_language_map(canonical: str) -> dict[str, str]:
    return {
        provider_id: value
        for provider_id in PROVIDER_IDS
        if (value := language_for_provider(provider_id, canonical)) is not None
    }


def language_for_provider(provider_id: str, canonical: str | None) -> str | None:
    if canonical is None:
        return None

    if provider_id == "google":
        return _google_language(canonical)
    if provider_id == "deepgram":
        return canonical
    return _iso639_1(canonical)


def _google_language(canonical: str) -> str:
    return _GOOGLE_OVERRIDES.get(canonical, canonical)


def _iso639_1(canonical: str) -> str:
    if canonical in _ISO_OVERRIDES:
        return _ISO_OVERRIDES[canonical]
    primary = canonical.split("-", 1)[0].lower()
    if primary == "cmn":
        return "zh"
    return primary
