---
translation_of: README.md
source_revision: docs-v0.5.0-alpha.1
last_synced_version: 0.5.0-alpha.1
---

# Auto Route for Codex

**Ngôn ngữ:** [English](README.md) | [Português (Brasil)](README.pt-BR.md) | [简体中文](README.zh-CN.md) | [繁體中文](README.zh-TW.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Türkçe](README.tr.md) | [Русский](README.ru.md) | Tiếng Việt | [ไทย](README.th.md) | [Deutsch](README.de.md) | [Español](README.es.md)

> Dự án cộng đồng ở giai đoạn alpha. Không phải là sản phẩm chính thức của OpenAI.

Auto Route for Codex là một plugin Codex yêu cầu người dùng chủ động bật, có chức năng đề xuất vai trò mô hình, mức độ suy luận và cấu trúc thực thi đủ dùng dựa trên hồ sơ tác vụ được giới hạn để bảo vệ quyền riêng tư. Trên host Codex Desktop được hỗ trợ, plugin chỉ có thể tiếp tục một tác vụ nhạy cảm với `quality` hoặc `parallelism` trong fork sau khi vượt qua capability gate và evidence gate. Mọi môi trường khác hạ cấp an toàn thành đề xuất trong tác vụ hiện tại.

## Vì sao dự án này tồn tại

Lựa chọn mô hình và mức độ suy luận là hai quyết định riêng biệt. Một tác vụ ngắn nhưng rủi ro có thể cần mô hình mạnh hơn, trong khi một công việc dài, lặp lại và có thể kiểm chứng có thể phù hợp hơn với mô hình nhanh hơn. Plugin này làm rõ những đánh đổi đó mà không biến việc chọn mô hình thành một tác dụng phụ vô hình.

Hợp đồng công khai tuân theo sáu quy tắc:

- việc kích hoạt phải được thực hiện rõ ràng thông qua `$auto-route-for-codex`;
- chỉ các trường hồ sơ đã được liệt kê mới được chuyển đến bộ định tuyến xác định;
- current setting ưu tiên host-injected evidence; khi không có bằng chứng này, bounded fallback `read_current_setting.py` chỉ được xuất `current` và `current_provenance`, còn mọi kết quả `unknown` vẫn là recommendation-only;
- việc tiếp tục tác vụ yêu cầu Codex Desktop, mọi task tool cần thiết, current-setting và catalog evidence đã `verified`, cùng model và thinking được host hỗ trợ;
- routing yêu cầu `host_capabilities.source_task_context=true`, và mỗi lần chuyển độc lập yêu cầu một `CODEX_THREAD_ID` hợp lệ; `transfer_state.py` suy ra `source_binding_sha256` cục bộ và không bao giờ lưu bền hay xuất định danh nguồn thô;
- mỗi side effect trong `fork -> send -> readback -> navigate -> archive` cần một atomic reservation riêng, và chỉ được archive nguồn sau khi chuỗi đã xác nhận đến đúng một đích.

## Bắt đầu nhanh

Điều kiện tiên quyết:

- một giao diện Codex hỗ trợ plugin và gọi kỹ năng một cách rõ ràng;
- Codex CLI khả dụng trong `PATH`;
- quyền truy cập vào kho Git công khai.

```sh
codex plugin marketplace add jacob101519/auto-route-for-codex --ref v0.5.0-alpha.1
codex plugin add auto-route-for-codex@jacob101519
```

Bắt đầu một tác vụ Codex mới, chọn **Auto Route for Codex**, hoặc gọi:

```text
$auto-route-for-codex Review this task and use a sufficient Codex setting.
```

Plugin luôn trả về decision có phiên bản và ưu tiên host-injected current setting. Nếu không có observation đó nhưng có `CODEX_THREAD_ID` cùng một `CODEX_HOME` dùng được, `read_current_setting.py` chỉ được kiểm tra local session tương ứng trong `$CODEX_HOME/sessions` và xuất kết quả bounded `current + current_provenance` không chứa task text, path hoặc thread identifier. Reader failure trả về `unknown`. Trên host Codex Desktop đủ khả năng, mismatch `quality` hoặc `parallelism` đã xác minh có thể tiếp tục trong fork với `model` và `thinking` được đề xuất; mismatch `efficiency`, surface không được hỗ trợ, tool bị thiếu, cài đặt không được hỗ trợ hoặc evidence `unknown|stale|uncertain` vẫn là `stay` và recommendation-only.

Plugin không sửa native model picker, `config.toml`, mặc định lâu dài, sandbox, approval policy, network access hoặc credential.

Mỗi lần chuyển đều được ràng buộc với tác vụ nguồn: bằng chứng host lúc định tuyến phải khai báo `host_capabilities.source_task_context=true`, đồng thời lúc chạy phải có `CODEX_THREAD_ID` hợp lệ; cả hai đều bắt buộc. `transfer_state.py` suy ra `source_binding_sha256` cục bộ và không bao giờ lưu bền hay xuất định danh nguồn thô. Hash này được đưa vào khóa theo nguồn, biên nhận chuẩn, `authorization_binding`, từng reservation marker và mọi lần kiểm tra chuyển trạng thái, kể cả xác nhận archive. Vì vậy cùng một nguồn không thể bắt đầu lần chuyển thứ hai bằng `transfer_id` khác, còn nguồn khác không thể tiếp tục, xác nhận hay archive lần chuyển đó. Ngữ cảnh nguồn thiếu, không hợp lệ hoặc không khớp sẽ fail closed.

## Tiếp tục Desktop được bảo vệ bằng capability gate

Luồng đầy đủ chỉ khả dụng khi tất cả kiểm tra sau đạt yêu cầu:

1. surface hiện tại là Codex Desktop;
2. host cung cấp `fork_thread`, `send_message_to_thread`, `read_thread`, `navigate_to_codex_page` và `set_thread_archived` tương thích;
3. current-setting evidence là `verified` và còn hiệu lực, ưu tiên host injection và chỉ dùng bounded fallback khi cần; model-catalog evidence cũng là `verified` và còn hiệu lực;
4. live host hỗ trợ `model` và `thinking` được đề xuất;
5. trước mỗi lời gọi fork, send, readback, navigation hoặc archive, `transfer_state.py --reserve-event` tạo atomic marker `O_EXCL` trong durable default root `$CODEX_HOME/state/auto-route-for-codex`. `AUTO_ROUTE_STATE_HOME` chỉ là explicit override/test hook, và chỉ gọi host khi `side_effect_authorized=true` bằng winner-only `reservation_lease` do reservation trả về;
6. prompt delivery xác nhận các giá trị model và thinking override thực tế, destination readback chứng minh yêu cầu gốc đã bỏ từ gọi skill đến đúng fork, và navigation thành công trước khi cho phép archive.

lifecycle có thứ tự là:

```text
planned
  -> fork_created
  -> prompt_delivery_confirmed
  -> destination_readback_confirmed
  -> navigation_confirmed
  -> source_archive_confirmed
```

Successful reservation trả về winner-only `reservation_lease`. Sau host side effect, bước xác nhận dùng `--event` với cùng `--router-input` và truyền lease bằng `--reservation-lease`; `prompt_delivery_confirmed` còn yêu cầu `--observed-model` và `--observed-thinking`. Canonical receipt lưu bền `pending_reservation`, nên ngay cả khi marker bị thiếu, reserve lặp lại vẫn trả về `reconcile_required` và `side_effect_authorized=false`, không bao giờ cấp lại quyền cho side effect. Marker, receipt và state directory mới tạo đều được `fsync`. Root mặc định `$CODEX_HOME/state/auto-route-for-codex` đã durable; `AUTO_ROUTE_STATE_HOME` chỉ là explicit override/test hook, không bắt buộc để persistence. Reservation marker chỉ chứa hashes và bounded transfer metadata, không lưu raw task text và không bao giờ đi vào package hoặc repository.

`reservation_lease` là một ephemeral coordination nonce và bearer capability, không phải credential. Giá trị này chỉ được phát một lần cho thao tác thắng trong private local CLI stdout hoặc tool-execution detail tương đương, rồi được truyền lại bằng process argument `--reservation-lease`; giao diện tương thích trong tương lai có thể dùng stdin. Hãy giữ giá trị trong thao tác riêng tư đó. Không bao giờ sao chép nó vào task prompt, final hoặc user-facing prose khác, package hay repository, external telemetry, Issue hay support report, hoặc durable log. Ranh giới này giảm rò rỉ ngoài ý muốn nhưng không bảo vệ lease trước malicious same-user writer.

Evidence đã hết hạn hoặc stale không bao giờ cấp quyền cho reservation mới. Nếu reservation đã được ghi bền vững dưới dạng `pending_reservation` khi immutable binding còn hợp lệ, lease khớp chỉ có thể xác nhận chính thao tác đã bắt đầu đó hoặc đánh dấu nó là `uncertain` sau evidence TTL. Ngoại lệ này không thể cấp quyền cho host side effect khác. State mutation interface duy nhất được hỗ trợ là CLI `transfer_state.py`. Python import của phần triển khai và sửa trực tiếp state file là unsupported internals.

Timeout, mismatch, kết quả không đầy đủ hoặc side effect mơ hồ chuyển sang `uncertain`. Plugin không được gửi lại, tạo fork khác, chạy yêu cầu gốc ở nguồn hoặc archive nguồn. Khi biết destination identifier, plugin chỉ được đối chiếu đích đó. Nếu fork thực sự thành công nhưng host response bị mất trước khi bất kỳ destination identifier nào được trả về, durable replay protection vẫn chặn việc tạo lại fork, thực thi ở nguồn và archive nguồn, nhưng plugin không thể tự tìm ra đích chưa biết. Hãy giữ nguồn hiển thị và dùng host UI hoặc support channel để tìm hay khôi phục đích. Điều này ngăn duplicate execution, nhưng không chứng minh zero lost tasks. Receipt và reservation hashes cung cấp deterministic integrity chứ không phải signature; malicious local writer có thể thay thế local state nằm ngoài threat boundary.

## Ranh giới an toàn của phiên bản công khai

Bao gồm:

- lược đồ JSON nghiêm ngặt cho input, output và transfer receipt;
- deterministic routing, bounded current-setting fallback và reservation-backed transfer-state logic;
- source-task binding bảo vệ quyền riêng tư, ngăn việc tiếp tục từ nguồn khác và ngăn nhiều `transfer_id` cho cùng một nguồn;
- contract tiếp tục tác vụ Codex Desktop có capability gate;
- route, contract, semantic-negative, state-machine và failure-boundary tests;
- xác minh repository, privacy, translation và release;
- tài liệu tiếng Anh có thẩm quyền, bản dịch tiếng Trung giản thể đầy đủ và các README được bản địa hóa.

Chủ đích không bao gồm:

- unbounded session scanning, task-text extraction hoặc xuất session content và reservation marker;
- current-setting receipt riêng tư, private catalog hoặc local marketplace state;
- nhật ký thời gian chạy, thông tin xác thực, đường dẫn cục bộ, mã định danh tác vụ hoặc cấu hình riêng tư;
- hidden invocation, tự động transfer cho `efficiency`, thay đổi native model picker hoặc ghi vào global Codex configuration;
- tuyên bố rằng Codex CLI, IDE, cloud, API hoặc agent khác cung cấp Codex Desktop task tool.

Xem [Quyền riêng tư và luồng dữ liệu](docs/privacy-and-data-flow.md), [Chính sách định tuyến](docs/routing-policy.md) và [Khả năng tương thích](docs/compatibility.md).

## Sơ đồ kho mã nguồn

| Đường dẫn | Mục đích |
|---|---|
| `.codex-plugin/plugin.json` | Tệp kê khai plugin |
| `.agents/plugins/marketplace.json` | Mục nhập marketplace |
| `skills/auto-route-for-codex/` | Kỹ năng, lược đồ, bounded current-setting reader, bộ định tuyến, reservation-backed transfer reducer và bài kiểm thử |
| `docs/` | Tài liệu tiếng Anh có thẩm quyền |
| `docs/i18n/zh-CN/` | Bản dịch tiếng Trung giản thể đầy đủ |
| `scripts/verify_public_repo.py` | Kiểm tra kho mã nguồn, bản dịch, quyền riêng tư và liên kết |
| `scripts/build_release.py` | Trình tạo ZIP plugin và `SHA256SUMS` có tính xác định |

## Xác minh từ một bản sao sạch

```sh
python3 -m pip install --disable-pip-version-check PyYAML==6.0.3 jsonschema==4.26.0
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

`v0.5.0-alpha.1` là alpha công khai đầu tiên có capability-gated Codex Desktop task continuation. API và bố cục gói có thể thay đổi trước khi phát hành phiên bản ổn định. Xem [CHANGELOG.md](CHANGELOG.md) và [ROADMAP.md](ROADMAP.md).

## Đóng góp và bảo mật

Hãy đọc [CONTRIBUTING.md](CONTRIBUTING.md) trước khi mở pull request. Báo cáo vấn đề bảo mật thông qua tính năng báo cáo lỗ hổng riêng tư của GitHub như được mô tả trong [SECURITY.md](SECURITY.md); không đăng các báo cáo nhạy cảm trong issue công khai.

## Giấy phép

Apache License 2.0. Xem [LICENSE](LICENSE) và [NOTICE](NOTICE).
