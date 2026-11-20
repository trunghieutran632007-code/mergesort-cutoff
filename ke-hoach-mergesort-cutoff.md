# Kế hoạch project: Tìm CUTOFF tối ưu cho Mergesort (thay thế cho log chat với AI)

9/11/2026 · Hiếu

## Tổng quan

Mục tiêu: tìm giá trị CUTOFF cho thời gian chạy nhỏ nhất trên máy của bạn, và trả lời câu hỏi 7 hay 10 phù hợp hơn. Cần phân biệt khác biệt thật với nhiễu đo. Toàn bộ kế hoạch có 9 bước, khoảng 3–4 buổi làm việc.

Nguyên tắc xuyên suốt: Merge.java do bạn tự viết từ bài giảng. Claude Code chỉ viết test, harness đo, script sinh dữ liệu, script phân tích và góp ý báo cáo.

| Bước | Việc chính | Ai làm | Thời gian | Đầu ra |
| --- | --- | --- | --- | --- |
| 0 | Môi trường, git, CLAUDE.md | Bạn | 1 giờ | Thư mục project, CLAUDE.md, machine.txt |
| 1 | Cài đặt mergesort | Bạn tự viết, không AI | 2–3 giờ | Merge.java, MergeCount.java |
| 2 | Test tính đúng | Claude Code viết test, bạn sửa lỗi | 1 giờ | TestCorrectness.java |
| 3 | Sinh bộ dữ liệu | Claude Code | 1 giờ | DataGen.java, data/ |
| 4 | Harness đo, chạy thử | Claude Code, bạn kiểm tra | 2 giờ | Benchmark.java, CSV chạy thử |
| 5 | Chạy thí nghiệm | Máy chạy | 1–2 giờ máy | results/*.csv |
| 6 | Thống kê, đồ thị | Claude Code viết script, bạn đọc kết quả | 2 giờ | analyze.py, figures/, tables/ |
| 7 | Viết báo cáo | Bạn viết, Claude góp ý | 4–6 giờ | Báo cáo |
| 8 | Đóng gói, nộp | Bạn | 30 phút | README.md, file zip |

Câu hỏi mở: hạn nộp là ngày nào? Có hạn thì chia lịch ngược từ đó; nên xong Bước 0–2 ngay trong buổi đầu.

Commit git sau mỗi bước. Lịch sử commit là bằng chứng bạn tự làm Merge.java trước khi dùng AI.

## Bước 0 — Chuẩn bị môi trường

Kết quả của bước này: một thư mục project có git, file CLAUDE.md đặt luật cho Claude Code, và file ghi cấu hình máy.

1. Cài đặt: JDK 17 hoặc 21 (kiểm tra bằng `java -version`), Python 3 với `pip install pandas matplotlib scipy numpy`, git, Claude Code desktop. Trên Windows, dùng Git Bash để chạy các script `.sh`.
2. Tạo cấu trúc thư mục:

```
mergesort-cutoff/
├── CLAUDE.md
├── README.md
├── src/        # Merge.java, MergeCount.java, test, harness
├── data/       # bộ dữ liệu sinh ra
├── results/    # CSV thô, machine.txt, log
├── scripts/    # gen_data.sh, run_all.sh, analyze.py
├── figures/    # đồ thị
├── tables/     # bảng thống kê
└── report/     # báo cáo
```

3. Chạy `git init` và commit khung thư mục trống.
4. Ghi cấu hình máy vào `results/machine.txt`: model CPU, số nhân, RAM, hệ điều hành, phiên bản JDK. Lệnh tham khảo: macOS `sysctl -n machdep.cpu.brand_string` và `sysctl hw.memsize`; Windows `systeminfo`; Linux `lscpu`. Có thể nhờ Claude Code viết script tự ghi.
5. Tạo `CLAUDE.md` với nội dung dưới đây. Claude Code đọc file này đầu mỗi phiên, nên đây là nơi đặt luật chơi.

```markdown
# Project: Thí nghiệm CUTOFF cho Mergesort (môn CTDL&GT, UET)

## Quy tắc bắt buộc
- src/Merge.java và src/MergeCount.java do tôi tự viết từ bài giảng.
  KHÔNG viết mới, sửa, refactor hay "tối ưu" các file này.
  Nếu thấy lỗi: chỉ mô tả lỗi và vị trí để tôi tự sửa.
- Không dùng hay tham khảo cài đặt mergesort khác (algs4 Merge/MergeX, mã trên mạng).
  Arrays.sort chỉ được dùng trong test để đối chiếu kết quả.
- Được phép: test tính đúng, harness đo thời gian, script sinh dữ liệu,
  script phân tích và vẽ đồ thị, góp ý báo cáo.

## Quy ước
- Java chuẩn: System.out.println, Scanner/BufferedReader.
  Không dùng thư viện algs4 (StdIn, StdOut, StdRandom).
- Python 3 + pandas, matplotlib, scipy cho phân tích.
- API: Merge.sort(int[] a, int cutoff). Đoạn con có độ dài <= cutoff thì dùng insertion sort.
  cutoff = 0 nghĩa là không dùng insertion sort (baseline).
- Dữ liệu ngẫu nhiên luôn sinh bằng seed cố định, ghi seed vào output.
- Kết quả đo ghi CSV thô vào results/, tên file có timestamp, không ghi đè file cũ.
```

## Bước 1 — Tự cài đặt Merge.java (không dùng AI)

Đây là phần duy nhất đề cấm dùng cài đặt khác. Hãy viết tay dựa trên slide Mergesort (top-down, mảng phụ `aux`) và không mở Claude Code khi làm bước này.

Các hàm cần có trong `src/Merge.java`:

- `public static void sort(int[] a, int cutoff)`: cấp phát `aux` một lần, rồi gọi hàm đệ quy.
- `private static void sort(int[] a, int[] aux, int lo, int hi, int cutoff)`: nếu độ dài `hi - lo + 1 <= cutoff` thì insertion sort đoạn `a[lo..hi]` rồi return; ngược lại chia đôi, sort hai nửa, merge.
- `private static void merge(int[] a, int[] aux, int lo, int mid, int hi)`: copy sang `aux`, trộn ngược về `a`, như slide.
- `static void insertionSort(int[] a, int lo, int hi)`: insertion sort trên một đoạn con. Để mức truy cập package (không `private`) vì thí nghiệm TN4 cần gọi trực tiếp.
- `public static boolean isSorted(int[] a)`.

Các quyết định thiết kế cần ghi lại để đưa vào báo cáo:

- **Kiểu dữ liệu**: dùng `int[]` cho thí nghiệm chính. Kiểu nguyên thủy cho số đo ổn định hơn, ít nhiễu do GC.
- **Chỉ bật cải tiến cutoff**: tắt kiểm tra `a[mid] <= a[mid+1]` và kỹ thuật đổi vai `a`/`aux`. Như vậy tác động đo được chỉ đến từ cutoff.
- **Định nghĩa CUTOFF chính xác**: đoạn có độ dài ≤ CUTOFF thì insertion sort. Slide algs4 viết `hi <= lo + CUTOFF - 1` (độ dài ≤ CUTOFF), nhưng một số bản code algs4 viết `hi <= lo + CUTOFF` (độ dài ≤ CUTOFF + 1). Kiểm tra lại slide của cô và ghi rõ quy ước khi so sánh với 7 và 10.

Sau khi `Merge.java` chạy đúng, tạo `src/MergeCount.java`: bản sao code của bạn, thêm biến `static long compares` tăng ở mỗi phép so sánh (trong `merge` và `insertionSort`). File này chỉ dùng cho thí nghiệm đếm (TN3). Không dùng nó để đo thời gian vì phép đếm làm chậm code.

Nếu định làm TN6 (tùy chọn), viết thêm `MergeGeneric.java` cho `Comparable[]`, cùng logic.

Commit với message rõ ràng, ví dụ "Tự cài đặt Merge.java từ bài giảng". Nếu muốn, gửi file lên chat project để mình review trước khi sang bước sau.

## Bước 2 — Kiểm tra tính đúng

Một bản sort sai mà chạy nhanh sẽ làm mọi số đo vô nghĩa, nên phải test kỹ trước khi đo. Đây là lần đầu bạn dùng Claude Code. Prompt mẫu:

```
Đọc CLAUDE.md. Viết src/TestCorrectness.java để kiểm tra Merge.sort(int[] a, int cutoff):
- Với mọi cutoff trong {0, 1, 2, ..., 40, 64, 100} và mọi n từ 0 đến 300,
  cùng vài n lớn (1000, 4096, 100000): sinh mảng ngẫu nhiên với seed cố định,
  sort bằng Merge.sort, so sánh với bản sao sort bằng Arrays.sort.
- Thêm mảng đặc biệt: đã sắp xếp, sắp xếp ngược, toàn phần tử bằng nhau,
  chỉ có 2 giá trị, có số âm.
- Kiểm tra tương tự cho MergeCount.
- Gặp ca sai đầu tiên thì in (n, cutoff, loại dữ liệu) rồi dừng.
- Không sửa Merge.java hay MergeCount.java.
```

Vì sao n chạy từ 0 đến 300 với mọi cutoff: lỗi hay nằm ở biên, khi n = cutoff hoặc n = cutoff + 1, và ở mảng rỗng hoặc 1 phần tử.

Nếu test báo lỗi, hỏi Claude Code "lỗi nằm ở đâu, vì sao" rồi tự sửa. Qua hết test thì commit.

## Bước 3 — Sinh bộ dữ liệu

Bộ dữ liệu gồm 5 phân bố, sinh bằng seed cố định để ai chạy lại cũng ra đúng input đó.

| Tên | Mô tả | Mục đích |
| --- | --- | --- |
| random | Số nguyên ngẫu nhiên đều | Trường hợp chính |
| sorted | 0, 1, ..., N−1 | Insertion sort chạy tuyến tính, cutoff lớn có lợi |
| reversed | N−1, ..., 0 | Trường hợp xấu nhất của insertion sort |
| nearly | Đã sắp xếp, hoán đổi ngẫu nhiên 1% phần tử | Dữ liệu gần sắp xếp, hay gặp thực tế |
| fewdistinct | Giá trị trong 0–9 | Nhiều phần tử trùng |

Kích thước theo từng thí nghiệm ở Bước 5: random cần N = 10^4, 10^5, 10^6, 10^7 và dãy doubling 2^17 → 2^23. Bốn phân bố còn lại chỉ cần N = 10^6.

Về dung lượng: lưu dạng nhị phân (4 byte mỗi số). Toàn bộ dữ liệu khoảng 120 MB, có thể quá nặng để nộp. Phương án: nộp file thật cho N ≤ 10^6, còn file lớn thì nộp generator, seed và mã SHA-256 để chứng minh tái tạo được.

Prompt mẫu:

```
Đọc CLAUDE.md. Viết src/DataGen.java:
- Sinh 5 phân bố: random, sorted, reversed, nearly (sorted rồi hoán đổi ngẫu nhiên 1% phần tử),
  fewdistinct (giá trị 0..9). Kích thước lấy từ tham số dòng lệnh.
- Mỗi (phân bố, N) có seed cố định. Ghi data/manifest.csv gồm: tên file, phân bố, N, seed, SHA-256.
- Ghi file nhị phân data/<dist>_<N>.bin (DataOutputStream: N rồi N số int).
  Với N <= 10000 ghi thêm bản .txt để xem bằng mắt.
- Viết lớp src/DataIO.java với hàm int[] read(String path) để harness dùng.
- Viết scripts/gen_data.sh sinh toàn bộ dữ liệu cho các thí nghiệm: random với
  N = 10^4, 10^5, 10^6, 10^7 và 2^17..2^23; sorted, reversed, nearly, fewdistinct với N = 10^6.
```

Kiểm tra nhanh: mở file `.txt` của N = 10^4, xem từng phân bố có đúng dạng không. Commit generator và manifest; thêm các file `.bin` lớn vào `.gitignore`.

## Bước 4 — Harness đo thời gian và chạy thử

Đo sai là lỗi phổ biến nhất của project này. Bảy nguyên tắc dưới đây vừa là yêu cầu cho Claude Code, vừa là nội dung bạn phải hiểu để viết phần phương pháp trong báo cáo.

1. **Warm-up**: trước khi đo, sort khoảng 50 lần với nhiều cutoff khác nhau để JIT biên dịch xong code.
2. **Cùng input**: mọi cutoff sort trên bản sao (`clone`) của cùng một mảng gốc. Thời gian clone không tính vào kết quả.
3. **Nhiều trial, thứ tự ngẫu nhiên**: mặc định 30 trial; mỗi trial trộn thứ tự các cutoff để nhiễu (máy nóng lên, GC) không dồn vào một cutoff.
4. **Đo theo lô khi N nhỏ**: với N ≤ 10^5, một lần sort quá ngắn so với nhiễu. Mỗi phép đo sort K bản sao chuẩn bị sẵn, rồi chia thời gian cho K, sao cho mỗi phép đo kéo dài ít nhất khoảng 20 ms.
5. **Kiểm tra kết quả**: sau mỗi lần sort gọi `isSorted` (ngoài vùng tính giờ); sai thì dừng chương trình.
6. **Cố định JVM**: heap cố định, ví dụ `-Xms4g -Xmx4g` tùy RAM, ghi flag vào `machine.txt`. Mỗi thí nghiệm chạy trong một tiến trình JVM riêng.
7. **Ghi số liệu thô**: CSV gồm experiment, dist, n, cutoff, trial, k, ns_per_sort. Không tính trung bình trong Java; việc đó để Python làm ở Bước 6.

Prompt mẫu:

```
Đọc CLAUDE.md. Viết src/Benchmark.java đo thời gian Merge.sort theo 7 nguyên tắc sau:
[dán 7 nguyên tắc ở trên]
Tham số dòng lệnh: --data <file .bin>, --cutoffs 0-30,40,50,64, --trials 30, --warmup 50,
--exp <tên thí nghiệm>, --out results/<tên>_<timestamp>.csv.
In tiến độ ra màn hình (trial hiện tại / tổng). Chỉ gọi Merge.sort, không tự cài sort khác.
Sau đó viết scripts/run_pilot.sh: chạy random N = 10^5 và 10^6, cutoffs 0,1,5,10,20, trials 5.
```

Chạy pilot rồi kiểm tra bốn điều:

- [ ] Chương trình không lỗi, CSV đúng định dạng.
- [ ] Cutoff 0 và cutoff 1 cho thời gian gần như bằng nhau, vì hai cách này tương đương. Chênh lệch giữa chúng cho bạn ước lượng mức nhiễu đo.
- [ ] Độ lệch chuẩn chia trung bình dưới khoảng 5%. Nếu lớn hơn: tăng K, tăng warm-up, tắt ứng dụng nền.
- [ ] Từ thời gian pilot, ước lượng tổng thời gian chạy chính thức.

Có thể đưa CSV pilot cho Claude Code và hỏi "số liệu có gì bất thường không?". Ổn thì commit.

## Bước 5 — Các thí nghiệm chính thức

Sáu thí nghiệm, mỗi cái trả lời một câu hỏi. TN1–TN3 là bắt buộc; TN4–TN5 giúp phần giải thích sâu hơn; TN6 là điểm cộng.

| TN | Câu hỏi | Dữ liệu | CUTOFF | Trials | Mức độ |
| --- | --- | --- | --- | --- | --- |
| 1 | Cutoff nào nhanh nhất, có đổi theo N không? | random, N = 10^4, 10^5, 10^6, 10^7 | 0–30, 40, 50, 64 | 30 (N = 10^7: 10) | Bắt buộc |
| 2 | Phân bố dữ liệu có làm dịch điểm tối ưu không? | sorted, reversed, nearly, fewdistinct, N = 10^6 | 0–30, 40, 50, 64 | 20 | Bắt buộc |
| 3 | Vì sao có điểm tối ưu? (đếm số phép so sánh) | random, N = 10^6 | 0–64 | 3 | Bắt buộc |
| 4 | Insertion sort nhanh hơn mergesort đến độ dài nào? | mảng random độ dài n = 2–64 | insertionSort so với Merge.sort cutoff 0 | 30, đo theo lô | Nên làm |
| 5 | Cutoff chỉ đổi hằng số, không đổi bậc tăng (doubling test, chủ đề 1.3) | random, N = 2^17 → 2^23 | 0, 7, 10, tốt nhất từ TN1 | 10 | Nên làm |
| 6 | Phép so sánh đắt hơn thì cutoff tối ưu đổi thế nào? | Integer[] hoặc String[], N = 10^6 | 0–30, 40, 64 | 20 | Tùy chọn |

Ghi chú: TN4 gọi `Merge.sort` trên mảng rất nhỏ nên tính cả chi phí cấp phát `aux`; ghi chú điều này trong báo cáo. TN6 cần `MergeGeneric.java` do bạn tự viết ở Bước 1.

Điều kiện khi chạy:

- Cắm sạc, bật chế độ hiệu năng cao, tắt trình duyệt và các ứng dụng nặng.
- Không dùng máy trong lúc chạy; có thể để chạy qua đêm.
- Nếu máy nóng, cho nghỉ vài phút giữa các thí nghiệm.
- Chạy lại TN1 lần hai vào thời điểm khác (ví dụ hôm sau). Hai lần cho kết quả giống nhau là bằng chứng mạnh trong báo cáo.

Prompt mẫu:

```
Đọc CLAUDE.md. Viết scripts/run_all.sh chạy lần lượt TN1–TN5 theo bảng sau:
[dán bảng thí nghiệm]
Mỗi TN là một tiến trình JVM riêng với -Xms4g -Xmx4g. CSV ghi vào results/ có timestamp,
log ghi ra results/run_<timestamp>.log.
TN3 dùng MergeCount và ghi số phép so sánh thay cho thời gian.
TN4 cần thêm src/SmallBench.java, gọi Merge.insertionSort và Merge.sort.
```

Ước tính thời gian máy chạy khoảng 1–2 giờ; pilot ở Bước 4 cho con số chính xác hơn. Chạy xong thì commit toàn bộ CSV thô.

## Bước 6 — Phân tích thống kê và đồ thị

Kết quả quan trọng nhất của bước này là xác định **vùng tối ưu**, cùng câu trả lời 7 và 10 có khác nhau thật không. Một con số tốt nhất đơn lẻ là chưa đủ.

Thống kê cho mỗi tổ hợp (TN, phân bố, N, cutoff):

- Median, mean, độ lệch chuẩn, khoảng tin cậy 95% của mean (phân phối t), min. Dùng median làm số chính vì nó ít bị ảnh hưởng bởi lần đo bất thường.
- Chuẩn hóa: tỉ lệ T(cutoff) / T(0). Phần trăm cải thiện bằng 1 trừ tỉ lệ này.
- Cutoff tốt nhất: cutoff có median nhỏ nhất.
- Vùng tối ưu: các cutoff có median chênh không quá 2% so với cutoff tốt nhất. Đây là đáy phẳng của đường cong chữ U.
- So sánh 7 với 10 (và với cutoff tốt nhất): chênh lệch %, kiểm định Mann-Whitney U hoặc Welch t-test. Nếu p > 0,05 thì không đủ bằng chứng để nói hai giá trị khác nhau.

Đồ thị cần vẽ:

1. **TN1 (hình chính)**: T(c)/T(0) theo cutoff, mỗi N một đường, có error bar CI 95%, đường dọc đánh dấu 7 và 10.
2. **TN2**: tương tự, mỗi phân bố một đường.
3. **TN3**: số phép so sánh chia N log₂N theo cutoff, đặt cạnh đồ thị thời gian. Hình này cho thấy số so sánh tăng mà thời gian vẫn giảm, tức là chi phí đệ quy và copy mới là thứ được tiết kiệm.
4. **TN4**: thời gian insertion sort và mergesort theo n, chỉ ra điểm giao nhau.
5. **TN5**: log-log của T theo N, độ dốc xấp xỉ 1; kèm tỉ lệ doubling T(2N)/T(N).
6. **TN6** (nếu làm): đường `int[]` so với `Integer[]`.

Bảng cần lập:

- Bảng A: cutoff tốt nhất, vùng tối ưu, % cải thiện so với không cutoff, theo N (TN1) và theo phân bố (TN2).
- Bảng B: cutoff 0, 7, 10 và tốt nhất, với median, CI 95% và p-value của cặp 7–10.
- Bảng C: tỉ lệ doubling của TN5.

Prompt mẫu:

```
Đọc CLAUDE.md. Viết scripts/analyze.py:
- Đọc toàn bộ CSV trong results/, tính các thống kê sau: [dán danh sách thống kê ở trên].
- Xuất bảng A, B, C ra tables/*.csv và tables/*.md.
- Vẽ các đồ thị [dán danh sách đồ thị] ra figures/*.png, dpi 200.
- Nhãn trục và tiêu đề bằng tiếng Việt, ghi rõ đơn vị (ms, số phép so sánh).
```

Thứ tự làm việc: tự xem đồ thị trước, tự viết nhận xét của bạn, rồi mới hỏi Claude Code "nhận xét của tôi có khớp với số liệu không?". Đây cũng là cách luyện phần phân tích thuật toán cho kỳ thi.

## Bước 7 — Viết báo cáo

Báo cáo phải kết thúc bằng một câu trả lời trực tiếp: trên máy của bạn, CUTOFF nên là bao nhiêu (hoặc khoảng nào), và 7 hay 10 tốt hơn. Dàn ý gợi ý:

1. **Giới thiệu**: bài toán, câu hỏi 7 hay 10, mục tiêu thí nghiệm.
2. **Cơ sở lý thuyết**: vì sao cutoff giúp.
    - Insertion sort cần khoảng N²/4 phép so sánh nhưng hằng số nhỏ, không đệ quy, dữ liệu nằm gọn trong cache.
    - Mergesort trên đoạn nhỏ tốn chi phí gọi hàm và copy sang `aux`.
    - Dự đoán: thời gian theo cutoff có dạng chữ U.
3. **Cài đặt**: mô tả Merge.java (trích đoạn code chính), quy ước CUTOFF, các cải tiến bật hoặc tắt, cách kiểm tra tính đúng.
4. **Môi trường**: bảng cấu hình máy, JDK, JVM flags, điều kiện khi chạy.
5. **Thiết kế thí nghiệm**: bảng TN1–TN6, bộ dữ liệu, phương pháp đo (warm-up, đo theo lô, trial, thứ tự ngẫu nhiên), các thống kê dùng.
6. **Kết quả**: đồ thị và bảng của từng TN; mỗi hình kèm 2–3 câu nhận xét.
7. **Thảo luận**:
    - Cutoff tối ưu và vùng tối ưu.
    - Có phụ thuộc N, phân bố dữ liệu, kiểu phần tử không?
    - 7 và 10 có khác biệt có ý nghĩa thống kê không?
    - Giải thích cơ chế bằng TN3 và TN4; liên hệ chủ đề 1.3 qua doubling test.
8. **Hạn chế**: chỉ đo trên một máy, nhiễu hệ điều hành, ảnh hưởng của JIT; máy khác có thể cho kết quả khác.
9. **Kết luận**: giá trị hoặc khoảng CUTOFF đề xuất cho máy của bạn.
10. **Phụ lục**: hướng dẫn chạy lại, cấu trúc thư mục.

Về dùng AI khi viết: tự viết phần Thảo luận và Kết luận. Nhờ Claude góp ý lập luận và kiểm tra số liệu trích dẫn có khớp bảng không. Thêm một đoạn ngắn "Sử dụng AI" nói rõ AI đã hỗ trợ những phần nào; như vậy minh bạch và đúng yêu cầu đề.

Câu hỏi mở: cô có yêu cầu định dạng báo cáo (Word, PDF, mẫu riêng) không? Nếu không, có thể viết Markdown trong `report/` rồi xuất PDF.

## Bước 8 — Đóng gói và nộp

Gói nộp gồm ba phần theo đề: báo cáo, code và script, bộ dữ liệu. Nhờ Claude Code viết `README.md` gồm: yêu cầu môi trường, lệnh biên dịch, lệnh sinh dữ liệu, lệnh chạy từng thí nghiệm, lệnh phân tích.

Checklist trước khi nộp:

- [ ] Merge.java tự viết, có comment, qua toàn bộ test
- [ ] Bộ dữ liệu: file thật cho N ≤ 10^6, generator + seed + SHA-256 cho file lớn
- [ ] CSV thô của mọi thí nghiệm, kể cả lần chạy lặp lại TN1
- [ ] File machine.txt ghi cấu hình máy và JVM flags
- [ ] Chạy thử lại từ đầu: clone repo ra thư mục mới, làm theo README, xem có chạy được không
- [ ] Đồ thị và bảng trong báo cáo khớp với file trong figures/ và tables/
- [ ] Báo cáo có kết luận trả lời trực tiếp câu hỏi của đề
- [ ] Có đoạn ghi chú sử dụng AI
- [ ] Nén thư mục, đặt tên theo quy định của cô (ví dụ MSSV_HoTen_MergesortCutoff.zip)
