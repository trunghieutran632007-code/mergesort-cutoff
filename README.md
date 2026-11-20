# Thí nghiệm tìm CUTOFF tối ưu cho Mergesort

Project môn Cấu trúc dữ liệu và giải thuật (UET): đo thực nghiệm để tìm độ dài CUTOFF chuyển sang insertion sort
cho mergesort tự cài đặt từ bài giảng, và trả lời câu hỏi nên chọn CUTOFF = 7 hay 10.

Báo cáo: [report/bao-cao.docx](report/bao-cao.docx) (Word) và [report/bao-cao.md](report/bao-cao.md) (Markdown).

## Kết quả chính

Trên máy đo (MacBook Air M2, JDK 25.0.1, mảng `int[]`):

- **CUTOFF nên nằm trong khoảng 40–50; nếu chọn một giá trị thì chọn 40.** Trên dữ liệu ngẫu nhiên, cutoff 40
  nhanh hơn mergesort không cutoff 16–27% và cách tối ưu không quá 2% ở cả bốn N (10⁴ đến 10⁷).
- **Giữa 7 và 10 thì 10 tốt hơn:** nhanh hơn 1.45–6.01%, khác biệt có ý nghĩa thống kê ở 14/15 cấu hình.
  Tuy vậy cutoff 40 còn giảm thêm được 5–15% thời gian so với cả 7 và 10.

## Nội dung

| Đường dẫn | Nội dung |
|---|---|
| `src/Merge.java` | Mergesort có cutoff, `Merge.sort(int[] a, int cutoff)`: đoạn có độ dài ≤ cutoff dùng insertion sort; cutoff 0 là không cutoff. Tự viết từ bài giảng |
| `src/MergeCount.java` | Bản sao của `Merge` có đếm số phép so sánh (dùng cho TN3). Tự viết từ bài giảng |
| `src/TestCorrectness.java` | Kiểm tra tính đúng của hai file trên, đối chiếu với `Arrays.sort` |
| `src/DataGen.java`, `src/DataIO.java` | Sinh dữ liệu theo seed cố định; đọc/ghi file `.bin` |
| `src/Benchmark.java` | Harness đo thời gian `Merge.sort` theo cutoff (TN1, TN2, TN5) |
| `src/CompareCount.java` | Đếm số phép so sánh theo cutoff (TN3) |
| `src/SmallBench.java` | Insertion sort so với mergesort trên mảng ngắn (TN4) |
| `scripts/config.sh` | Cờ JVM dùng chung cho mọi lần đo: `-Xms4g -Xmx4g` |
| `scripts/gen_data.sh` | Sinh toàn bộ dữ liệu vào `data/` |
| `scripts/machine_info.sh` | Ghi cấu hình máy vào `results/machine.txt` |
| `scripts/run_pilot.sh`, `scripts/check_pilot.py` | Chạy thử harness và kiểm tra nhanh file CSV |
| `scripts/run_all.sh` | Chạy các thí nghiệm TN1–TN5 |
| `scripts/analyze.py` | Thống kê: bảng A–F, hình 1–5 |
| `scripts/leaf_sizes.py` | Độ dài đoạn lá của cây đệ quy theo cutoff: bảng G, hình 6 |
| `data/` | Bộ dữ liệu và `manifest.csv` (seed, SHA-256 của từng file) |
| `results/` | CSV thô và file `.meta.txt` của mọi lần đo, log của từng đợt chạy, `machine.txt` |
| `results/bi-chay-chong/GHI-CHU.md` | Ghi chú về số liệu bị loại vì hai đợt đo chạy chồng nhau |
| `tables/`, `figures/` | Bảng (CSV đầy đủ và Markdown) và đồ thị, do hai script phân tích sinh ra |
| `report/` | Báo cáo |
| `ke-hoach-mergesort-cutoff.md` | Kế hoạch làm project theo từng bước |
| `CLAUDE.md` | Quy tắc khi dùng AI (Claude Code) trong project; việc dùng AI được trình bày ở mục 10 của báo cáo |

## Yêu cầu môi trường

- **JDK 17 trở lên.** Số liệu trong báo cáo đo bằng JDK 25.0.1. JVM chạy với heap cố định 4 GB nên máy cần
  ít nhất 8 GB RAM.
- **Python 3.12** với các thư viện trong `requirements.txt` (pandas, NumPy, SciPy, matplotlib, đúng phiên bản đã dùng).
- **macOS cho các script đo** (`run_all.sh`, `run_pilot.sh`, `machine_info.sh`), vì chúng dùng `pmset`, `sysctl`,
  `sw_vers`, `caffeinate`. Trên hệ điều hành khác, chạy trực tiếp các lệnh `java` ở mục
  [Chạy từng thí nghiệm không qua script](#chạy-từng-thí-nghiệm-không-qua-script).
  Biên dịch, test, sinh dữ liệu và phân tích chạy được ở mọi nơi có `bash`, JDK và Python.
- Khoảng 130 MB đĩa trống cho `data/` sau khi sinh đủ dữ liệu.

## Chạy lại từ đầu (Các bước thí nghiệm)

Mọi lệnh chạy từ thư mục gốc của project. Thời gian ghi trong ngoặc là thời gian trên máy đo.

**1. Tạo môi trường Python** (một lần, khoảng 10 giây, cần mạng):

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

**2. Biên dịch và kiểm tra tính đúng** (khoảng 5 giây):

```bash
javac -encoding UTF-8 -d out src/*.java
java -cp out TestCorrectness
```

Khi qua hết, dòng cuối in `TẤT CẢ ĐỀU ĐÚNG: 240307 phép kiểm tra, seed = 20261109`. Gặp ca sai đầu tiên thì
test in ra (n, cutoff, loại dữ liệu, seed) và dừng với mã thoát 1.

**3. Sinh dữ liệu** (khoảng 3 giây):

```bash
bash scripts/gen_data.sh
```

Script sinh lại toàn bộ 19 file `.bin` từ seed cố định, kể cả các file đã có trong git. Mỗi dòng in ra phải kết thúc
bằng `khớp manifest cũ`, nghĩa là SHA-256 của file vừa sinh trùng với `data/manifest.csv`. Xem thêm mục [Dữ liệu](#dữ-liệu).

**4. Chạy thí nghiệm** (khoảng 23 phút cho cả năm TN):

```bash
bash scripts/run_all.sh
```

Trước khi chạy: cắm sạc, tắt Low Power Mode, đóng trình duyệt và các ứng dụng nặng, không dùng máy trong lúc đo.
Script tự dừng nếu máy chưa cắm sạc hoặc đang bật Low Power Mode. **Chỉ chạy một đợt đo tại một thời điểm**: hai đợt
chạy chồng nhau làm số đo chậm đi khoảng 2.5% (xem `results/bi-chay-chong/GHI-CHU.md`).

Trước khi đo, script biên dịch lại `src/`, ghi lại `results/machine.txt` theo máy đang chạy và chạy `TestCorrectness`.
Mỗi lần gọi harness là một tiến trình JVM riêng; giữa hai TN máy nghỉ 120 giây.

Các cách gọi khác:

| Lệnh | Tác dụng |
|---|---|
| `bash scripts/run_all.sh tn1` | Chỉ chạy TN1 (có thể ghi nhiều tên: `tn1 tn2`) |
| `DRY_RUN=1 bash scripts/run_all.sh` | Chỉ in các lệnh `java` sẽ chạy, không đo gì |
| `PAUSE=0 bash scripts/run_all.sh` | Không nghỉ giữa các TN |
| `BEST_CUTOFF=40 bash scripts/run_all.sh tn5` | TN5 dùng cutoff 40 thay cho cutoff tốt nhất tự lấy từ TN1 |

Năm thí nghiệm:

| TN | Câu hỏi | Dữ liệu | Cutoff hoặc độ dài | Trial | Thời gian |
|---|---|---|---|---:|---:|
| TN1 | Cutoff nào nhanh nhất, theo N? | random, N = 10⁴, 10⁵, 10⁶, 10⁷ | 0–30, 40, 50, 64, 80, 96, 128 | 30 (10⁷: 10) | 9 phút |
| TN2 | Phân bố dữ liệu có làm dịch điểm tối ưu? | sorted, reversed, nearly, fewdistinct, N = 10⁶ | như TN1 | 20 | 2 phút |
| TN3 | Cutoff ảnh hưởng số phép so sánh thế nào? | random, N = 10⁶ | 0–64, 80, 96, 128 | 3 | 17 giây |
| TN4 | Insertion sort nhanh hơn mergesort đến độ dài nào? | mảng random độ dài n | n = 2–64, 80, 96, 112, 128, 160, 192, 256 | 30 | 2 phút |
| TN5 | Cutoff có đổi bậc tăng trưởng không? (doubling test) | random, N = 2¹⁷ đến 2²³ | 0, 7, 10 và cutoff tốt nhất của TN1 | 10 | 2 phút |

"Cutoff tốt nhất của TN1" là cutoff có median nhỏ nhất ở TN1, N = 10⁶, trong file TN1 mới nhất của `results/`.

Mỗi đợt chạy có một timestamp `TS` chung cho mọi file. Đầu ra ghi thêm vào `results/`, không ghi đè file cũ:

- `results/<tn>_<phân bố>_<N>_<TS>.csv`: số liệu thô, mỗi phép đo một dòng;
- `results/<tn>_<phân bố>_<N>_<TS>.meta.txt`: tham số, K, cờ JVM thực tế, trạng thái kết thúc;
- `results/run_<TS>.log`: toàn bộ những gì in ra màn hình.

**5. Phân tích** (dưới một phút):

```bash
.venv/bin/python scripts/analyze.py
.venv/bin/python scripts/leaf_sizes.py
```

`analyze.py` đọc `results/tn*.csv` (bỏ qua file `pilot_*` và các thư mục con), ghi `tables/A`–`F`,
`tables/thong_ke_day_du.csv` và hình 1–5 vào `figures/`. `leaf_sizes.py` đọc `tables/thong_ke_day_du.csv` nên
phải chạy sau, ghi `tables/G` và hình 6. Hai script ghi đè `tables/` và `figures/` mỗi lần chạy, vì toàn bộ
tạo lại được từ `results/`.

Với mỗi (TN, phân bố, N), file mới nhất là số liệu chính; các lần chạy TN1 cũ hơn chỉ dùng cho bảng D (độ lặp lại).
Vì vậy, sau khi chạy lại bước 4, bảng và hình sẽ theo số đo mới và không còn khớp từng con số trong báo cáo.
Chạy bước 5 ngay trên bản clone, chưa đo thêm gì, thì cho lại đúng các file `tables/` và `figures/` trong git.

**Chạy thử harness** (không bắt buộc, dưới một phút): `bash scripts/run_pilot.sh` đo random N = 10⁵ và 10⁶
với cutoff 0, 1, 5, 10, 20, 5 trial, rồi gọi `check_pilot.py`. `check_pilot.py` cũng kiểm tra nhanh được file CSV
của TN1, TN2, TN5: `.venv/bin/python scripts/check_pilot.py results/tn1_random_1000000_<TS>.csv`.

## Chạy từng thí nghiệm không qua script

Dùng khi không chạy được `run_all.sh` (không phải macOS), hoặc muốn đo một cấu hình riêng. Sau khi biên dịch và
sinh dữ liệu (bước 2, 3), mỗi dòng dưới đây là một tiến trình JVM; đổi `<TS>` thành thời điểm chạy, ví dụ
`20261120_134812`. Harness không ghi đè file `--out` đã tồn tại.

```bash
# TN1: lặp với N = 10000, 100000, 1000000 (30 trial) và N = 10000000 (10 trial)
java -Xms4g -Xmx4g -cp out Benchmark --exp tn1 --data data/random_1000000.bin --cutoffs 0-30,40,50,64,80,96,128 --trials 30 --warmup 50 --out results/tn1_random_1000000_<TS>.csv

# TN2: lặp với sorted, reversed, nearly, fewdistinct
java -Xms4g -Xmx4g -cp out Benchmark --exp tn2 --data data/sorted_1000000.bin --cutoffs 0-30,40,50,64,80,96,128 --trials 20 --warmup 50 --out results/tn2_sorted_1000000_<TS>.csv

# TN3
java -Xms4g -Xmx4g -cp out CompareCount --exp tn3 --data data/random_1000000.bin --cutoffs 0-64,80,96,128 --trials 3 --out results/tn3_random_1000000_<TS>.csv

# TN4
java -Xms4g -Xmx4g -cp out SmallBench --exp tn4 --sizes 2-64,80,96,112,128,160,192,256 --trials 30 --warmup 50 --out results/tn4_random_small_<TS>.csv

# TN5: lặp với N = 131072, 262144, ..., 8388608 (2^17 đến 2^23)
java -Xms4g -Xmx4g -cp out Benchmark --exp tn5 --data data/random_131072.bin --cutoffs 0,7,10,40 --trials 10 --warmup 50 --out results/tn5_random_131072_<TS>.csv
```

Tên file `--out` phải giữ dạng `<tn>_<phân bố>_<N>_<yyyyMMdd_HHmmss>.csv` thì `analyze.py` mới đọc được.

## Dữ liệu

- **Phân bố:** `random` (số nguyên ngẫu nhiên đều trên toàn miền `int`), `sorted` (0, 1, …, N−1), `reversed`,
  `nearly` (mảng đã sắp xếp rồi hoán đổi ngẫu nhiên N/100 cặp phần tử), `fewdistinct` (giá trị ngẫu nhiên trong 0..9).
- **Seed:** mỗi (phân bố, N) có một seed cố định `seed = 20261109 × 10⁹ + mã phân bố × 10⁸ + N`, với mã random 0,
  sorted 1, reversed 2, nearly 3, fewdistinct 4. Seed của từng file ghi trong `data/manifest.csv`.
- **Định dạng `.bin`:** 4 byte N, sau đó N số `int` (big-endian, như `DataOutputStream`), tổng 4 + 4N byte.
  Các file N = 10⁴ có thêm bản `.txt` (dòng đầu là N, mỗi dòng sau một số) để xem bằng mắt.
- **File trong git:** mọi file có N ≤ 2²⁰ (khoảng 27 MB).
- **File không đưa lên git:** bốn file random lớn, N = 10⁷, 2²¹, 2²², 2²³ (tổng khoảng 96 MB). Sinh lại bằng
  `scripts/gen_data.sh`; `DataGen` so SHA-256 của file vừa sinh với `data/manifest.csv`.

## Đóng gói để nộp
