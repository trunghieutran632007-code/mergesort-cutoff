# Bảng A: cutoff tốt nhất và vùng tối ưu

- Cutoff tốt nhất: cutoff có median nhỏ nhất. Cải thiện = 1 − median(tốt nhất) / median(cutoff 0).
- Vùng tối ưu: các cutoff có median chênh không quá 2% so với cutoff tốt nhất (chỉ gộp thành khoảng a–b khi các cutoff liên tiếp đều được đo).
- Đo lệch: số phép đo chậm hơn median của cùng cutoff quá 10% / tổng số phép đo (không bị loại).
- Dòng "random (TN1)" ở nhóm TN2 lấy từ TN1, N = 10⁶, để so với các phân bố khác.

| TN | phân bố | N | trial | median cutoff 0 (ms) | cutoff tốt nhất | median tốt nhất (ms) | T(tốt nhất)/T(0) | cải thiện | vùng tối ưu (≤ 2%) | đo lệch |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|---:|
| TN1 | random | 10⁴ | 30 | 0.5542 | 40 | 0.4039 | 0.729 | 27.1% | 40, 50, 64 | 10/1110 |
| TN1 | random | 10⁵ | 30 | 7.283 | 64 | 5.702 | 0.783 | 21.7% | 25–30, 40, 50, 64, 80, 96 | 8/1110 |
| TN1 | random | 10⁶ | 30 | 85.95 | 40 | 70.92 | 0.825 | 17.5% | 30, 40, 50, 64, 80, 96 | 4/1110 |
| TN1 | random | 10⁷ | 10 | 992.3 | 40 | 836.2 | 0.843 | 15.7% | 19–30, 40, 50, 64, 80, 96, 128 | 0/370 |
| TN2 | random (TN1) | 10⁶ | 30 | 85.95 | 40 | 70.92 | 0.825 | 17.5% | 30, 40, 50, 64, 80, 96 | 4/1110 |
| TN2 | sorted | 10⁶ | 20 | 29.81 | 128 | 17.32 | 0.581 | 41.9% | 128 | 3/740 |
| TN2 | reversed | 10⁶ | 20 | 27.08 | 10 | 22.09 | 0.816 | 18.4% | 7–14 | 1/740 |
| TN2 | nearly | 10⁶ | 20 | 31.59 | 128 | 18.91 | 0.599 | 40.1% | 128 | 5/740 |
| TN2 | fewdistinct | 10⁶ | 20 | 47.27 | 40 | 32.37 | 0.685 | 31.5% | 40, 50 | 1/740 |

Nguồn: `results/tn1_random_10000_20261120_134812.csv`, `results/tn1_random_100000_20261120_134812.csv`, `results/tn1_random_1000000_20261120_134812.csv`, `results/tn1_random_10000000_20261120_134812.csv`, `results/tn2_sorted_1000000_20261120_134812.csv`, `results/tn2_reversed_1000000_20261120_134812.csv`, `results/tn2_nearly_1000000_20261120_134812.csv`, `results/tn2_fewdistinct_1000000_20261120_134812.csv`
