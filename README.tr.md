---
translation_of: README.md
source_revision: docs-v0.4.0-alpha.1
last_synced_version: 0.4.0-alpha.1
---

# Auto Route for Codex

**Dil:** [English](README.md) | [Português (Brasil)](README.pt-BR.md) | [简体中文](README.zh-CN.md) | [繁體中文](README.zh-TW.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | Türkçe | [Русский](README.ru.md) | [Tiếng Việt](README.vi.md) | [ไทย](README.th.md) | [Deutsch](README.de.md) | [Español](README.es.md)

> Alfa aşamasındaki topluluk projesi. Resmî bir OpenAI ürünü değildir.

Auto Route for Codex, gizlilik sınırları belirlenmiş bir görev profilinden yeterli bir model rolü, akıl yürütme çabası ve yürütme topolojisi öneren, açıkça etkinleştirilen bir Codex eklentisidir. Herkese açık sürüm bilinçli olarak yalnızca öneri sunar: hiçbir zaman bir görevi çatallamaz, oluşturmaz, göreve gitmez, görevi arşivlemez veya yeniden yürütmez.

## Bu proje neden var

Model seçimi ile akıl yürütme çabası birbirinden ayrı kararlardır. Kısa ancak riskli bir görev daha güçlü bir model gerektirebilir; uzun, tekrarlayan ve doğrulanabilir bir iş ise daha hızlı bir modelden yararlanabilir. Bu eklenti, model seçimini görünmez bir yan etkiye dönüştürmeden bu ödünleşimleri açık hâle getirir.

Herkese açık sözleşme dört kurala uyar:

- etkinleştirme `$auto-route-for-codex` aracılığıyla açıkça yapılır;
- deterministik yönlendiriciye yalnızca listelenmiş profil alanları ulaşır;
- bir öneri yalnızca host tarafından sağlanan model ve thinking değerleriyle çözümlenir;
- herkese açık her karar `stay + none|efficiency + none + keep` olarak kalır.

## Hızlı başlangıç

Ön koşullar:

- eklentileri ve açık skill çağrısını destekleyen bir Codex arayüzü;
- `PATH` üzerinde erişilebilir Codex CLI;
- herkese açık Git deposuna erişim.

```sh
codex plugin marketplace add jacob101519/auto-route-for-codex --ref v0.4.0-alpha.1
codex plugin add auto-route-for-codex@jacob101519
```

Yeni bir Codex görevi başlatın, **Auto Route for Codex** seçeneğini seçin veya şunu çağırın:

```text
$auto-route-for-codex Review this task and recommend a sufficient Codex setting.
```

Eklenti, sürümlendirilmiş bir öneri döndürür. Geçerli görevin modelini veya ayarlarını değiştirmez.

## Herkese açık güvenlik sınırı

Dahil edilenler:

- katı JSON girdi ve çıktı schemaları;
- deterministik yönlendirme mantığı;
- yalnızca öneri sunan testler ve semantik negatif durumlar;
- herkese açık depo ve release doğrulama scriptleri;
- İngilizce belgeler ve eksiksiz Basitleştirilmiş Çince çeviriler.

Bilinçli olarak hariç tutulanlar:

- yerel oturum dosyası okuyucuları;
- özel geçerli ayar makbuzları veya katalogları;
- görev çatallama, göreve gitme, arşivleme ve yeniden yürütme orkestrasyonu;
- çalışma zamanı logları, kimlik bilgileri, yerel yollar, görev tanımlayıcıları veya özel yapılandırma;
- otomatik model değişiklikleri veya genel Codex yapılandırmasına yazma işlemleri.

[Gizlilik ve veri akışı](docs/privacy-and-data-flow.md) ile [Yönlendirme politikası](docs/routing-policy.md) belgelerine bakın.

## Depo haritası

| Yol | Amaç |
|---|---|
| `.codex-plugin/plugin.json` | Eklenti manifesti |
| `.agents/plugins/marketplace.json` | Marketplace girdisi |
| `skills/auto-route-for-codex/` | Skill, schemalar, yönlendirici ve testler |
| `docs/` | Kaynak niteliğindeki İngilizce belgeler |
| `docs/i18n/zh-CN/` | Eksiksiz Basitleştirilmiş Çince çeviriler |
| `scripts/verify_public_repo.py` | Depo, çeviri, gizlilik ve bağlantı kontrolleri |
| `scripts/build_release.py` | Deterministik eklenti ZIP'i ve `SHA256SUMS` oluşturucu |

## Temiz bir klondan doğrulama

```sh
python3 scripts/verify_public_repo.py
python3 -m unittest discover -s skills/auto-route-for-codex/tests -v
python3 skills/auto-route-for-codex/scripts/validate_contracts.py
python3 scripts/build_release.py --output-dir dist
```

Yerel kontrollerin geçmesi depo sözleşmesini doğrular. Bu, her Codex host sürümünün aynı eklenti veya model arayüzünü sunduğunu kanıtlamaz; [Uyumluluk](docs/compatibility.md) belgesine bakın.

## Belgeler

- [Mimari](docs/architecture.md)
- [Kurulum ve geri alma](docs/installation.md)
- [Yapılandırma sözleşmesi](docs/configuration.md)
- [Gizlilik ve veri akışı](docs/privacy-and-data-flow.md)
- [Yönlendirme politikası](docs/routing-policy.md)
- [Uyumluluk](docs/compatibility.md)
- [Sorun giderme](docs/troubleshooting.md)
- [SSS](docs/faq.md)

## Proje durumu

`v0.4.0-alpha.1`, herkese açık ilk alfa sürümüdür. API ve paket düzeni kararlı bir sürümden önce değişebilir. [CHANGELOG.md](CHANGELOG.md) ve [ROADMAP.md](ROADMAP.md) belgelerine bakın.

## Katkı ve güvenlik

Bir pull request açmadan önce [CONTRIBUTING.md](CONTRIBUTING.md) belgesini okuyun. Güvenlik sorunlarını [SECURITY.md](SECURITY.md) belgesinde açıklandığı şekilde GitHub özel güvenlik açığı bildirimi aracılığıyla bildirin; hassas raporları herkese açık bir issue içinde yayımlamayın.

## Lisans

Apache License 2.0. [LICENSE](LICENSE) ve [NOTICE](NOTICE) belgelerine bakın.
