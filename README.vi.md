---
translation_of: README.md
source_revision: docs-v0.4.0-alpha.1
last_synced_version: 0.4.0-alpha.1
---

# Auto Route for Codex

**Ngôn ngữ:** [English](README.md) | [Português (Brasil)](README.pt-BR.md) | [简体中文](README.zh-CN.md) | [繁體中文](README.zh-TW.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Türkçe](README.tr.md) | [Русский](README.ru.md) | Tiếng Việt | [ไทย](README.th.md) | [Deutsch](README.de.md) | [Español](README.es.md)

> Dự án cộng đồng ở giai đoạn alpha. Không phải là sản phẩm chính thức của OpenAI.

Auto Route for Codex là một plugin Codex yêu cầu người dùng chủ động bật, có chức năng đề xuất vai trò mô hình, mức độ suy luận và cấu trúc thực thi đủ dùng dựa trên hồ sơ tác vụ được giới hạn để bảo vệ quyền riêng tư. Phiên bản công khai được chủ đích giới hạn ở việc đưa ra đề xuất: nó không bao giờ phân nhánh, tạo mới, điều hướng, lưu trữ hoặc chạy lại một tác vụ.

## Vì sao dự án này tồn tại

Lựa chọn mô hình và mức độ suy luận là hai quyết định riêng biệt. Một tác vụ ngắn nhưng rủi ro có thể cần mô hình mạnh hơn, trong khi một công việc dài, lặp lại và có thể kiểm chứng có thể phù hợp hơn với mô hình nhanh hơn. Plugin này làm rõ những đánh đổi đó mà không biến việc chọn mô hình thành một tác dụng phụ vô hình.

Hợp đồng công khai tuân theo bốn quy tắc:

- việc kích hoạt phải được thực hiện rõ ràng thông qua `$auto-route-for-codex`;
- chỉ các trường hồ sơ đã được liệt kê mới được chuyển đến bộ định tuyến xác định;
- một đề xuất chỉ được phân giải theo các giá trị mô hình và chế độ suy luận do môi trường chủ cung cấp;
- mọi quyết định công khai luôn giữ nguyên `stay + none|efficiency + none + keep`.

## Bắt đầu nhanh

Điều kiện tiên quyết:

- một giao diện Codex hỗ trợ plugin và gọi kỹ năng một cách rõ ràng;
- Codex CLI khả dụng trong `PATH`;
- quyền truy cập vào kho Git công khai.

```sh
codex plugin marketplace add jacob101519/auto-route-for-codex --ref v0.4.0-alpha.1
codex plugin add auto-route-for-codex@jacob101519
```

Bắt đầu một tác vụ Codex mới, chọn **Auto Route for Codex**, hoặc gọi:

```text
$auto-route-for-codex Review this task and recommend a sufficient Codex setting.
```

Plugin trả về một đề xuất có phiên bản. Plugin không thay đổi mô hình hoặc cài đặt của tác vụ hiện tại.

## Ranh giới an toàn của phiên bản công khai

Bao gồm:

- lược đồ JSON nghiêm ngặt cho dữ liệu đầu vào và đầu ra;
- logic định tuyến xác định;
- các bài kiểm thử chỉ đưa ra đề xuất và các trường hợp kiểm thử ngữ nghĩa phủ định;
- các tập lệnh xác minh kho công khai và bản phát hành;
- tài liệu tiếng Anh và bản dịch tiếng Trung giản thể đầy đủ.

Chủ đích không bao gồm:

- trình đọc tệp phiên cục bộ;
- biên nhận hoặc danh mục riêng tư về cài đặt hiện tại;
- cơ chế điều phối phân nhánh, điều hướng, lưu trữ và chạy lại tác vụ;
- nhật ký thời gian chạy, thông tin xác thực, đường dẫn cục bộ, mã định danh tác vụ hoặc cấu hình riêng tư;
- tự động thay đổi mô hình hoặc ghi vào cấu hình Codex toàn cục.

Xem [Quyền riêng tư và luồng dữ liệu](docs/privacy-and-data-flow.md) và [Chính sách định tuyến](docs/routing-policy.md).

## Sơ đồ kho mã nguồn

| Đường dẫn | Mục đích |
|---|---|
| `.codex-plugin/plugin.json` | Tệp kê khai plugin |
| `.agents/plugins/marketplace.json` | Mục nhập marketplace |
| `skills/auto-route-for-codex/` | Kỹ năng, lược đồ, bộ định tuyến và bài kiểm thử |
| `docs/` | Tài liệu tiếng Anh có thẩm quyền |
| `docs/i18n/zh-CN/` | Bản dịch tiếng Trung giản thể đầy đủ |
| `scripts/verify_public_repo.py` | Kiểm tra kho mã nguồn, bản dịch, quyền riêng tư và liên kết |
| `scripts/build_release.py` | Trình tạo ZIP plugin và `SHA256SUMS` có tính xác định |

## Xác minh từ một bản sao sạch

```sh
python3 scripts/verify_public_repo.py
python3 -m unittest discover -s skills/auto-route-for-codex/tests -v
python3 skills/auto-route-for-codex/scripts/validate_contracts.py
python3 scripts/build_release.py --output-dir dist
```

Các bước kiểm tra cục bộ vượt qua sẽ xác thực hợp đồng của kho mã nguồn. Điều đó không chứng minh rằng mọi phiên bản môi trường Codex đều cung cấp cùng một giao diện plugin hoặc mô hình; hãy tham khảo [Khả năng tương thích](docs/compatibility.md).

## Tài liệu

- [Kiến trúc](docs/architecture.md)
- [Cài đặt và quay lui](docs/installation.md)
- [Hợp đồng cấu hình](docs/configuration.md)
- [Quyền riêng tư và luồng dữ liệu](docs/privacy-and-data-flow.md)
- [Chính sách định tuyến](docs/routing-policy.md)
- [Khả năng tương thích](docs/compatibility.md)
- [Khắc phục sự cố](docs/troubleshooting.md)
- [Câu hỏi thường gặp](docs/faq.md)

## Trạng thái dự án

`v0.4.0-alpha.1` là bản alpha công khai đầu tiên. API và bố cục gói có thể thay đổi trước khi phát hành phiên bản ổn định. Xem [CHANGELOG.md](CHANGELOG.md) và [ROADMAP.md](ROADMAP.md).

## Đóng góp và bảo mật

Hãy đọc [CONTRIBUTING.md](CONTRIBUTING.md) trước khi mở pull request. Báo cáo vấn đề bảo mật thông qua tính năng báo cáo lỗ hổng riêng tư của GitHub như được mô tả trong [SECURITY.md](SECURITY.md); không đăng các báo cáo nhạy cảm trong issue công khai.

## Giấy phép

Apache License 2.0. Xem [LICENSE](LICENSE) và [NOTICE](NOTICE).
