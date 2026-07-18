# Translation coverage

English is the authoritative source. A localized README translates every section of `README.md`; it is not a summary. Only Simplified Chinese currently includes a complete translation of the deep documentation under `docs/`.

| Language | Locale | README | Deep documentation | Entry point |
|---|---|---:|---:|---|
| English | `en` | Complete, authoritative | Complete, authoritative | [README.md](../../README.md) |
| Português (Brasil) | `pt-BR` | Complete | English fallback | [README.pt-BR.md](../../README.pt-BR.md) |
| 简体中文 | `zh-CN` | Complete | Complete | [README.zh-CN.md](../../README.zh-CN.md) |
| 繁體中文 | `zh-TW` | Complete | English fallback | [README.zh-TW.md](../../README.zh-TW.md) |
| 日本語 | `ja` | Complete | English fallback | [README.ja.md](../../README.ja.md) |
| 한국어 | `ko` | Complete | English fallback | [README.ko.md](../../README.ko.md) |
| Türkçe | `tr` | Complete | English fallback | [README.tr.md](../../README.tr.md) |
| Русский | `ru` | Complete | English fallback | [README.ru.md](../../README.ru.md) |
| Tiếng Việt | `vi` | Complete | English fallback | [README.vi.md](../../README.vi.md) |
| ไทย | `th` | Complete | English fallback | [README.th.md](../../README.th.md) |
| Deutsch | `de` | Complete | English fallback | [README.de.md](../../README.de.md) |
| Español | `es` | Complete | English fallback | [README.es.md](../../README.es.md) |

## Synchronization policy

- Update `README.md` first.
- Keep `translation_of`, `source_revision`, and `last_synced_version` in every translated README.
- Update every localized README before release when the authoritative README changes materially.
- Keep commands, paths, JSON keys, model identifiers, enum values, status tokens, and version numbers unchanged.
- Run `python3 scripts/verify_public_repo.py` to validate metadata, navigation, privacy, and local links.
