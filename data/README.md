# Dữ liệu local

SafeShift sử dụng **InspecSafe-V1**. Repository không chứa dataset hoặc script tải/parse dữ liệu ở bước khởi tạo này.

## Vị trí trên máy

Từ repository root, đặt bản dataset được phép sử dụng tại:

```text
data/
├── raw/
│   └── InspecSafe-V1/   # Nội dung dataset gốc trên máy local
├── manifests/          # Manifest nhỏ, dùng relative path
└── processed/          # Sản phẩm dẫn xuất local
```

`data/raw/InspecSafe-V1/` là quy ước vị trí local của dự án, không phải tuyên bố về cấu trúc phát hành của dataset. Giữ nguyên cây thư mục, tên file và nội dung của bản gốc bên trong vị trí này. Chưa giả định tên file annotation, schema hay split khi chưa kiểm tra dữ liệu thực tế.

## Chuẩn bị và truy vết

1. Xác minh nguồn phát hành chính thức và điều kiện sử dụng trước khi lấy dữ liệu. URL và license sẽ được ghi sau khi kiểm chứng, không dùng nguồn suy đoán.
2. Lưu/giải nén dataset dưới `data/raw/InspecSafe-V1/`; nếu giữ archive, lưu trong `data/raw/`. Không sửa dữ liệu gốc.
3. Ghi nguồn, ngày lấy, version/release, checksum và cây thư mục thực tế vào báo cáo audit W1 trong `notes/`.
4. Đặt dữ liệu được xử lý sau này trong `data/processed/` và ghi cách tạo lại. Manifest có thể lưu ở `data/manifests/` nếu nhỏ, được phép chia sẻ và chỉ chứa metadata cần thiết.

Trong code/cấu hình/manifest, sử dụng đường dẫn tương đối như `data/raw/InspecSafe-V1/...`, tính từ repository root. Không ghi đường dẫn tuyệt đối hoặc thông tin cá nhân của máy vào file được commit.

## Quy tắc Git

- Toàn bộ nội dung `data/raw/` và `data/processed/` bị ignore, ngoại trừ `.gitkeep` để giữ thư mục.
- Không commit dataset, archive, ảnh/video gốc, annotation dump lớn hoặc bản sao dataset ở thư mục khác; không dùng Git LFS cho dataset.
- `data/manifests/` có thể được version control, nhưng phải kiểm tra dung lượng, quyền chia sẻ và nội dung trước khi thêm vào Git; không nhúng dữ liệu ảnh.
- Raw model outputs sau này đặt trong thư mục local dưới `outputs/` (ví dụ `outputs/runs/<run-id>/`), kèm metadata tái lập và sample IDs.
- `.gitignore` là lớp bảo vệ ban đầu, không thay thế việc kiểm tra staged files trước khi commit.
