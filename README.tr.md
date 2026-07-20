---
translation_of: README.md
source_revision: docs-v0.5.0-alpha.1
last_synced_version: 0.5.0-alpha.1
---

# Auto Route for Codex

**Dil:** [English](README.md) | [Português (Brasil)](README.pt-BR.md) | [简体中文](README.zh-CN.md) | [繁體中文](README.zh-TW.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | Türkçe | [Русский](README.ru.md) | [Tiếng Việt](README.vi.md) | [ไทย](README.th.md) | [Deutsch](README.de.md) | [Español](README.es.md)

> Alfa aşamasındaki topluluk projesi. Resmî bir OpenAI ürünü değildir.

Auto Route for Codex, gizlilik sınırları belirlenmiş bir görev profilinden yeterli bir model rolü, akıl yürütme çabası ve yürütme topolojisi öneren, açıkça etkinleştirilen bir Codex eklentisidir. Uyumlu bir Codex Desktop host üzerinde, `quality` veya `parallelism` açısından hassas bir görevi ancak host capability ve evidence gate kontrolleri geçerse fork içinde sürdürebilir. Diğer ortamlar güvenli biçimde geçerli görevdeki öneriye geri döner.

## Bu proje neden var

Model seçimi ile akıl yürütme çabası birbirinden ayrı kararlardır. Kısa ancak riskli bir görev daha güçlü bir model gerektirebilir; uzun, tekrarlayan ve doğrulanabilir bir iş ise daha hızlı bir modelden yararlanabilir. Bu eklenti, model seçimini görünmez bir yan etkiye dönüştürmeden bu ödünleşimleri açık hâle getirir.

Herkese açık sözleşme altı kurala uyar:

- etkinleştirme `$auto-route-for-codex` aracılığıyla açıkça yapılır;
- deterministik yönlendiriciye yalnızca listelenmiş profil alanları ulaşır;
- geçerli ayar host-injected evidence değerini önceler; bu kanıt yoksa sınırlı `read_current_setting.py` fallback yalnızca `current` ve `current_provenance` üretebilir ve her `unknown` sonucu recommendation-only kalır;
- görev devamı için Codex Desktop, gerekli tüm task tool öğeleri, doğrulanmış current-setting ve catalog evidence ile host tarafından desteklenen önerilen model ve thinking gerekir;
- routing için `host_capabilities.source_task_context=true` gerekir ve her aktarım ayrıca geçerli bir `CODEX_THREAD_ID` gerektirir; `transfer_state.py` yerel olarak `source_binding_sha256` türetir ve ham kaynak tanımlayıcısını asla kalıcılaştırmaz veya dışa vermez;
- her `fork -> send -> readback -> navigate -> archive` side effect kendi atomic reservation kaydını gerektirir ve kaynak yalnızca doğrulanmış sıra tek bir hedefe ulaştıktan sonra arşivlenebilir.

## Hızlı başlangıç

Ön koşullar:

- eklentileri ve açık skill çağrısını destekleyen bir Codex arayüzü;
- `PATH` üzerinde erişilebilir Codex CLI;
- herkese açık Git deposuna erişim.

```sh
codex plugin marketplace add jacob101519/auto-route-for-codex --ref v0.5.0-alpha.1
codex plugin add auto-route-for-codex@jacob101519
```

Yeni bir Codex görevi başlatın, **Auto Route for Codex** seçeneğini seçin veya şunu çağırın:

```text
$auto-route-for-codex Review this task and use a sufficient Codex setting.
```

Eklenti her zaman sürümlendirilmiş bir decision döndürür ve host-injected current setting değerini önceler. Bu observation yoksa ve `CODEX_THREAD_ID` ile kullanılabilir bir `CODEX_HOME` varsa `read_current_setting.py` yalnızca `$CODEX_HOME/sessions` altındaki eşleşen local session kaydını inceleyebilir ve task text, path veya thread identifier içermeyen sınırlı bir `current + current_provenance` sonucu üretebilir. Reader failure `unknown` döndürür. Uyumlu bir Codex Desktop host üzerinde doğrulanmış `quality` veya `parallelism` mismatch, önerilen `model` ve `thinking` ile fork içinde sürdürülebilir; `efficiency` mismatch, desteklenmeyen surface, eksik tool, desteklenmeyen ayar veya `unknown|stale|uncertain` evidence ise `stay` ve recommendation-only olarak kalır.

Eklenti native model picker, `config.toml`, kalıcı varsayılanlar, sandbox, approval policy, network access veya credential değerlerini değiştirmez.

Her aktarım kaynak göreve bağlanır: yönlendirme anındaki host evidence `host_capabilities.source_task_context=true` değerini bildirmeli, çalışma anında da geçerli bir `CODEX_THREAD_ID` bulunmalıdır; ikisi de zorunludur. `transfer_state.py`, `source_binding_sha256` değerini yerel olarak türetir ve ham kaynak kimliğini kalıcılaştırmaz veya çıktılamaz. Bu hash; kaynak başına kilit anahtarına, canonical receipt kaydına, `authorization_binding` alanına, her reservation marker kaydına ve archive confirmation dahil tüm transition doğrulamalarına girer. Böylece aynı kaynak farklı bir `transfer_id` ile ikinci aktarımı başlatamaz; yanlış kaynak da aktarımı sürdüremez, onaylayamaz veya arşivleyemez. Eksik, geçersiz ya da uyumsuz kaynak bağlamı fail closed olur.

## Capability gate korumalı Desktop devamı

Tam yol yalnızca şu kontrollerin tümü geçerse kullanılabilir:

1. geçerli surface Codex Desktop'tır;
2. host uyumlu `fork_thread`, `send_message_to_thread`, `read_thread`, `navigate_to_codex_page` ve `set_thread_archived` capability öğelerini sunar;
3. current-setting evidence `verified` ve günceldir, önce host injection kullanır ve yalnızca gerektiğinde bounded fallback uygular; model-catalog evidence de `verified` ve günceldir;
4. önerilen `model` ve `thinking` canlı host tarafından desteklenir;
5. her fork, send, readback, navigation veya archive çağrısından önce `transfer_state.py --reserve-event`, durable default root `$CODEX_HOME/state/auto-route-for-codex` altında atomic bir `O_EXCL` marker oluşturur. `AUTO_ROUTE_STATE_HOME` yalnızca explicit override/test hook'tur ve host call yalnızca `side_effect_authorized=true` olduğunda reservation tarafından döndürülen winner-only `reservation_lease` ile çalışır;
6. prompt delivery gerçek model ve thinking override değerlerini doğrular, destination readback temizlenmiş özgün isteğin tam fork'a ulaştığını kanıtlar ve archive yetkilendirilmeden önce navigation başarılı olur.

Sıralı lifecycle şöyledir:

```text
planned
  -> fork_created
  -> prompt_delivery_confirmed
  -> destination_readback_confirmed
  -> navigation_confirmed
  -> source_archive_confirmed
```

Successful reservation winner-only bir `reservation_lease` döndürür. Host side effect sonrasında aynı `--router-input` ve `--event` kullanılır, lease ise `--reservation-lease` ile doğrulamaya geçirilir. `prompt_delivery_confirmed` ayrıca `--observed-model` ve `--observed-thinking` gerektirir. Canonical receipt `pending_reservation` değerini kalıcı tutar; dolayısıyla marker eksik olsa bile yinelenen reserve `reconcile_required` ve `side_effect_authorized=false` döndürür ve side effect'i yeniden yetkilendirmez. Marker, receipt ve yeni oluşturulan state directory öğelerinin tümü `fsync` edilir. Varsayılan root `$CODEX_HOME/state/auto-route-for-codex` durable'dır; `AUTO_ROUTE_STATE_HOME` yalnızca explicit override/test hook'tur ve kalıcılık için gerekli değildir. Reservation marker yalnızca hash değerleri ve bounded transfer metadata içerir, raw task text saklamaz ve package ya da repository içine girmez.

`reservation_lease`, geçici bir coordination nonce ve bearer capability değeridir; credential değildir. Kazanan işlemin private local CLI stdout çıktısında veya eşdeğer tool-execution detail içinde yalnızca bir kez üretilir ve process argument olarak `--reservation-lease` ile geri verilir; gelecekteki uyumlu bir arayüz bunun yerine stdin kullanabilir. Değeri bu özel işlem içinde tutun. Task prompt, final veya başka user-facing prose, package ya da repository, external telemetry, Issue veya support report ya da durable log içine asla kopyalamayın. Bu sınır kazara ifşayı azaltır ancak lease'i malicious same-user writer'a karşı korumaz.

Süresi dolmuş veya stale evidence hiçbir zaman yeni reservation yetkilendirmez. Immutable binding geçerliyken reservation zaten kalıcı olarak `pending_reservation` şeklinde kaydedildiyse, eşleşen lease evidence TTL sonrasında yalnızca tam olarak başlatılmış bu işlemi doğrulayabilir veya `uncertain` olarak işaretleyebilir. Bu istisna başka bir host side effect yetkilendiremez. Desteklenen tek state mutation interface `transfer_state.py` CLI'dır. Uygulamanın Python import yoluyla kullanılması ve state file üzerinde doğrudan değişiklik unsupported internals kapsamındadır.

Timeout, mismatch, eksik sonuç veya belirsiz side effect `uncertain` durumuna girer. Eklenti yeniden gönderemez, yeniden fork oluşturamaz, özgün isteği kaynakta çalıştıramaz veya kaynağı arşivleyemez. Bir destination identifier biliniyorsa yalnızca o hedefi uzlaştırabilir. Fork gerçekte başarılı olmuş ancak herhangi bir destination identifier dönmeden host response kaybolmuşsa durable replay protection yeniden fork oluşturmayı, kaynakta çalıştırmayı ve kaynağı arşivlemeyi engellemeye devam eder; ancak eklenti bilinmeyen hedefi kendi başına bulamaz. Kaynağı görünür tutun ve hedefi bulmak veya kurtarmak için host UI ya da support channel kullanın. Bu, duplicate execution durumunu önler ancak lost task sayısının sıfır olduğunu kanıtlamaz. Receipt ve reservation hash değerleri deterministic integrity sağlar, signature değildir; local state değerini değiştirebilen malicious local writer threat boundary dışındadır.

## Herkese açık güvenlik sınırı

Dahil edilenler:

- katı JSON girdi, çıktı ve transfer-receipt schemaları;
- deterministik yönlendirme, bounded current-setting fallback ve reservation-backed transfer-state mantığı;
- farklı bir kaynaktan sürdürmeyi ve tek bir kaynak için birden fazla `transfer_id` kullanılmasını engelleyen gizliliği koruyan kaynak-görev bağlaması;
- capability-gated Codex Desktop task continuation sözleşmesi;
- route, contract, semantic-negative, state-machine ve failure-boundary testleri;
- herkese açık depo, gizlilik, çeviri ve release doğrulaması;
- yetkili İngilizce belgeler, eksiksiz Basitleştirilmiş Çince çeviri ve yerelleştirilmiş README girişleri.

Bilinçli olarak hariç tutulanlar:

- unbounded session scanning, task-text extraction veya session content ile reservation marker dışa aktarımı;
- özel current-setting receipt, private catalog veya local marketplace state;
- çalışma zamanı logları, kimlik bilgileri, yerel yollar, görev tanımlayıcıları veya özel yapılandırma;
- hidden invocation, `efficiency` için otomatik transfer, native model picker değişikliği veya genel Codex yapılandırmasına yazma;
- Codex CLI, IDE, cloud, API veya başka agents ortamlarının Codex Desktop task tool sunduğu iddiası.

[Gizlilik ve veri akışı](docs/privacy-and-data-flow.md), [Yönlendirme politikası](docs/routing-policy.md) ve [Uyumluluk](docs/compatibility.md) belgelerine bakın.

## Depo haritası

| Yol | Amaç |
|---|---|
| `.codex-plugin/plugin.json` | Eklenti manifesti |
| `.agents/plugins/marketplace.json` | Marketplace girdisi |
| `skills/auto-route-for-codex/` | Skill, schemalar, bounded current-setting reader, yönlendirici, reservation-backed transfer reducer ve testler |
| `docs/` | Kaynak niteliğindeki İngilizce belgeler |
| `docs/i18n/zh-CN/` | Eksiksiz Basitleştirilmiş Çince çeviriler |
| `scripts/verify_public_repo.py` | Depo, çeviri, gizlilik ve bağlantı kontrolleri |
| `scripts/build_release.py` | Deterministik eklenti ZIP'i ve `SHA256SUMS` oluşturucu |

## Temiz bir klondan doğrulama

```sh
python3 -m pip install --disable-pip-version-check PyYAML==6.0.3 jsonschema==4.26.0
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

`v0.5.0-alpha.1`, capability-gated Codex Desktop task continuation içeren ilk genel alfa sürümüdür. API ve paket düzeni kararlı bir sürümden önce değişebilir. [CHANGELOG.md](CHANGELOG.md) ve [ROADMAP.md](ROADMAP.md) belgelerine bakın.

## Katkı ve güvenlik

Bir pull request açmadan önce [CONTRIBUTING.md](CONTRIBUTING.md) belgesini okuyun. Güvenlik sorunlarını [SECURITY.md](SECURITY.md) belgesinde açıklandığı şekilde GitHub özel güvenlik açığı bildirimi aracılığıyla bildirin; hassas raporları herkese açık bir issue içinde yayımlamayın.

## Lisans

Apache License 2.0. [LICENSE](LICENSE) ve [NOTICE](NOTICE) belgelerine bakın.
