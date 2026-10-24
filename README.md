# SafeShift

SafeShift là dự án nghiên cứu đánh giá mô hình thị giác–ngôn ngữ trong bối cảnh
an toàn công nghiệp. Repository đang chuẩn bị cho giai đoạn nghiên cứu mới.

Main tối giản là nền tảng phát triển tiếp theo, **không phải release tương đương
các thực nghiệm cũ**. Hướng nghiên cứu và protocol mới cần được phê duyệt riêng;
việc dọn repository không cấp quyền thực nghiệm.

Toàn bộ 693 file đã được Git theo dõi trước reset được giữ tại nhánh
[`legacy/pre-reset-20261024`](https://github.com/tantdna2/SafeShift/tree/legacy/pre-reset-20261024)
và annotated tag
[`safeshift-pre-reset-20261024`](https://github.com/tantdna2/SafeShift/tree/safeshift-pre-reset-20261024).
Xem [lịch sử và cách tra cứu](docs/HISTORY.md) cùng [quy tắc làm việc](AGENTS.md).

Kiểm tra cấu trúc mới bằng Python, chỉ cần thư viện chuẩn:

```console
python -B -m unittest discover -s tests -v
```
