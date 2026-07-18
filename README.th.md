---
translation_of: README.md
source_revision: docs-v0.4.0-alpha.1
last_synced_version: 0.4.0-alpha.1
---

# Auto Route for Codex

**ภาษา:** [English](README.md) | [Português (Brasil)](README.pt-BR.md) | [简体中文](README.zh-CN.md) | [繁體中文](README.zh-TW.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Türkçe](README.tr.md) | [Русский](README.ru.md) | [Tiếng Việt](README.vi.md) | ไทย | [Deutsch](README.de.md) | [Español](README.es.md)

> โปรเจกต์ชุมชนระยะอัลฟา ไม่ใช่ผลิตภัณฑ์อย่างเป็นทางการของ OpenAI

Auto Route for Codex เป็นปลั๊กอิน Codex ที่ผู้ใช้ต้องเลือกเปิดใช้อย่างชัดเจน โดยแนะนำบทบาทของโมเดล ระดับการใช้เหตุผล และโครงสร้างการทำงานที่เพียงพอจากโปรไฟล์งานซึ่งจำกัดข้อมูลเพื่อคุ้มครองความเป็นส่วนตัว รุ่นสาธารณะถูกออกแบบให้ให้คำแนะนำเท่านั้น โดยจะไม่สร้างแขนงงาน สร้างงานใหม่ นำทาง เก็บถาวร หรือเรียกใช้งานซ้ำ

## เหตุผลที่มีโปรเจกต์นี้

การเลือกโมเดลและระดับการใช้เหตุผลเป็นการตัดสินใจคนละส่วน งานที่สั้นแต่มีความเสี่ยงอาจต้องใช้โมเดลที่มีความสามารถสูงกว่า ขณะที่งานระยะยาว ซ้ำเดิม และตรวจสอบผลได้อาจเหมาะกับโมเดลที่เร็วกว่า ปลั๊กอินนี้ทำให้ข้อแลกเปลี่ยนเหล่านั้นชัดเจน โดยไม่ทำให้การเลือกโมเดลกลายเป็นผลข้างเคียงที่มองไม่เห็น

สัญญาสาธารณะปฏิบัติตามกฎสี่ข้อ:

- การเปิดใช้งานต้องทำอย่างชัดเจนผ่าน `$auto-route-for-codex`;
- เฉพาะฟิลด์โปรไฟล์ที่ระบุไว้เท่านั้นที่จะถูกส่งไปยังตัวกำหนดเส้นทางแบบกำหนดแน่นอน;
- คำแนะนำจะจับคู่เฉพาะกับค่าโมเดลและโหมดการคิดที่โฮสต์จัดเตรียมไว้;
- การตัดสินใจสาธารณะทุกครั้งยังคงเป็น `stay + none|efficiency + none + keep`.

## เริ่มต้นอย่างรวดเร็ว

ข้อกำหนดเบื้องต้น:

- อินเทอร์เฟซ Codex ที่รองรับปลั๊กอินและการเรียกใช้สกิลอย่างชัดเจน;
- Codex CLI ที่พร้อมใช้งานใน `PATH`;
- สิทธิ์เข้าถึง Git repository สาธารณะ

```sh
codex plugin marketplace add jacob101519/auto-route-for-codex --ref v0.4.0-alpha.1
codex plugin add auto-route-for-codex@jacob101519
```

เริ่มงาน Codex ใหม่ เลือก **Auto Route for Codex** หรือเรียกใช้:

```text
$auto-route-for-codex Review this task and recommend a sufficient Codex setting.
```

ปลั๊กอินจะส่งคืนคำแนะนำที่มีการกำกับเวอร์ชัน และจะไม่เปลี่ยนโมเดลหรือการตั้งค่าของงานปัจจุบัน

## ขอบเขตความปลอดภัยของรุ่นสาธารณะ

สิ่งที่รวมอยู่:

- JSON schema สำหรับอินพุตและเอาต์พุตที่เข้มงวด;
- ตรรกะการกำหนดเส้นทางแบบกำหนดแน่นอน;
- การทดสอบโหมดให้คำแนะนำเท่านั้นและกรณีลบเชิงความหมาย;
- สคริปต์ตรวจสอบ repository สาธารณะและ release;
- เอกสารภาษาอังกฤษและคำแปลภาษาจีนตัวย่อฉบับสมบูรณ์

สิ่งที่ตั้งใจไม่รวม:

- ตัวอ่านไฟล์ session ภายในเครื่อง;
- receipt หรือ catalog ส่วนตัวของการตั้งค่าปัจจุบัน;
- การประสานงานสำหรับการสร้างแขนงงาน การนำทาง การเก็บถาวร และการเรียกใช้งานซ้ำ;
- runtime log, credential, path ภายในเครื่อง, task identifier หรือ private configuration;
- การเปลี่ยนโมเดลอัตโนมัติหรือการเขียนค่าไปยัง global Codex configuration

ดู [ความเป็นส่วนตัวและการไหลของข้อมูล](docs/privacy-and-data-flow.md) และ [นโยบายการกำหนดเส้นทาง](docs/routing-policy.md)

## แผนผัง repository

| Path | วัตถุประสงค์ |
|---|---|
| `.codex-plugin/plugin.json` | Manifest ของปลั๊กอิน |
| `.agents/plugins/marketplace.json` | รายการ Marketplace |
| `skills/auto-route-for-codex/` | สกิล, schema, ตัวกำหนดเส้นทาง และการทดสอบ |
| `docs/` | เอกสารภาษาอังกฤษที่เป็นแหล่งข้อมูลหลัก |
| `docs/i18n/zh-CN/` | คำแปลภาษาจีนตัวย่อฉบับสมบูรณ์ |
| `scripts/verify_public_repo.py` | การตรวจสอบ repository, คำแปล, ความเป็นส่วนตัว และลิงก์ |
| `scripts/build_release.py` | ตัวสร้าง ZIP ของปลั๊กอินและ `SHA256SUMS` แบบกำหนดผลแน่นอน |

## ตรวจสอบจาก clone ที่สะอาด

```sh
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

`v0.4.0-alpha.1` เป็นรุ่นอัลฟาสาธารณะรุ่นแรก API และโครงสร้างแพ็กเกจอาจเปลี่ยนแปลงก่อนการออกเวอร์ชันเสถียร ดู [CHANGELOG.md](CHANGELOG.md) และ [ROADMAP.md](ROADMAP.md)

## การมีส่วนร่วมและความปลอดภัย

โปรดอ่าน [CONTRIBUTING.md](CONTRIBUTING.md) ก่อนเปิด pull request รายงานปัญหาด้านความปลอดภัยผ่าน private vulnerability reporting ของ GitHub ตามที่อธิบายไว้ใน [SECURITY.md](SECURITY.md) และอย่าเผยแพร่รายงานที่มีข้อมูลละเอียดอ่อนใน issue สาธารณะ

## ใบอนุญาต

Apache License 2.0 ดู [LICENSE](LICENSE) และ [NOTICE](NOTICE)
