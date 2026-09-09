# InspecSafe-V1 Dataset Schema & Structure Survey

Tài liệu này ghi nhận kết quả khảo sát thực tế trên toàn bộ dữ liệu gốc InspecSafe-V1 tại `data/raw/InspecSafe-V1/` trong khuôn khổ Week 1 (Dataset Audit) của dự án SafeShift. Mọi số liệu và cấu trúc dưới đây được kiểm chứng trực tiếp bằng mã nguồn kiểm kê trên 100% tệp dữ liệu, không sử dụng giả định hoặc suy đoán.

---

## 1. Cây thư mục thực tế

Dữ liệu cục bộ được giải nén từ các tệp nén gốc (`train.tar.gz` ~17.8 GB, `test.tar.gz` ~5.7 GB). Do cấu trúc đường dẫn bên trong archive nén chứa thư mục gốc `DATA_PATH`, cây thư mục thực tế trên đĩa có dạng lồng như sau:

```text
data/raw/InspecSafe-V1/
├── README.md                          # Tài liệu giới thiệu dataset từ tác giả
├── dataset_loader.py                  # Script PyTorch dataset loader của tác giả
├── model_api_generate_results.py      # Script gọi API VLM benchmark của tác giả
├── model_benchmark_evaluation.py      # Script đánh giá độ tương đồng text qua embedding
├── model_confusion_matrix.py          # Script vẽ ma trận nhầm lẫn phân loại an toàn
├── train.tar.gz                       # Archive nén gốc tập train
├── test.tar.gz                        # Archive nén gốc tập test
├── train/
│   └── DATA_PATH/
│       └── train/
│           ├── Annotations/
│           │   ├── Normal_data/       # 1,675 thư mục điểm kiểm tra (3,014 mẫu)
│           │   │   ├── coal_conveyor-Level04-SuspendedRail-000560/
│           │   │   │   ├── coal_conveyor-Level04-SuspendedRail-000560-001.jpg
│           │   │   │   ├── coal_conveyor-Level04-SuspendedRail-000560-001.json
│           │   │   │   └── coal_conveyor-Level04-SuspendedRail-000560-001.txt
│           │   │   └── ...
│           │   └── Anomaly_data/      # 749 thư mục điểm kiểm tra (749 mẫu)
│           │       ├── coal_conveyor-Level01-SuspendedRail-002486/
│           │       │   ├── coal_conveyor-Level01-SuspendedRail-002486-001.jpg
│           │       │   ├── coal_conveyor-Level01-SuspendedRail-002486-001.json
│           │       │   └── coal_conveyor-Level01-SuspendedRail-002486-001.txt
│           │       └── ...
│           ├── Other_modalities/      # 1,674 thư mục điểm đa phương thức (chỉ có cho Normal_data)
│           │   ├── coal_conveyor-Level04-SuspendedRail-000560/
│           │   │   ├── coal_conveyor-Level04-SuspendedRail-000560-visible.mp4
│           │   │   ├── coal_conveyor-Level04-SuspendedRail-000560-infrared.mp4
│           │   │   ├── coal_conveyor-Level04-SuspendedRail-000560-sensor.txt
│           │   │   └── coal_conveyor-Level04-SuspendedRail-000560-audio.wav
│           │   └── ...
│           └── Parameters/            # 4 tệp JSON tham số cảm biến phần cứng
│               ├── Depth_Camera_params.json
│               ├── IR_Camera_params.json
│               ├── LiDAR_params.json
│               └── RGB_Camera_params.json
└── test/
    └── DATA_PATH/
        └── test/
            ├── Annotations/
            │   ├── Normal_data/       # 559 thư mục điểm kiểm tra (999 mẫu)
            │   └── Anomaly_data/      # 251 thư mục điểm kiểm tra (251 mẫu)
            ├── Other_modalities/      # 559 thư mục điểm đa phương thức (chỉ có cho Normal_data)
            └── Parameters/            # 4 tệp JSON tham số cảm biến phần cứng
```

### Thống kê định lượng tổng thể

| Tập dữ liệu (Split) | Phân loại | Số thư mục điểm (Waypoints) | Số ảnh (`.jpg`) | Số JSON (`.json`) | Số TXT (`.txt`) | Tổng số mẫu (Triplets) |
|---|---|---|---|---|---|---|
| **Train** | `Normal_data` | 1,675 | 3,014 | 3,014 | 3,014 | 3,014 |
| **Train** | `Anomaly_data` | 749 | 749 | 749 | 749 | 749 |
| **Train Tổng** | | **2,424** | **3,763** | **3,763** | **3,763** | **3,763** |
| **Test** | `Normal_data` | 559 | 999 | 999 | 999 | 999 |
| **Test** | `Anomaly_data` | 251 | 251 | 251 | 251 | 251 |
| **Test Tổng** | | **810** | **1,250** | **1,250** | **1,250** | **1,250** |
| **Toàn bộ Dataset** | | **3,234** | **5,013** | **5,013** | **5,013** | **5,013** |

*Ghi chú kiểm tra tính toàn vẹn:* 100% mẫu (5,013 / 5,013) đều tạo thành bộ 3 tệp hoàn chỉnh (`.jpg`, `.json`, `.txt`) có stem tên tệp trùng khớp tuyệt đối. Không có tệp mồ côi hoặc phần mở rộng lạ trong thư mục `Annotations`.

---

## 2. Mô tả một sample thật

Một mẫu (sample/instance) trong tập dữ liệu thị giác được xác định bởi một bộ ba (triplet) tệp nằm trong thư mục điểm tuần tra tương ứng:
1. **Tệp ảnh (`.jpg`):** Ảnh quang học vùng khả kiến (visible-light RGB frame).
2. **Tệp annotation (`.json`):** Tệp cấu trúc JSON (định dạng AnyLabeling / LabelMe) chứa danh sách các đa giác phân vùng (`polygon`), nhãn đối tượng và chuỗi nhúng base64 của ảnh.
3. **Tệp mô tả ngữ nghĩa (`.txt`):** Một đoạn văn bản tiếng Anh một dòng mô tả các thực thể quan sát được trong cảnh và kết luận mức độ an toàn.

### Số lượng mẫu trên mỗi điểm tuần tra (Waypoint)
- Trong `Anomaly_data`: Mỗi thư mục điểm tuần tra chứa **duy nhất 1 mẫu** (`-001`).
- Trong `Normal_data`: Một điểm tuần tra có thể chứa từ 1 đến 4 mẫu ảnh chụp liên tiếp:
  - Phân bố tập Train (1,675 điểm): 1 mẫu (645 điểm), 2 mẫu (836 điểm), 3 mẫu (79 điểm), 4 mẫu (115 điểm).
  - Phân bố tập Test (559 điểm): 1 mẫu (216 điểm), 2 mẫu (282 điểm), 3 mẫu (25 điểm), 4 mẫu (36 điểm).

---

## 3. Quy tắc đặt tên (Naming Pattern)

### 3.1. Tên thư mục điểm tuần tra (Point Directory)
Tất cả 3,234 thư mục điểm kiểm tra trong dataset tuân thủ 100% biểu thức chính quy (0 ngoại lệ):
```regex
^([a-zA-Z0-9_]+)-Level([0-9]{2})-([a-zA-Z0-9_]+)-([0-9]{6})$
```
Cú pháp: `{domain}-Level{safety_level:02d}-{platform}-{point_id:06d}`

Ví dụ:
- `coal_conveyor-Level04-SuspendedRail-000560`
- `oil_chemical-Level01-Wheeled-002669`
- `power-Level02-SuspendedRail-002980`
- `tunnel-Level03-SuspendedRail-003215`

### 3.2. Tên tệp trong thư mục điểm (Sample Files)
Tất cả 15,039 tệp (`.jpg`, `.json`, `.txt`) tuân thủ 100% quy tắc đặt tên:
```regex
^([a-zA-Z0-9_]+-Level[0-9]{2}-[a-zA-Z0-9_]+-[0-9]{6})-([0-9]{3})\.(jpg|json|txt)$
```
Cú pháp: `{point_directory}-{instance_id:03d}.{ext}`

Ví dụ:
- `coal_conveyor-Level04-SuspendedRail-000560-001.jpg`
- `coal_conveyor-Level04-SuspendedRail-000560-001.json`
- `coal_conveyor-Level04-SuspendedRail-000560-001.txt`

### 3.3. Phân chia Train/Test theo Point ID
- Point ID là chuỗi 6 chữ số từ `000001` đến `003234`.
- **Độ trùng lặp Point ID giữa Train và Test: 0** (phân vùng rời nhau hoàn toàn theo điểm tuần tra).
- Dải Point ID trong Test: `1` đến `2485` (810 điểm).
- Dải Point ID trong Train: `560` đến `3234` (2,424 điểm).
- *Lưu ý:* Các ID xen kẽ nhau trong dải tổng quát nhưng không bị trùng giữa hai tập.

---

## 4. Định dạng và đặc điểm ảnh

- **Phần mở rộng hiển thị:** 100% tệp ảnh đều có phần mở rộng `.jpg` (5,013 tệp).
- **Định dạng nhị phân thực tế (Magic bytes):**
  - **4,969 tệp** là chuẩn JPEG thực sự (bắt đầu bằng `FF D8 FF`).
  - **44 tệp là ảnh PNG bị đặt sai đuôi `.jpg`** (bắt đầu bằng signature chuẩn PNG: `89 50 4E 47 0D 0A 1A 0A`).
  - Toàn bộ 44 tệp PNG này đều nằm trong `Anomaly_data` (39 tệp ở Train, 5 tệp ở Test).
- **Độ phân giải thực tế:**
  - `2560 x 1440` (2K QHD): 2,576 ảnh (51.39%)
  - `1920 x 1080` (Full HD): 2,124 ảnh (42.37%)
  - `1280 x 720` (HD): 122 ảnh (2.43%)
  - Các biến thể khác (960x540, 2688x1520, 720x405, 1944x1200, ...): 191 ảnh (3.81%).
- **Kiểm tra khớp kích thước:** 100% (5,013 / 5,013) ảnh có kích thước đọc từ binary header trùng khớp hoàn toàn với hai trường `imageWidth` và `imageHeight` được ghi trong tệp `.json`.

---

## 5. Schema JSON thực tế

Tất cả 5,013 tệp JSON đều tuân thủ cấu trúc xuất chuẩn của công cụ gán nhãn AnyLabeling / LabelMe. Không chứa các metadata như `robot_id`, `timestamp`, `location`, `safety_label` ở top-level.

### 5.1. Các trường cấp cao nhất (Top-level Fields)
Tất cả 5,013 tệp JSON có đúng 7 trường top-level giống hệt nhau:
```json
{
  "version": "0.4.15",
  "flags": {},
  "shapes": [ ... ],
  "imagePath": "coal_conveyor-Level04-SuspendedRail-000560-001.jpg",
  "imageData": "/9j/4AAQSkZJRgABAQAAAQABAAD...",
  "imageHeight": 1440,
  "imageWidth": 2560
}
```

Chi tiết từng trường:
- `version` (`string`): Phiên bản của AnyLabeling (ví dụ `"0.4.15"`).
- `flags` (`object`): Từ điển rỗng `{}` trên 100% mẫu.
- `shapes` (`array`): Mảng các đối tượng hình học phân vùng.
- `imagePath` (`string`): Tên tệp ảnh tương đối (chỉ chứa tên file, ví dụ `"sample-001.jpg"`).
- `imageData` (`string`): **Chuỗi Base64 mã hóa toàn bộ dữ liệu nhị phân của ảnh** (độ dài trung bình ~1.28 triệu ký tự). Do đó kích thước mỗi tệp JSON thường từ 1.2 MB đến 2.5 MB.
- `imageHeight` (`integer`): Chiều cao ảnh tính bằng pixel.
- `imageWidth` (`integer`): Chiều rộng ảnh tính bằng pixel.

### 5.2. Cấu trúc trường `shapes`
Có tổng cộng **37,434 shapes** trên toàn bộ 5,013 mẫu. Mỗi phần tử shape có đúng 10 trường:
```json
{
  "label": "Pipeline",
  "points": [
    [1045.2, 345.6],
    [1080.1, 350.2],
    [1075.0, 520.4],
    [1040.8, 515.1]
  ],
  "group_id": null,
  "description": "",
  "difficult": false,
  "shape_type": "polygon",
  "flags": {},
  "attributes": {},
  "score": null,
  "kie_linking": []
}
```

Kiểm tra phân bố giá trị trên toàn bộ 37,434 shapes:
- `shape_type`: **100% là `"polygon"`** (37,434 / 37,434). Không có shape_type `"rectangle"`, `"circle"`, `"line"`, v.v.
- `points`: Danh sách các cặp tọa độ float `[x, y]` pixel tạo thành đa giác khép kín.
- `label`: Chuỗi tên danh mục đối tượng. Có **231 nhãn duy nhất**.
  - 230 nhãn bằng tiếng Anh (ví dụ: `Pipeline`, `Traffic Cone`, `Stent`, `Idler Roller`, `Bolt`, `Person`, `Belt`, `Open Flame`, `Cigarette`, `Mobile Phone`, `Safety Helmet`, v.v.).
  - 1 nhãn tiếng Trung: `"出口"` (Exit) xuất hiện đúng 1 lần tại mẫu `tunnel-Level01-SuspendedRail-003064-001`.
- `group_id`: `null` trên 100% shapes.
- `description`: `""` (chuỗi rỗng) trên 100% shapes.
- `difficult`: `false` trên 100% shapes.
- `flags`: `{}` (từ điển rỗng) trên 100% shapes.
- `attributes`: `{}` (từ điển rỗng) trên 100% shapes.
- `score`: `null` trên 100% shapes.
- `kie_linking`: `[]` (mảng rỗng) trên 100% shapes.

---

## 6. Format TXT thực tế

100% (5,013 / 5,013) tệp `.txt` đều là **văn bản tiếng Anh gồm duy nhất 1 dòng**.
Không có tệp nào bị rỗng. Không có tệp nào chứa tiếng Trung. Không chứa các tag markdown định dạng như `[Image Description]` hay `[Safety Level]`.

### 6.1. Cấu trúc cho `Normal_data` (4,013 mẫu)
Mô tả các thực thể thiết bị/môi trường bình thường trong ảnh và kết thúc bằng cụm từ khẳng định an toàn:
> *Template:* `In the <domain/setting> scene, <list of detected objects> are present / running smoothly / properly positioned, no abnormalities observed.`

Ví dụ:
- `coal_conveyor-Level04-SuspendedRail-000560-001.txt`:
  > `"In the coal conveyor bridge scene, the idler roller, lamp, railing, and stent are all present and properly positioned, no abnormalities observed."`
- `power-Level04-Wheeled-001701-001.txt`:
  > `"In the power facility scene, the distribution cabinet displays steady indicator lights and properly functioning instrumentation, no abnormalities observed."`

### 6.2. Cấu trúc cho `Anomaly_data` (1,000 mẫu)
Mô tả các yếu tố nguy cơ/vi phạm quy định an toàn và kết thúc bằng việc xếp cấp mức độ an toàn:
> *Template:* `In the <domain/setting> scenario, <description of hazards/violations>. Therefore, the safety level is <Grade/Level>.`

Ví dụ:
- `coal_conveyor-Level01-SuspendedRail-002486-001.txt`:
  > `"In the coal conveying trestle scenario, the potential hazards in the image are personnel smoking and not wearing gloves. Therefore, the safety level is classified as Level One."`
- `tunnel-Level01-SuspendedRail-003035-001.txt`:
  > `"In the tunnel scenario, there is an open flame. Therefore, the safety level is grade one."`
- `power-Level02-SuspendedRail-002980-001.txt`:
  > `"In the power scenario, the cabinet door is abnormally open. Therefore, the safety level is Grade Two."`

### 6.3. Các biến thể cú pháp ghi cấp độ an toàn ở cuối câu TXT
Cụm từ chỉ cấp độ an toàn trong tệp TXT không được chuẩn hóa thành một token cố định mà có nhiều biến thể từ vựng:
- **Cấp 1:** `Level One`, `level one`, `Grade One`, `grade one`, `Grade 1`, `one`, `classified as Level One`, `rated as Level One`.
- **Cấp 2:** `Grade Two`, `grade two`, `Grade 2`, `Level 2`, `Level Two`, `Grade II`, `rated as Level 2`.
- **Cấp 3:** `grade three`, `Grade 3`, `Grade Three`.
- **Cấp 4:** `no abnormalities observed`.

---

## 7. Khảo sát 5–10 mẫu đại diện theo từng Industrial Domain

### 7.1. Domain `coal_conveyor` (Băng tải than)
- **Train Normal:** `coal_conveyor-Level04-SuspendedRail-000560-001`
  - TXT: *"In the coal conveyor bridge scene, the idler roller, lamp, railing, and stent are all present and properly positioned, no abnormalities observed."*
  - Shapes (7): `Idler Roller`, `Idler Roller`, `Lamp`, `Railing`, `Stent`, `Stent`, `Stent`.
- **Train Anomaly (Level 1):** `coal_conveyor-Level01-SuspendedRail-002486-001`
  - TXT: *"In the coal conveying trestle scenario, the potential hazards in the image are personnel smoking and not wearing gloves. Therefore, the safety level is classified as Level One."*
  - Shapes (14): `Safety Helmet`, `Mobile Phone`, `Cigarette`, `Guardrail`, `Electrical Box` (x4), `Hook`, `Motor`, `Radiator` (x3), `Person`.
- **Train Anomaly (Level 2):** `coal_conveyor-Level02-SuspendedRail-002620-001`
  - TXT: *"In the coal conveyor bridge scenario, personnel are using mobile phones and not wearing gloves. The safety level is Grade 2."*
  - Shapes (8): `Mobile Phone`, `Safety Helmet`, `Guardrail`, `Belt`, `Idler Roller` (x3), `Person`.
- **Test Normal:** `coal_conveyor-Level04-SuspendedRail-000001-001`
  - TXT: *"In the coal conveyor bridge scene, the idler roller, lamp, railing, and stent are all present and properly positioned, no abnormalities observed."*
  - Shapes (4): `Idler Roller`, `Lamp`, `Railing`, `Stent`.
- **Test Anomaly (Level 1):** `coal_conveyor-Level01-SuspendedRail-002235-001`
  - TXT: *"In the coal conveyor bridge scenario, the potential hazards in the image include smoking, not wearing a safety helmet, and not wearing gloves. Therefore, the safety level is Grade One."*
  - Shapes (16): `Cigarette`, `Stent` (x4), `Pipeline` (x2), `Protective Net` (x2), `Belt` (x2), `Idler Roller` (x2), `Window` (x2), `Person`.

### 7.2. Domain `metallurgy` (Luyện kim / Thiêu kết)
- **Train Normal:** `metallurgy-Level04-SuspendedRail-000645-001`
  - TXT: *"In the sintering equipment area scene, the pipeline, stent, and fire extinguisher are all properly installed and positioned, with no abnormalities observed."*
  - Shapes (9): `Pipeline`, `Stent` (x5), `Fire Extinguisher` (x3).
- **Train Normal:** `metallurgy-Level04-SuspendedRail-000646-001`
  - TXT: *"In the sintering equipment area scene, the pipeline, valve, and stent are all securely in place, no abnormalities observed."*
  - Shapes (10): `Valve` (x2), `Pipeline` (x4), `Stent` (x4).
- **Train Anomaly (Level 3 - Mẫu dị thường luyện kim thực sự duy nhất):** `metallurgy-Level03-SuspendedRail-002666-001`
  - TXT: *"In the metallurgical scene, there is water accumulation on the ground. The safety level is grade three."*
  - Shapes (10): `Sight Hole Cover`, `Person`, `Bellows`, `Pipeline` (x3), `Liquid`, `Bottle`, `Safety Helmet`, `Mobile Phone`.
- **Train Anomaly (Level 1 - Ví dụ trong 8 mẫu mismatch sang oil_chemical):** `metallurgy-Level01-SuspendedRail-002658-001`
  - TXT: *"In the oil and gas chemical environment, there is an open flame. Therefore, the safety level is Grade One."* *(Lưu ý: mismatch tên miền; 8 trong số 9 mẫu anomaly gán nhãn metallurgy thực chất mô tả môi trường dầu khí hóa chất)*
  - Shapes (6): `Open Flame`, `Stairs`, `Stent` (x4).
- **Test Normal:** `metallurgy-Level04-SuspendedRail-000030-001`
  - TXT: *"In the sintering equipment area scene, the pipeline, stent, and stairs are all securely in place, no abnormalities observed."*
  - Shapes (8): `Stairs`, `Pipeline` (x3), `Stent` (x4).

### 7.3. Domain `oil_chemical` (Dầu khí / Hóa chất)
- **Train Normal:** `oil_chemical-Level04-SuspendedRail-000958-001`
  - TXT: *"In the oil, gas, and chemical plant scene, the pipeline runs adjacent to a set of stairs supported by a stent, no abnormalities observed."*
  - Shapes (7): `Pipeline`, `Stairs`, `Stent` (x5).
- **Train Anomaly (Level 1):** `oil_chemical-Level01-Wheeled-002668-001`
  - TXT: *"In the oil and gas chemical scene, the potential hazards in the image include smoking, not wearing a safety helmet, and not wearing gloves. Therefore, the safety level is Grade One."*
  - Shapes (9): `Cigarette`, `Pipeline` (x3), `Industrial Tower`, `Stent` (x3), `Person`.
- **Train Anomaly (Level 2):** `oil_chemical-Level02-Wheeled-002875-001`
  - TXT: *"In the oil and gas chemical scenario, there is liquid accumulation on the ground. The safety level is Grade II."*
  - Shapes (5): `Liquid`, `Pipeline` (x2), `Industrial Tower`, `Stent`.
- **Test Normal:** `oil_chemical-Level04-SuspendedRail-000100-001`
  - TXT: *"In the oil, gas, and chemical plant scene, the valve and flange connections are intact, no abnormalities observed."*
  - Shapes (5): `Valve`, `Flange` (x2), `Pipeline` (x2).
- **Test Anomaly (Level 1):** `oil_chemical-Level01-Wheeled-002270-001`
  - TXT: *"In the oil and gas chemical scenario, there is smoke and an open flame, and personnel are not wearing safety helmets. The safety level is Grade One."*
  - Shapes (10): `Open Flame`, `Smoke`, `Pipeline` (x4), `Stent` (x3), `Person`.

### 7.4. Domain `power` (Điện lực)
- **Train Normal:** `power-Level04-Wheeled-001701-001`
  - TXT: *"In the power facility scene, the distribution cabinet displays steady indicator lights and properly functioning instrumentation, no abnormalities observed."*
  - Shapes (7): `Distribution Cabinet`, `Instrumentation` (x2), `Indicator Light` (x4).
- **Train Anomaly (Level 1):** `power-Level01-SuspendedRail-002954-001`
  - TXT: *"In the power scenario, there is a person on the ground. Therefore, the safety level is one."*
  - Shapes (6): `Person`, `Stent` (x2), `Fire Cabinet`, `Window` (x2).
- **Train Anomaly (Level 2):** `power-Level02-SuspendedRail-002980-001`
  - TXT: *"In the power scenario, the cabinet door is abnormally open. Therefore, the safety level is Grade Two."*
  - Shapes (6): `Power Distribution Cabinet`, `Cabinet Door Open`, `Instrumentation` (x2), `Indicator Light` (x2).
- **Train Anomaly (Level 3):** `power-Level03-SuspendedRail-003010-001`
  - TXT: *"In the power scenario, personnel are not wearing masks. The safety level is grade three."*
  - Shapes (5): `Person`, `Safety Helmet`, `Power Distribution Cabinet`, `Window` (x2).
- **Test Normal:** `power-Level04-Wheeled-000450-001`
  - TXT: *"In the power facility scene, the distribution cabinet displays steady indicator lights and properly functioning instrumentation, no abnormalities observed."*
  - Shapes (8): `Distribution Cabinet`, `Instrumentation` (x3), `Indicator Light` (x4).

### 7.5. Domain `tunnel` (Đường hầm)
- **Train Normal:** `tunnel-Level04-SuspendedRail-001997-001`
  - TXT: *"In the tunnel scene, the distribution box and fire hydrant cabinet appear normal, no abnormalities observed."*
  - Shapes (2): `Distribution Box`, `Fire Hydrant Cabinet`.
- **Train Anomaly (Level 1):** `tunnel-Level01-SuspendedRail-003035-001`
  - TXT: *"In the tunnel scenario, there is an open flame. Therefore, the safety level is grade one."*
  - Shapes (8): `Open Flame`, `Fire Extinguisher`, `Railway Track`, `Stairs`, `Pipeline` (x2), `Person` (x2).
- **Train Anomaly (Level 2):** `tunnel-Level02-SuspendedRail-003180-001`
  - TXT: *"In the tunnel scenario, there is a foreign object. The safety level is Grade Two."*
  - Shapes (6): `Plastic Bag`, `Railway Track`, `Pipeline` (x2), `Stairs`, `Person`.
- **Test Normal:** `tunnel-Level04-SuspendedRail-000481-001`
  - TXT: *"In the tunnel scene, the distribution box, fire alarm system, and fire hydrant cabinet are all in normal working condition, no abnormalities observed."*
  - Shapes (4): `Distribution Box`, `Fire Alarm System`, `Fire Hydrant Cabinet` (x2).
- **Test Anomaly (Level 1):** `tunnel-Level01-SuspendedRail-002400-001`
  - TXT: *"In the tunnel scenario, there is an open flame and smoke. Therefore, the safety level is Grade One."*
  - Shapes (7): `Open Flame`, `Smoke`, `Railway Track`, `Pipeline` (x2), `Person` (x2).

---

## 8. Khả năng parse metadata từ tên tệp và đường dẫn

Bảng đối chiếu giữa các thông tin quan trọng và nguồn trích xuất:

| Thuộc tính (Attribute) | Có trong tệp JSON gốc không? | Có parse được từ tên/đường dẫn không? | Cách trích xuất khả thi |
|---|---|---|---|
| **Split** (`train` / `test`) | Không | **Có** | Thư mục cha: `.../{split}/DATA_PATH/...` |
| **Data Type** (`Normal_data` / `Anomaly_data`) | Không | **Có** | Thư mục con: `Annotations/{data_type}/...` |
| **Domain** (`coal_conveyor`, `power`, ...) | Không | **Có** | Token thứ 1 của thư mục điểm: `{domain}-Level...` |
| **Safety Level** (`Level01` .. `Level04`) | Không | **Có** | Token thứ 2 của thư mục điểm: `...-Level{lvl}-...` |
| **Robot Platform** (`SuspendedRail` / `Wheeled`) | Không | **Có** | Token thứ 3 của thư mục điểm: `...-{platform}-...` |
| **Point ID** (Waypoint ID) | Không | **Có** | Token thứ 4 của thư mục điểm: 6 chữ số (`000560`) |
| **Instance ID** (Frame ID) | Không (chỉ có trong `imagePath`) | **Có** | Hậu tố 3 chữ số của tên tệp: `-001` |
| **Sample ID duy nhất** | Không | **Có** | Stem của tệp: `{point_folder}-{instance_id}` |
| **Image Resolution** | Có (`imageWidth`, `imageHeight`) | Không | Đọc từ top-level của tệp JSON |
| **Polygons / Object Masks** | Có (`shapes[].points`) | Không | Đọc từ danh sách `shapes` trong JSON |
| **Text Description** | Không | Không | Đọc từ tệp `.txt` đi kèm |

### Nhận định phân loại: Field gốc vs Field suy luận
- **Field gốc thực sự (Native fields):**
  - Trong ảnh: Dữ liệu pixel nhị phân, kích thước resolution.
  - Trong JSON: `shapes` (tọa độ đa giác `points`, tên đối tượng `label`, loại `shape_type`), `imageWidth`, `imageHeight`, `imageData`.
  - Trong TXT: Toàn văn câu mô tả ngữ nghĩa tiếng Anh.
  - Trong thư mục `Parameters/`: Thông số phần cứng cảm biến (FOV, độ phân giải, bước sóng laser, sai số khoảng cách).
- **Field suy luận từ quy ước thư mục và đặt tên (Inferred metadata):**
  - `split`, `domain`, `safety_level`, `robot_platform`, `point_id`, `instance_id`.
  - Không có bất kỳ header hay trường metadata cấu trúc nào trong JSON chứa trực tiếp các giá trị này. Mọi parser tự động bắt buộc phải bóc tách từ đường dẫn tương đối và tên tệp.

---

## 9. Các trường đề xuất để xây dựng Data Manifest

Khi xây dựng manifest chuẩn cho SafeShift (ví dụ dạng JSON Lines hoặc CSV nhỏ gọn, độc lập với máy cá nhân), các trường sau đây có thể tạo ra một cách nhất quán và có thể truy vết:

1. `sample_id` (`string`): Định danh mẫu duy nhất, ví dụ `"coal_conveyor-Level04-SuspendedRail-000560-001"`.
2. `point_id` (`string`): Định danh điểm kiểm tra (6 chữ số), ví dụ `"000560"`.
3. `instance_id` (`string`): Định danh số thứ tự mẫu tại điểm (3 chữ số), ví dụ `"001"`.
4. `split` (`string`): Tập dữ liệu chính thức (`"train"` hoặc `"test"`).
5. `data_type` (`string`): Phân loại nhãn nhị phân của tập dữ liệu (`"Normal_data"` hoặc `"Anomaly_data"`).
6. `domain` (`string`): Ngành công nghiệp (`"coal_conveyor"`, `"metallurgy"`, `"oil_chemical"`, `"power"`, `"tunnel"`).
7. `safety_level` (`string`): Cấp độ an toàn 4 mức (`"Level01"`, `"Level02"`, `"Level03"`, `"Level04"`).
8. `safety_level_int` (`integer`): Mã số nguyên tương ứng (1: High Risk, 2: Moderate Risk, 3: Minor Hazard, 4: Normal).
9. `robot_platform` (`string`): Loại robot di chuyển (`"SuspendedRail"` hoặc `"Wheeled"`).
10. `image_relpath` (`string`): Đường dẫn tương đối tính từ repository root, ví dụ `"data/raw/InspecSafe-V1/train/DATA_PATH/train/Annotations/Normal_data/.../....jpg"`.
11. `json_relpath` (`string`): Đường dẫn tương đối tới tệp JSON tương ứng.
12. `txt_relpath` (`string`): Đường dẫn tương đối tới tệp TXT tương ứng.
13. `image_width` (`integer`) & `image_height` (`integer`): Độ phân giải ảnh.
14. `image_format` (`string`): Định dạng nhị phân thực tế (`"JPEG"` hoặc `"PNG"`).
15. `num_shapes` (`integer`): Số lượng đối tượng đa giác trong mẫu.
16. `has_other_modalities` (`boolean`): Cờ đánh dấu điểm này có dữ liệu trong `Other_modalities` hay không.

---

## 10. Giả định khi viết Parser (Parsing Assumptions)

Trước khi viết bất kỳ code parser nào, các giả định sau cần được ghi nhận rõ ràng:
1. **Đường dẫn lồng:** Do việc giải nén archive tạo ra thư mục lồng `data/raw/InspecSafe-V1/{split}/DATA_PATH/{split}/...`, parser phải duyệt từ `DATA_PATH/{split}/Annotations` thay vì giả định ngay dưới `{split}/Annotations`.
2. **Quy tắc bộ ba (Triplet) và yêu cầu kiểm tra tính toàn vẹn:**
   - *Hiện trạng dữ liệu thực tế:* Kiểm kê xác nhận 100% mẫu (5,013 / 5,013) hiện có đầy đủ bộ ba tệp (`.jpg`, `.json`, `.txt`) với stem tên trùng khớp.
   - *Yêu cầu bắt buộc đối với Parser:* Parser **không được chủ quan giả định mọi sample luôn đầy đủ mà bỏ qua việc kiểm tra tệp thiếu**. Parser phải được thiết kế theo nguyên tắc lập trình phòng thủ (defensive programming): bắt buộc kiểm tra sự tồn tại và tính hợp lệ của cả 3 tệp (`.jpg`, `.json`, `.txt`) cho từng mẫu; nếu phát hiện mẫu thiếu tệp hoặc stem không khớp, parser phải ghi log cảnh báo rõ ràng (log error) hoặc báo lỗi có kiểm soát (fail-fast), tuyệt đối không âm thầm bỏ qua lỗi.
3. **Thư viện đọc ảnh:** Parser **không được giả định toàn bộ `.jpg` là JPEG thuần túy**, vì có 44 tệp thực chất là định dạng PNG. Phải dùng thư viện tự nhận diện magic bytes (như PIL / OpenCV) hoặc xử lý ngoại lệ khi dùng các bộ giải mã JPEG chuyên dụng.
4. **Trích xuất nhãn an toàn:** Nhãn an toàn chuẩn xác nhất nên lấy từ token `LevelXX` trên tên thư mục điểm (hoặc nhị phân từ `Normal_data`/`Anomaly_data`), **không nên parse regex từ tệp TXT** do các biến thể ngữ nghĩa phức tạp ("grade one", "Grade 1", "classified as Level One", v.v.).
5. **Dung lượng tệp JSON:** Không nên cache toàn bộ nội dung tệp JSON vào bộ nhớ nếu chỉ cần metadata, vì trường `imageData` chứa chuỗi Base64 rất nặng (~1.3MB/file, tổng cộng hơn 6.5GB nếu load hết 5,013 file). Parser chỉ nên bóc tách `shapes`, `imageWidth`, `imageHeight` và bỏ qua `imageData`.

---

## 11. Các bất thường và ngoại lệ phát hiện được (Exceptions & Anomalies)

Qua khảo sát toàn diện, các bất thường sau đã được ghi nhận:

1. **44 tệp ảnh PNG bị đổi đuôi thành `.jpg`:**
   - 39 tệp ở tập `train` (đều trong `Anomaly_data`).
   - 5 tệp ở tập `test` (đều trong `Anomaly_data`).
   - Các tệp này có header chuẩn PNG (`89 50 4E 47`) nhưng lại mang đuôi `.jpg`.
2. **36 mẫu có xung đột miền (Domain Mismatch) giữa tên thư mục và nội dung TXT:**
   - *Giải thích nguyên nhân số liệu:* Khảo sát sơ bộ ban đầu ghi nhận 14 mẫu do bộ lọc từ khóa đơn giản vô tình bỏ qua các mẫu chứa từ khóa phức tạp (như từ "tunnel" xuất hiện trong phần mô tả thiết bị "utility tunnel" của cảnh dầu khí). Khi chạy đối chiếu có hệ thống trên 100% mẫu (5,013 tệp) dựa trên câu mở đầu xác định ngữ cảnh của từng tệp TXT, **xác nhận chính xác 36 mẫu (thuộc 22 điểm tuần tra) có tên miền ở thư mục khác hoàn toàn với tên miền được khẳng định trong câu mở đầu TXT**.
   - **Ma trận đối chiếu giữa Folder Domain và Text Domain trên toàn bộ 5,013 mẫu:**

| Thư mục điểm (Folder Domain) \ Khẳng định trong TXT | coal_conveyor | metallurgy | oil_chemical | power | tunnel | Tổng theo thư mục |
|---|---|---|---|---|---|---|
| **coal_conveyor** | **1,121** | 0 | 0 | 0 | 0 | 1,121 |
| **metallurgy** | 0 | **712** | **8** | 0 | 0 | 720 |
| **oil_chemical** | 0 | 0 | **1,023** | 0 | 0 | 1,023 |
| **power** | **4** | 0 | 0 | **865** | 0 | 869 |
| **tunnel** | 0 | 0 | **24** | 0 | **1,256** | 1,280 |
| **Tổng theo câu mở đầu TXT** | 1,125 | 712 | 1,055 | 865 | 1,256 | **5,013** |

   - **Danh sách chi tiết đầy đủ 36 mẫu xung đột (phân theo 3 nhóm):**
     1. **Nhóm `power` (thư mục) $\rightarrow$ `coal_conveyor` (TXT):** 4 mẫu thuộc 2 điểm tuần tra (Train `Normal_data`).
        - `power-Level04-SuspendedRail-000901-001.txt` & `-002.txt` (TXT: *"In the coal conveyor bridge scene..."*)
        - `power-Level04-SuspendedRail-001700-001.txt` & `-002.txt` (TXT: *"In the coal conveyor bridge scene..."*)
     2. **Nhóm `metallurgy` (thư mục) $\rightarrow$ `oil_chemical` (TXT):** 8 mẫu thuộc 8 điểm tuần tra (Train `Anomaly_data`).
        - `metallurgy-Level01-SuspendedRail-002658-001.txt` (TXT: *"In the oil and gas chemical environment..."*)
        - `metallurgy-Level01-SuspendedRail-002659-001.txt` (TXT: *"In the oil and gas chemical environment..."*)
        - `metallurgy-Level01-SuspendedRail-002660-001.txt` (TXT: *"In the oil and gas chemical environment..."*)
        - `metallurgy-Level01-SuspendedRail-002661-001.txt` (TXT: *"In the oil and gas chemical environment..."*)
        - `metallurgy-Level01-SuspendedRail-002662-001.txt` (TXT: *"In the oil and gas chemical environment..."*)
        - `metallurgy-Level01-SuspendedRail-002663-001.txt` (TXT: *"In the oil and gas chemical environment..."*)
        - `metallurgy-Level01-SuspendedRail-002664-001.txt` (TXT: *"In the oil and gas chemical environment..."*)
        - `metallurgy-Level01-SuspendedRail-002665-001.txt` (TXT: *"In the oil and gas chemical environment..."*)
        - *Phát hiện nghiên cứu hệ quả:* Toàn bộ tập Train `Anomaly_data` của domain `metallurgy` chỉ có đúng 9 mẫu; 8 mẫu trên thực chất là cảnh dầu khí hóa chất. Cả dataset InspecSafe-V1 chỉ có duy nhất **1 mẫu dị thường luyện kim thực sự** (`metallurgy-Level03-SuspendedRail-002666-001`).
     3. **Nhóm `tunnel` (thư mục) $\rightarrow$ `oil_chemical` (TXT):** 24 mẫu thuộc 12 điểm tuần tra (mỗi điểm gồm 2 mẫu `-001` và `-002`, TXT đều mở đầu bằng *"In the oil, gas, and chemical plant scene..."*).
        - Tập Train `Normal_data` (20 mẫu / 10 điểm):
          - `tunnel-Level04-Wheeled-002224` (`-001`, `-002`)
          - `tunnel-Level04-Wheeled-002225` (`-001`, `-002`)
          - `tunnel-Level04-Wheeled-002226` (`-001`, `-002`)
          - `tunnel-Level04-Wheeled-002227` (`-001`, `-002`)
          - `tunnel-Level04-Wheeled-002228` (`-001`, `-002`)
          - `tunnel-Level04-Wheeled-002229` (`-001`, `-002`)
          - `tunnel-Level04-Wheeled-002230` (`-001`, `-002`)
          - `tunnel-Level04-Wheeled-002231` (`-001`, `-002`)
          - `tunnel-Level04-Wheeled-002232` (`-001`, `-002`)
          - `tunnel-Level04-Wheeled-002233` (`-001`, `-002`)
        - Tập Test `Normal_data` (4 mẫu / 2 điểm):
          - `tunnel-Level04-Wheeled-000558` (`-001`, `-002`)
          - `tunnel-Level04-Wheeled-000559` (`-001`, `-002`)
     - Tổng cộng chính xác: $4 + 8 + 24 = 36$ mẫu. 4,977 mẫu còn lại khớp hoàn toàn giữa tên thư mục và khẳng định miền trong TXT.
3. **Sự mất cân bằng nghiêm trọng và thiếu hụt dữ liệu dị thường ở domain `metallurgy`:**
   - Trong tập `test`: Domain `metallurgy` có 90 mẫu `Normal_data`, nhưng có **0 mẫu `Anomaly_data`**!
   - Trong tập `train`: Domain `metallurgy` có 271 mẫu `Normal_data`, nhưng chỉ có **9 mẫu `Anomaly_data`** (trong đó có tới 4 mẫu nội dung TXT lại nói về dầu khí).
   - Điều này tạo ra rủi ro nghiêm trọng nếu dùng `metallurgy` làm tập test cross-domain cho bài toán phát hiện dị thường / thẩm định an toàn.
4. **Mất cân bằng cực đoan giữa các cấp độ an toàn (Extreme Class Imbalance):**
   - `Level04` (Bình thường): 4,013 mẫu (**80.05%**).
   - `Level01` (Nguy cơ cao): 659 mẫu (**13.15%**).
   - `Level02` (Nguy cơ vừa): 326 mẫu (**6.50%**).
   - `Level03` (Nguy cơ thấp): **Chỉ có 15 mẫu trên toàn bộ dataset (0.30%)** (8 mẫu train, 7 mẫu test).
5. **`Other_modalities` chỉ tồn tại cho dữ liệu bình thường (`Normal_data`):**
   - 100% các mẫu dị thường (`Anomaly_data`, 1,000 điểm) **hoàn toàn không có dữ liệu đa phương thức** trong `Other_modalities`.
   - Trong `train`, có 1 điểm normal bị thiếu trong `Other_modalities`: `oil_chemical-Level04-SuspendedRail-001477`.
   - Tồn tại 2 tệp rác dung lượng 0 byte tên tiếng Trung `分帧` bên trong `Other_modalities` (`train/.../002053` và `test/.../000422`).
6. **1 nhãn polygon duy nhất chứa ký tự tiếng Trung:**
   - Nhãn `"出口"` (Exit) xuất hiện đúng 1 lần tại `tunnel-Level01-SuspendedRail-003064-001.json`.

---

## 12. Đánh giá về khả năng hỗ trợ Evidence Grounding của Dataset

Theo nguyên tắc nghiên cứu số 10: *Chưa được kết luận rằng dataset hỗ trợ grounding theo cách nào cho tới khi đã nhìn dữ liệu thật.*

Sau khi khảo sát toàn bộ 37,434 đa giác gán nhãn trong 5,013 tệp JSON, chúng tôi xác minh thực tế như sau:

1. **Bản chất của annotation hình học:**
   - Toàn bộ annotation là **các đa giác phân vùng đối tượng thông thường (Instance Segmentation Masks)** theo chuẩn AnyLabeling / LabelMe.
   - Không có trường `evidence_id`, không có bounding box riêng cho bằng chứng, không có liên kết (linking) giữa các đối tượng và câu mô tả lý do mất an toàn.
2. **Đối với các nguy cơ vật lý hiện hữu (Positive Physical Hazards):**
   - Với các đối tượng nguy cơ như `Open Flame` (Ngọn lửa hở), `Cigarette` (Điếu thuốc), `Mobile Phone` (Điện thoại), `Plastic Bag` / `Foreign Object` (Dị vật), `Liquid` / `Oil` (Tràn dầu/nước), trong tệp JSON **thực sự có đa giác bao quanh chính đối tượng đó**.
   - Tuy nhiên, đa giác này được lưu bình đẳng ngang hàng với các đối tượng nền xung quanh (`Pipeline`, `Stent`, `Window`, `Stairs`). JSON không tự chỉ ra đa giác nào là nguyên nhân gây nguy hiểm.
3. **Đối với các vi phạm thiếu trang bị bảo hộ (Negative/Absence PPE Violations):**
   - Với các trường hợp vi phạm quy tắc như *"personnel not wearing safety helmets"*, *"not wearing gloves"*, *"not wearing masks"*, **hoàn toàn không có đa giác nào cho vật thể bị thiếu** (vì vật thể không tồn tại trong ảnh).
   - Đa giác tồn tại duy nhất có liên quan trong ảnh là đa giác bao quanh toàn bộ cơ thể người (`Person`), không có phân vùng riêng cho đầu (`Head`) hay tay (`Hands`).
4. **Kết luận về bài toán Grounding:**
   - InspecSafe-V1 **không cung cấp sẵn nhãn Grounding chuyên biệt (turnkey Grounding annotations)**.
   - Để đánh giá khả năng Grounding của VLM trên InspecSafe-V1, SafeShift sẽ cần phải:
     - Định nghĩa một từ điển phân loại (Taxonomy): tách các nhãn đối tượng thành hai nhóm: `Hazard/Evidence Labels` (ví dụ `Open Flame`, `Cigarette`, `Mobile Phone`, ...) và `Benign Context Labels` (`Pipeline`, `Stent`, ...).
     - Quy ước cách đánh giá Grounding cho các vi phạm thiếu bảo hộ (ví dụ: grounding trúng hộp giới hạn của đối tượng `Person` vi phạm).
     - Chuyển đổi tọa độ đa giác (`points`) thành hộp giới hạn (`[x1, y1, x2, y2]`) hoặc mặt nạ nhị phân phục vụ tính toán các độ đo IoU / Pointing Game.

---

## 13. Các câu hỏi mở cần giải quyết trước Week 2 (Research Protocol)

1. **Chiến lược xử lý mất cân bằng nhãn an toàn:**
   - Cấp 3 (`Level03`) chỉ có vỏn vẹn 15 mẫu trong toàn bộ 5,013 mẫu. Liệu nên gộp phân loại thành 3 mức (Level 1, Level 2, Normal) hay giữ nguyên 4 mức phân loại như đề xuất ban đầu của tác giả dataset?
2. **Chiến lược phân chia Cross-Domain Generalization:**
   - Ngành `metallurgy` ở tập test có 0 mẫu dị thường và chỉ có 9 mẫu dị thường ở train. Có nên loại `metallurgy` khỏi vai trò target test domain trong bài toán phát hiện bất thường hay không?
   - Cần chốt rõ các cặp source/target domain (ví dụ train trên 3-4 domain, evaluate zero-shot trên domain còn lại) để tránh sai lệch dữ liệu.
3. **Xử lý 36 mẫu mâu thuẫn domain:**
   - Nên tin cậy nhãn domain từ tên thư mục (hệ thống tuần tra robot thực tế ghi nhận) hay từ câu mô tả cảnh trong tệp TXT? Cần ghi nhận thành quy tắc trong manifest.
4. **Phương pháp đánh giá Grounding cho vi phạm thiếu bảo hộ (Negative PPE):**
   - Khi mô hình VLM giải thích *"không đội mũ bảo hiểm"*, bounding box mô hình đưa ra cần khớp với vùng đầu của công nhân hay chấp nhận khớp với toàn bộ cơ thể `Person`?
5. **Khai thác dữ liệu đa phương thức (`Other_modalities`):**
   - Do `Other_modalities` hoàn toàn không có mẫu dị thường nào, dataset hiện tại ở dạng multimodal chỉ phục vụ bài toán unsupervised / one-class anomaly detection (học phân bố bình thường từ video/cảm biến rồi phát hiện ngoại lai). Đối với bài toán đánh giá an toàn qua VLM (Zero-shot / Few-shot Safety Assessment), chúng ta chủ yếu khai thác nhánh thị giác khả kiến (`Annotations`) hay có kế hoạch mở rộng sang video/cảm biến không?

---

## 14. Nguồn gốc và phương pháp kiểm chứng số liệu (Provenance of Audit Statistics)

Nhằm đảm bảo tính minh bạch và khả năng tái lập theo quy định tại `AGENTS.md`, toàn bộ số liệu thống kê trong báo cáo này được tạo ra từ quy trình kiểm kê trực tiếp trên dữ liệu gốc như sau:

- **Môi trường thực thi:** Python 3.11.9 (sử dụng hoàn toàn thư viện chuẩn: `pathlib`, `json`, `re`, `struct`, `collections.Counter`, `collections.defaultdict`), hệ điều hành Windows 10/11 x64, thực hiện trong workspace `d:\SafeShift`.
- **Các script kiểm kê cục bộ:** Được lưu và thực thi tại thư mục scratch cục bộ của tiến trình phân tích (`.gemini/antigravity/brain/<conversation-id>/scratch/`), gồm:
  1. `scratch/comprehensive_survey.py`: Quét toàn bộ cây thư mục, kiểm đếm 3,234 thư mục waypoint, 5,013 mẫu, phân bố instance trên mỗi waypoint theo split và phân loại nhãn, kiểm chứng 100% regex đặt tên thư mục và tệp.
  2. `scratch/survey_json.py` & `scratch/check_shape_fields.py`: Phân tích toàn diện 5,013 tệp JSON, kiểm tra 7 trường top-level, quét 37,434 đa giác, 231 nhãn đối tượng, xác minh 100% các trường metadata (`attributes`, `flags`, `description`, `group_id`, `score`, `difficult`, `kie_linking`) rỗng/null, và kiểm tra ranh giới Point ID giữa train và test (overlap = 0).
  3. `scratch/check_magic_bytes.py` & `scratch/verify_jpegs.py`: Đọc trực tiếp magic bytes nhị phân ở cấp byte (`\xff\xd8\xff` và `\x89PNG\r\n\x1a\n`) của toàn bộ 5,013 ảnh, phát hiện chính xác 4,969 ảnh JPEG và 44 ảnh PNG bị đổi đuôi thành `.jpg`; giải mã kích thước nhị phân từ SOF0/IHDR và đối chiếu khớp 100% với trường `imageWidth`/`imageHeight` trong JSON.
  4. `scratch/check_txt.py` & `scratch/list_all_mismatches.py`: Đọc 5,013 tệp TXT, kiểm tra định dạng văn bản một dòng tiếng Anh, trích xuất các biến thể từ vựng đánh giá mức độ an toàn; phân loại câu mở đầu xác định ngữ cảnh không gian và lập ma trận đối chiếu 5x5 với tên thư mục điểm, xác nhận chính xác 36 mẫu xung đột miền.
- **Ghi chú về phạm vi:** Toàn bộ mã nguồn trên là các script kiểm toán cục bộ dùng một lần (ad-hoc audit scripts) phục vụ khảo sát Week 1, không được đưa vào repository chính thức và chưa phải là production dataset parser. Bộ parser hoàn chỉnh với unit tests và schema validation sẽ được xây dựng độc lập trong các task tiếp theo.
