"""Bảng G và hình 6: kích thước đoạn lá của cây đệ quy theo cutoff (bổ sung cho Bước 6).

Cách chạy (từ thư mục gốc, sau scripts/analyze.py vì cần tables/thong_ke_day_du.csv):
    .venv/bin/python scripts/leaf_sizes.py

Ý tưởng: Merge.sort chia đoạn độ dài L thành hai nửa ceil(L/2) và floor(L/2) (mid = lo + (hi - lo) / 2)
cho đến khi L <= cutoff (insertion sort) hoặc L <= 1. Với một N cố định, nhiều cutoff liền nhau sinh ra
CÙNG một cây đệ quy, nên chạy giống hệt nhau. Script này chỉ mô phỏng phép chia độ dài đoạn
(không sắp xếp gì, không gọi Merge.java) để biết mỗi cutoff ứng với đoạn lá dài bao nhiêu
và còn bao nhiêu tầng merge, rồi ghép với thời gian đo được ở TN1, TN2.

Đầu ra:
    tables/G_kich_thuoc_doan_la.csv   mọi (TN, phân bố, N, cutoff): lá nhỏ nhất/lớn nhất, số lá, số tầng merge,
                                      median thời gian, T(c)/T(0), thời gian tiết kiệm mỗi phần tử
    tables/G_kich_thuoc_doan_la.md    TN1, mỗi dòng là một nhóm cutoff cho cùng một cây đệ quy
    figures/tn1_tiet_kiem_theo_kich_thuoc_la.png
"""
import sys
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import FixedLocator, NullLocator

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze import (MAU_TRUC, RAMP_N, DAU, TABLES, gop_khoang, kieu_chung, luu,  # noqa: E402
                     ten_N, ten_N_hinh, tieu_de, ve_duong)


def cay_de_quy(n, cutoff):
    """Độ dài các đoạn lá (Counter: độ dài -> số đoạn) và số tầng merge của Merge.sort(a, cutoff), a.length = n."""
    la, tang, muc = Counter(), 0, {n: 1}
    while muc:
        tiep = Counter()
        for L, k in muc.items():
            if L <= 1 or L <= cutoff:
                la[L] += k
            else:
                tiep[(L + 1) // 2] += k
                tiep[L // 2] += k
        if tiep:
            tang += 1
        muc = tiep
    return la, tang


def bang_G(d):
    dong = []
    for (tn, dist, n), g in d[d.tn.isin(["tn1", "tn2"])].groupby(["tn", "dist", "n"]):
        g = g.set_index("cutoff")
        t0 = g.loc[0, "median_ms"]
        for c, r in g.iterrows():
            la, tang = cay_de_quy(int(n), int(c))
            dong.append(dict(tn=tn, dist=dist, n=int(n), cutoff=int(c), la_min=min(la), la_max=max(la),
                             so_la=sum(la.values()), la_tb=n / sum(la.values()), so_tang_merge=tang,
                             median_ms=r.median_ms, ti_le=r.ti_le,
                             tiet_kiem_ns_moi_pt=(t0 - r.median_ms) * 1e6 / n))
    return pd.DataFrame(dong)


def nhom_cay(g):
    """Gộp các cutoff liền nhau cho cùng một cây (cùng số lá và cùng lá nhỏ nhất/lớn nhất)."""
    g = g.sort_values("cutoff").copy()
    g["nhom"] = (g[["so_la", "la_min", "la_max"]].diff().abs().sum(axis=1) != 0).cumsum()
    return g.groupby("nhom").agg(c_dau=("cutoff", "min"), c_cuoi=("cutoff", "max"), cac_c=("cutoff", list),
                                 la_min=("la_min", "first"), la_max=("la_max", "first"), la_tb=("la_tb", "first"),
                                 tang=("so_tang_merge", "first"), tl_min=("ti_le", "min"), tl_max=("ti_le", "max"),
                                 tk=("tiet_kiem_ns_moi_pt", "median"))


def ghi_G(G):
    G.to_csv(TABLES / "G_kich_thuoc_doan_la.csv", index=False, float_format="%.6g")
    dong = ["# Bảng G: kích thước đoạn lá của cây đệ quy theo cutoff (TN1, random)", "",
            "- Đoạn lá: đoạn được insertion sort (độ dài ≤ cutoff), hoặc đoạn 1 phần tử khi cutoff ≤ 1. "
            "Tính bằng cách mô phỏng phép chia mid = lo + (hi − lo) / 2 của Merge.sort, không đo gì thêm.",
            "- Mỗi dòng là một nhóm cutoff liền nhau (trong số các cutoff đã đo) cho CÙNG một cây đệ quy: "
            "cùng đoạn lá, cùng số tầng merge, nên chạy giống hệt nhau.",
            "- T(c)/T(0): median, ghi min–max trong nhóm. Tiết kiệm = (T(0) − T(c)) / N, median trong nhóm, "
            "đơn vị ns cho mỗi phần tử.",
            "- TN5 dùng N = 2^k nên mọi đoạn lá dài đúng bằng lũy thừa của 2 lớn nhất ≤ cutoff: "
            "cutoff 7 → lá 4, cutoff 10 → lá 8, cutoff 40 → lá 32.", "",
            "| N | các cutoff (cùng cây) | độ dài đoạn lá | số tầng merge | T(c)/T(0) | tiết kiệm (ns/phần tử) |",
            "|---:|---|---|---:|---|---:|"]
    for n, g in G[G.tn == "tn1"].groupby("n"):
        for _, r in nhom_cay(g).iterrows():
            ten_c = gop_khoang(r.cac_c)
            la = str(r.la_min) if r.la_min == r.la_max else f"{r.la_min}–{r.la_max}"
            tl = f"{r.tl_min:.3f}" if round(r.tl_min, 3) == round(r.tl_max, 3) else f"{r.tl_min:.3f}–{r.tl_max:.3f}"
            dong.append(f"| {ten_N(n)} | {ten_c} | {la} | {r.tang} | {tl} | {0.0 if abs(r.tk) < 0.05 else r.tk:.1f} |")
    dong += ["", "Nguồn: `tables/thong_ke_day_du.csv` (TN1, từ `results/tn1_random_*_20261120_134812.csv`)", ""]
    (TABLES / "G_kich_thuoc_doan_la.md").write_text("\n".join(dong), encoding="utf-8")


def hinh_6(G):
    fig, ax = plt.subplots(figsize=(7.4, 4.6))
    tn1 = G[G.tn == "tn1"]
    for i, (n, g) in enumerate(tn1.groupby("n")):
        k = nhom_cay(g)
        k = k[k.c_cuoi >= 2]                     # bỏ nhóm cutoff 0–1 (không có insertion sort, tiết kiệm = 0)
        ve_duong(ax, k.la_tb, k.tk, mau=RAMP_N[i], dau=DAU[i], nhan=f"N = {ten_N_hinh(n)}")
    ax.axhline(0, color=MAU_TRUC, linewidth=0.9, zorder=1)
    ax.set_xscale("log", base=2)
    vach = [1, 2, 4, 8, 16, 32, 64, 128]
    ax.xaxis.set_major_locator(FixedLocator(vach))
    ax.xaxis.set_minor_locator(NullLocator())
    ax.set_xticklabels([str(v) for v in vach])
    ax.set_xlim(1.2, 150)
    ax.set_ylim(0, 18)
    ax.set_xlabel("độ dài trung bình của đoạn lá = N / số đoạn lá (thang log)")
    ax.set_ylabel("thời gian tiết kiệm (ns / phần tử)")
    tieu_de(fig, "TN1 · Thời gian tiết kiệm so với cutoff 0, theo độ dài đoạn lá",
            "Tiết kiệm = (T(0) − T(c)) / N, với T là median thời gian một lần sort. Mỗi điểm là một nhóm cutoff cho\n"
            "cùng một cây đệ quy (median trong nhóm). Độ dài đoạn lá tính từ phép chia của Merge.sort, không đo thêm.")
    fig.legend(*ax.get_legend_handles_labels(), loc="lower center", ncol=4, bbox_to_anchor=(0.5, 0.0))
    fig.tight_layout(rect=(0, 0.06, 1, 0.86))
    return luu(fig, "tn1_tiet_kiem_theo_kich_thuoc_la.png")


def main():
    p = TABLES / "thong_ke_day_du.csv"
    if not p.exists():
        sys.exit(f"thiếu {p}: chạy scripts/analyze.py trước")
    kieu_chung()
    G = bang_G(pd.read_csv(p))
    ghi_G(G)
    hinh_6(G)
    print("Đã ghi tables/G_kich_thuoc_doan_la.{csv,md} và figures/tn1_tiet_kiem_theo_kich_thuoc_la.png")


if __name__ == "__main__":
    main()
