---
translation_of: README.md
source_revision: docs-v0.5.0-alpha.1
last_synced_version: 0.5.0-alpha.1
---

# Auto Route for Codex

**ภาษา:** [English](README.md) | [Português (Brasil)](README.pt-BR.md) | [简体中文](README.zh-CN.md) | [繁體中文](README.zh-TW.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Türkçe](README.tr.md) | [Русский](README.ru.md) | [Tiếng Việt](README.vi.md) | ไทย | [Deutsch](README.de.md) | [Español](README.es.md)

> โปรเจกต์ชุมชนระยะอัลฟา ไม่ใช่ผลิตภัณฑ์อย่างเป็นทางการของ OpenAI

Auto Route for Codex เป็นปลั๊กอิน Codex ที่ผู้ใช้ต้องเลือกเปิดใช้อย่างชัดเจน โดยแนะนำบทบาทของโมเดล ระดับการใช้เหตุผล และโครงสร้างการทำงานที่เพียงพอจากโปรไฟล์งานซึ่งจำกัดข้อมูลเพื่อคุ้มครองความเป็นส่วนตัว บน host ของ Codex Desktop ที่รองรับ ระบบสามารถทำงานที่เน้น `quality` หรือ `parallelism` ต่อใน fork ได้เมื่อผ่าน capability gate และ evidence gate เท่านั้น สภาพแวดล้อมอื่นจะลดระดับอย่างปลอดภัยเป็นคำแนะนำในงานปัจจุบัน

## เหตุผลที่มีโปรเจกต์นี้

การเลือกโมเดลและระดับการใช้เหตุผลเป็นการตัดสินใจคนละส่วน งานที่สั้นแต่มีความเสี่ยงอาจต้องใช้โมเดลที่มีความสามารถสูงกว่า ขณะที่งานระยะยาว ซ้ำเดิม และตรวจสอบผลได้อาจเหมาะกับโมเดลที่เร็วกว่า ปลั๊กอินนี้ทำให้ข้อแลกเปลี่ยนเหล่านั้นชัดเจน โดยไม่ทำให้การเลือกโมเดลกลายเป็นผลข้างเคียงที่มองไม่เห็น

สัญญาสาธารณะปฏิบัติตามกฎหกข้อ:

- การเปิดใช้งานต้องทำอย่างชัดเจนผ่าน `$auto-route-for-codex`;
- เฉพาะฟิลด์โปรไฟล์ที่ระบุไว้เท่านั้นที่จะถูกส่งไปยังตัวกำหนดเส้นทางแบบกำหนดแน่นอน;
- current setting จะให้ความสำคัญกับ host-injected evidence ก่อน หากไม่มีข้อมูลดังกล่าว bounded fallback `read_current_setting.py` จะส่งออกได้เฉพาะ `current` และ `current_provenance` และผลลัพธ์ `unknown` ทุกกรณีจะคงเป็น recommendation-only;
- การทำงานต่อต้องใช้ Codex Desktop, task tool ที่จำเป็นทั้งหมด, current-setting และ catalog evidence ที่ `verified` รวมทั้ง model และ thinking ที่ host รองรับ;
- routing ต้องมี `host_capabilities.source_task_context=true` และการโอนแต่ละครั้งต้องมี `CODEX_THREAD_ID` ที่ถูกต้องแยกจากกัน; `transfer_state.py` สร้าง `source_binding_sha256` ในเครื่องและไม่เคยเก็บหรือส่งออกตัวระบุต้นทางดิบ;
- side effect แต่ละรายการใน `fork -> send -> readback -> navigate -> archive` ต้องมี atomic reservation ของตนเอง และจะ archive ต้นทางได้ต่อเมื่อลำดับที่ยืนยันแล้วไปถึงปลายทางเดียวเท่านั้น

## เริ่มต้นอย่างรวดเร็ว

ข้อกำหนดเบื้องต้น:

- อินเทอร์เฟซ Codex ที่รองรับปลั๊กอินและการเรียกใช้สกิลอย่างชัดเจน;
- Codex CLI ที่พร้อมใช้งานใน `PATH`;
- สิทธิ์เข้าถึง Git repository สาธารณะ

```sh
codex plugin marketplace add jacob101519/auto-route-for-codex --ref v0.5.0-alpha.1
codex plugin add auto-route-for-codex@jacob101519
```

เริ่มงาน Codex ใหม่ เลือก **Auto Route for Codex** หรือเรียกใช้:

```text
$auto-route-for-codex Review this task and use a sufficient Codex setting.
```

ปลั๊กอินจะส่งคืน decision ที่มีเวอร์ชันเสมอและให้ความสำคัญกับ host-injected current setting ก่อน หากไม่มี observation ดังกล่าว แต่มี `CODEX_THREAD_ID` และ `CODEX_HOME` ที่ใช้งานได้ `read_current_setting.py` จะตรวจสอบได้เฉพาะ local session ที่ตรงกันใน `$CODEX_HOME/sessions` และส่งออก bounded result แบบ `current + current_provenance` โดยไม่มี task text, path หรือ thread identifier หาก reader ล้มเหลวจะคืน `unknown` บน Codex Desktop host ที่พร้อมใช้งาน mismatch แบบ `quality` หรือ `parallelism` ที่ผ่านการตรวจสอบสามารถทำต่อใน fork ด้วย `model` และ `thinking` ที่แนะนำ ส่วน mismatch แบบ `efficiency`, surface ที่ไม่รองรับ, tool ที่ขาด, การตั้งค่าที่ไม่รองรับ หรือ evidence แบบ `unknown|stale|uncertain` จะคง `stay` และ recommendation-only

ปลั๊กอินไม่แก้ native model picker, `config.toml`, ค่าเริ่มต้นถาวร, sandbox, approval policy, network access หรือ credential

การโอนย้ายทุกครั้งผูกกับงานต้นทาง หลักฐานจาก host ตอน routing ต้องประกาศ `host_capabilities.source_task_context=true` และตอนทำงานต้องมี `CODEX_THREAD_ID` ที่ถูกต้อง โดยต้องมีทั้งสองอย่าง `transfer_state.py` จะคำนวณ `source_binding_sha256` ภายในเครื่องและจะไม่บันทึกหรือส่งออกตัวระบุต้นทางแบบดิบ hash นี้อยู่ใน per-source lock key, canonical receipt, `authorization_binding`, reservation marker ทุกตัว และการตรวจสอบ transition ทุกครั้งรวมถึง archive confirmation ดังนั้นต้นทางเดียวกันไม่สามารถเริ่มการโอนครั้งที่สองด้วย `transfer_id` อื่น และต้นทางที่ไม่ตรงกันไม่สามารถ resume, confirm หรือ archive การโอนนั้นได้ หาก source context หาย ไม่ถูกต้อง หรือไม่ตรงกัน ระบบจะ fail closed

## การทำงานต่อบน Desktop ที่มี capability gate

เส้นทางเต็มใช้ได้เมื่อผ่านการตรวจสอบทั้งหมดต่อไปนี้:

1. surface ปัจจุบันคือ Codex Desktop;
2. host มี `fork_thread`, `send_message_to_thread`, `read_thread`, `navigate_to_codex_page` และ `set_thread_archived` ที่เข้ากันได้;
3. current-setting evidence เป็น `verified` และยังไม่หมดอายุ โดยใช้ host injection ก่อนและใช้ bounded fallback เมื่อจำเป็นเท่านั้น ส่วน model-catalog evidence ต้องเป็น `verified` และยังไม่หมดอายุด้วย;
4. live host รองรับ `model` และ `thinking` ที่แนะนำ;
5. ก่อนเรียก fork, send, readback, navigation หรือ archive แต่ละครั้ง `transfer_state.py --reserve-event` จะสร้าง atomic marker แบบ `O_EXCL` ใน durable default root `$CODEX_HOME/state/auto-route-for-codex` โดย `AUTO_ROUTE_STATE_HOME` เป็นเพียง explicit override/test hook และจะเรียก host เมื่อ `side_effect_authorized=true` ด้วย winner-only `reservation_lease` ที่ reservation ส่งคืนเท่านั้น;
6. prompt delivery ยืนยันค่า model และ thinking override ที่ใช้จริง destination readback ยืนยันว่าคำขอต้นฉบับที่ลบคำเรียกใช้แล้วถึง fork ที่ถูกต้อง และ navigation สำเร็จก่อนอนุญาต archive

lifecycle ตามลำดับคือ:

```text
planned
  -> fork_created
  -> prompt_delivery_confirmed
  -> destination_readback_confirmed
  -> navigation_confirmed
  -> source_archive_confirmed
```

Successful reservation จะส่งคืน winner-only `reservation_lease` หลังทำ host side effect การยืนยันจะใช้ `--event` กับ `--router-input` เดิมและส่ง lease ผ่าน `--reservation-lease` ส่วน `prompt_delivery_confirmed` ต้องมี `--observed-model` และ `--observed-thinking` เพิ่มเติม Canonical receipt จะเก็บ `pending_reservation` อย่างถาวร ดังนั้นแม้ marker หายไป การ reserve ซ้ำก็จะคืน `reconcile_required` และ `side_effect_authorized=false` โดยไม่อนุญาต side effect ซ้ำ Marker, receipt และ state directory ที่สร้างใหม่ทั้งหมดจะได้รับ `fsync` Default root `$CODEX_HOME/state/auto-route-for-codex` มีความ durable อยู่แล้ว ส่วน `AUTO_ROUTE_STATE_HOME` เป็นเพียง explicit override/test hook ไม่จำเป็นต่อ persistence Reservation marker มีเพียง hashes และ bounded transfer metadata ไม่บันทึก raw task text และไม่เข้าไปใน package หรือ repository

`reservation_lease` เป็น ephemeral coordination nonce และ bearer capability ไม่ใช่ credential ค่านี้จะถูกส่งออกเพียงครั้งเดียวให้กับ operation ที่ชนะผ่าน private local CLI stdout หรือ tool-execution detail ที่เทียบเท่า แล้วส่งกลับด้วย process argument `--reservation-lease`; interface ที่เข้ากันได้ในอนาคตอาจใช้ stdin แทน ต้องเก็บค่านี้ไว้ภายใน operation ส่วนตัวนั้นเท่านั้น ห้ามคัดลอกไปยัง task prompt, final หรือ user-facing prose อื่น, package หรือ repository, external telemetry, Issue หรือ support report หรือ durable log ขอบเขตนี้ช่วยลดการเปิดเผยโดยไม่ตั้งใจ แต่ไม่ได้ป้องกัน lease จาก malicious same-user writer

Evidence ที่หมดอายุหรือ stale จะไม่อนุญาต reservation ใหม่ หาก reservation ถูกบันทึกอย่าง durable เป็น `pending_reservation` แล้วในขณะที่ immutable binding ยังใช้ได้ lease ที่ตรงกันจะใช้ได้เพียงเพื่อยืนยัน operation ที่เริ่มไปแล้วนั้นหรือทำเครื่องหมายเป็น `uncertain` หลัง evidence TTL เท่านั้น ข้อยกเว้นนี้ไม่สามารถอนุญาต host side effect อื่นได้ State mutation interface ที่รองรับเพียงอย่างเดียวคือ CLI `transfer_state.py` ส่วน Python import ของ implementation และการแก้ state file โดยตรงเป็น unsupported internals

timeout, mismatch, ผลลัพธ์ไม่สมบูรณ์ หรือ side effect ที่ไม่ชัดเจนจะเข้าสู่ `uncertain` ห้ามส่งซ้ำ สร้าง fork ใหม่ เรียกคำขอต้นฉบับในงานต้นทาง หรือ archive ต้นทาง หากทราบ destination identifier จะตรวจสอบได้เฉพาะปลายทางนั้น หาก fork สำเร็จจริงแต่ host response สูญหายก่อนส่งคืน destination identifier ใด ๆ durable replay protection จะยังคงป้องกันการสร้าง fork ใหม่ การทำงานในต้นทาง และการ archive ต้นทาง แต่ Plugin ไม่สามารถค้นหาปลายทางที่ไม่ทราบได้ด้วยตนเอง ให้คงต้นทางไว้ให้มองเห็นได้ และใช้ host UI หรือช่องทาง support เพื่อค้นหาหรือกู้คืนปลายทาง วิธีนี้ป้องกัน duplicate execution แต่ไม่ได้พิสูจน์ว่า lost task เป็นศูนย์ Receipt และ reservation hashes ให้ deterministic integrity ไม่ใช่ signature ส่วน malicious local writer ที่สามารถแทนที่ local state อยู่นอก threat boundary

## ขอบเขตความปลอดภัยของรุ่นสาธารณะ

สิ่งที่รวมอยู่:

- JSON schema สำหรับ input, output และ transfer receipt ที่เข้มงวด;
- deterministic routing, bounded current-setting fallback และ reservation-backed transfer-state logic;
- privacy-preserving source-task binding ที่ป้องกันการทำงานต่อจากต้นทางอื่น และป้องกัน `transfer_id` หลายค่าสำหรับต้นทางเดียว;
- contract สำหรับ Codex Desktop task continuation ที่มี capability gate;
- route, contract, semantic-negative, state-machine และ failure-boundary tests;
- การตรวจสอบ repository, privacy, translation และ release;
- เอกสารภาษาอังกฤษที่เป็นแหล่งอ้างอิง คำแปลจีนตัวย่อฉบับสมบูรณ์ และ README หลายภาษา

สิ่งที่ตั้งใจไม่รวม:

- unbounded session scanning, task-text extraction หรือการส่งออก session content และ reservation marker;
- current-setting receipt ส่วนตัว, private catalog หรือ local marketplace state;
- runtime log, credential, path ภายในเครื่อง, task identifier หรือ private configuration;
- hidden invocation, การ transfer อัตโนมัติสำหรับ `efficiency`, การแก้ native model picker หรือ global Codex configuration;
- การอ้างว่า Codex CLI, IDE, cloud, API หรือ agent อื่นมี Codex Desktop task tool

ดู [ความเป็นส่วนตัวและการไหลของข้อมูล](docs/privacy-and-data-flow.md), [นโยบายการกำหนดเส้นทาง](docs/routing-policy.md) และ [ความเข้ากันได้](docs/compatibility.md)

## แผนผัง repository

| Path | วัตถุประสงค์ |
|---|---|
| `.codex-plugin/plugin.json` | Manifest ของปลั๊กอิน |
| `.agents/plugins/marketplace.json` | รายการ Marketplace |
| `skills/auto-route-for-codex/` | สกิล, schema, bounded current-setting reader, ตัวกำหนดเส้นทาง, reservation-backed transfer reducer และการทดสอบ |
| `docs/` | เอกสารภาษาอังกฤษที่เป็นแหล่งข้อมูลหลัก |
| `docs/i18n/zh-CN/` | คำแปลภาษาจีนตัวย่อฉบับสมบูรณ์ |
| `scripts/verify_public_repo.py` | การตรวจสอบ repository, คำแปล, ความเป็นส่วนตัว และลิงก์ |
| `scripts/build_release.py` | ตัวสร้าง ZIP ของปลั๊กอินและ `SHA256SUMS` แบบกำหนดผลแน่นอน |

## ตรวจสอบจาก clone ที่สะอาด

```sh
python3 -m pip install --disable-pip-version-check PyYAML==6.0.3 jsonschema==4.26.0
python3 scripts/verify_public_repo.py
python3 -m unittest discover -s skills/auto-route-for-codex/tests -v
python3 skills/auto-route-for-codex/scripts/validate_contracts.py
python3 scripts/build_release.py --output-dir dist
```

เมื่อการตรวจสอบภายในเครื่องผ่าน จะเป็นการยืนยันสัญญาของ repository แต่ไม่ได้พิสูจน์ว่าโฮสต์ Codex ทุกเวอร์ชันเปิดเผยอินเทอร์เฟซของปลั๊กอินหรือโมเดลเหมือนกัน โปรดดู [ความเข้ากันได้](docs/compatibility.md)

## เอกสาร

- [สถาปัตยกรรม](docs/architecture.md)
- [การติดตั้งและการย้อนกลับ](docs/installation.md)
- [สัญญาการกำหนดค่า](docs/configuration.md)
- [ความเป็นส่วนตัวและการไหลของข้อมูล](docs/privacy-and-data-flow.md)
- [นโยบายการกำหนดเส้นทาง](docs/routing-policy.md)
- [ความเข้ากันได้](docs/compatibility.md)
- [การแก้ไขปัญหา](docs/troubleshooting.md)
- [คำถามที่พบบ่อย](docs/faq.md)

## สถานะโปรเจกต์

`v0.5.0-alpha.1` เป็นอัลฟาสาธารณะรุ่นแรกที่มี Codex Desktop task continuation แบบ capability gate API และโครงสร้างแพ็กเกจอาจเปลี่ยนแปลงก่อนการออกเวอร์ชันเสถียร ดู [CHANGELOG.md](CHANGELOG.md) และ [ROADMAP.md](ROADMAP.md)

## การมีส่วนร่วมและความปลอดภัย

โปรดอ่าน [CONTRIBUTING.md](CONTRIBUTING.md) ก่อนเปิด pull request รายงานปัญหาด้านความปลอดภัยผ่าน private vulnerability reporting ของ GitHub ตามที่อธิบายไว้ใน [SECURITY.md](SECURITY.md) และอย่าเผยแพร่รายงานที่มีข้อมูลละเอียดอ่อนใน issue สาธารณะ

## ใบอนุญาต

Apache License 2.0 ดู [LICENSE](LICENSE) และ [NOTICE](NOTICE)
