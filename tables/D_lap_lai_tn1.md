# Bảng D: độ lặp lại của TN1 giữa các lần chạy

- Lần chạy chính: file mới nhất (dùng cho mọi bảng và hình khác). Lần lặp lại: các file cũ hơn.
- Lệch median: median(lần lặp lại) / median(lần chính) − 1, tính cho từng cutoff; ghi min / trung bình / max.

| N | lần chạy | vai trò | cutoff tốt nhất | median tốt nhất (ms) | cải thiện | vùng tối ưu (≤ 2%) | lệch median min / TB / max |
|---:|---|---|---:|---:|---:|---|---:|
| 10⁴ | 20261120_134812 | chính | 40 | 0.4039 | 27.1% | 40, 50, 64 | — |
| 10⁴ | 20261120_131304 | lặp lại | 50 | 0.4068 | 26.2% | 40, 50, 64 | -0.85% / +0.66% / +1.78% |
| 10⁵ | 20261120_134812 | chính | 64 | 5.702 | 21.7% | 25–30, 40, 50, 64, 80, 96 | — |
| 10⁵ | 20261120_131304 | lặp lại | 64 | 5.689 | 21.6% | 25–30, 40, 50, 64, 80, 96 | -0.88% / -0.51% / -0.24% |
| 10⁶ | 20261120_134812 | chính | 40 | 70.92 | 17.5% | 30, 40, 50, 64, 80, 96 | — |
| 10⁶ | 20261120_131304 | lặp lại | 50 | 70.39 | 17.6% | 30, 40, 50, 64, 80, 96 | -1.07% / -0.71% / -0.20% |

Nguồn: `results/tn1_random_10000_20261120_134812.csv`, `results/tn1_random_10000_20261120_131304.csv`, `results/tn1_random_100000_20261120_134812.csv`, `results/tn1_random_100000_20261120_131304.csv`, `results/tn1_random_1000000_20261120_134812.csv`, `results/tn1_random_1000000_20261120_131304.csv`
