from __future__ import annotations

import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
I18N_DIR = BASE_DIR / "config" / "i18n"
DEFAULT_LANG = "en"
SUPPORTED = ("en", "es", "pt", "zh-CN", "ko", "ja", "de", "fr")


class I18n:
    """Load flat key JSON bundles for backend / QWebChannel."""

    def __init__(self, i18n_dir: str | Path | None = None, language: str = DEFAULT_LANG):
        self.i18n_dir = Path(i18n_dir) if i18n_dir else I18N_DIR
        self._cache: dict[str, dict[str, str]] = {}
        self.language = self.normalize(language)

    @staticmethod
    def normalize(lang: str | None) -> str:
        if not lang:
            return DEFAULT_LANG
        lang = str(lang).strip()
        if lang in SUPPORTED:
            return lang
        lower = lang.lower()
        for code in SUPPORTED:
            if code.lower() == lower or code.split("-")[0].lower() == lower:
                return code
        return DEFAULT_LANG

    def path_for(self, lang: str) -> Path:
        return self.i18n_dir / f"{self.normalize(lang)}.json"

    def load(self, lang: str | None = None) -> dict[str, str]:
        code = self.normalize(lang or self.language)
        if code in self._cache:
            return self._cache[code]
        path = self.path_for(code)
        data: dict[str, str] = {}
        try:
            with open(path, encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, dict):
                data = {str(k): str(v) for k, v in raw.items()}
        except (OSError, json.JSONDecodeError):
            data = {}
        if code != DEFAULT_LANG:
            data = {**self.load(DEFAULT_LANG), **data}
        self._cache[code] = data
        return data

    def t(self, key: str, lang: str | None = None) -> str:
        bundle = self.load(lang)
        return bundle.get(key, self.load(DEFAULT_LANG).get(key, key))

    def bundle(self, lang: str | None = None) -> dict[str, str]:
        return dict(self.load(lang))

    def available(self) -> list[str]:
        return [c for c in SUPPORTED if self.path_for(c).is_file() or c == DEFAULT_LANG]
