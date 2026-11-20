# Số liệu bị loại: hai đợt đo chạy chồng nhau (20/11/2026)

Dữ liệu thô bị nhiễu được chuyển nguyên vẹn vào thư mục này, không sửa nội dung. **Không dùng các file này khi phân tích.**
Các file dữ liệu chỉ giữ trên máy đo, không đưa lên git (xem `.gitignore`); trên git chỉ có file ghi chú này.

## Chuyện gì đã xảy ra

| Thời điểm | Sự kiện |
|---|---|
| 13:13:04 | Đợt 1 (`run_all.sh`, TN1–TN5, timestamp 131304) bắt đầu |
| 13:18:19 | Đợt 2 (`run_all.sh tn1`, timestamp 131819) được chạy ở một tab terminal khác trong khi đợt 1 chưa xong |
| 13:26:42 | Đợt 2 ghi dòng cuối, sau đó bị dừng bằng Ctrl+C trong trial 10/10 của N = 10^7 |
| 13:48:12 | Đợt 3 (`run_all.sh tn1 tn2`, timestamp 134812) chạy lại TN1 và TN2 một mình |

Hai JVM đo cùng lúc tranh nhau cache L2, băng thông bộ nhớ và nhiệt của máy (MacBook Air M2 không có quạt).
Bằng chứng ở đợt 1, TN1 N = 10^7, thời gian mỗi trial:

- trial 1–3 (chạy một mình): 32,6–32,8 s;
- trial 4–10 (chạy chồng với đợt 2): 33,3–33,9 s, tức chậm khoảng 2,5%.

Mức chậm này lớn hơn độ nhiễu đo (0,5–1,5%), đủ để đảo thứ hạng các cutoff gần nhau.

## Các file bị loại (19 file, chỉ có trên máy đo)

| File | Lý do loại |
|---|---|
| `tn1_random_{10000,100000,1000000,10000000}_20261120_131819.*` | Đợt 2: chạy chồng với đợt 1 toàn bộ thời gian. File N = 10^7 dừng giữa chừng (`status=đang chạy`, 333/370 phép đo) |
| `run_20261120_131819.log` | Log của đợt 2 |
| `tn2_{sorted,reversed,nearly,fewdistinct}_1000000_20261120_131304.*` | Đợt 1, TN2: chạy từ 13:23:52 đến 13:25:57, nằm trọn trong lúc đợt 2 đang đo |
| `tn1_random_10000000_20261120_131304.*` | Đợt 1, TN1 N = 10^7: trial 4–10 chạy chồng. Trial 1–3 sạch nhưng không dùng, vì đợt 3 đã có đủ 10 trial sạch |

## Dữ liệu sạch dùng để phân tích (nằm ở `results/`)

| TN | File |
|---|---|
| TN1 | `tn1_random_*_20261120_134812.csv`: đủ 4 cỡ N (lần chạy chính) |
| TN1 lặp lại | `tn1_random_{10000,100000,1000000}_20261120_131304.csv`: lần chạy thứ hai, dùng để kiểm tra độ lặp lại |
| TN2 | `tn2_*_1000000_20261120_134812.csv` |
| TN3, TN4, TN5 | `tn3_*`, `tn4_*`, `tn5_*` có timestamp `20261120_131304`: chạy sau khi đợt 2 đã dừng |

`run_20261120_131304.log` vẫn để ở `results/` vì phần TN3–TN5 trong đó sạch. Riêng phần TN1 N = 10^7 và TN2 trong log này thuộc khoảng chạy chồng.

## Ảnh hưởng tới TN5

TN5 tự chọn "cutoff tốt nhất của TN1" từ file TN1 N = 10^6 mới nhất lúc nó chạy. File đó là file bị nhiễu của đợt 2, nên TN5 dùng cutoff **40**.
Theo file sạch, cutoff tốt nhất là **50** (70,39 ms), còn 40 chỉ chậm hơn 0,06 ms (70,45 ms, tức 0,09%), nhỏ hơn nhiều so với độ nhiễu đo.
Ở đợt 3, cutoff tốt nhất lại là 40. Vì vậy TN5 được giữ nguyên, không chạy lại.

## Bài học

Mỗi lúc chỉ chạy một lệnh đo, và không dùng máy trong lúc đo.
