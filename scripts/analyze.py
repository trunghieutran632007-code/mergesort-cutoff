#!/usr/bin/env python3
"""Bước 6: thống kê và vẽ đồ thị từ kết quả đo TN1–TN5 (results/tn*.csv).

Cách chạy (từ thư mục gốc):
    .venv/bin/python scripts/analyze.py                   error bar = CI 95% của median (mặc định)
    .venv/bin/python scripts/analyze.py --errorbar mean   error bar = CI 95% của mean (phân phối t)

Đầu vào: results/tn<1-5>_<phân bố>_<N hoặc small>_<yyyyMMdd_HHmmss>.csv. Không đọc file pilot_* và các thư mục
con (results/bi-chay-chong/). Với mỗi (TN, phân bố, N) có nhiều lần chạy, file mới nhất là số liệu chính; các lần
cũ hơn của TN1 chỉ dùng cho bảng D (độ lặp lại). File có .meta.txt mà status khác ok thì dừng.

Đầu ra (ghi đè mỗi lần chạy, vì tạo lại được hoàn toàn từ results/):
    tables/thong_ke_day_du.csv              mọi thống kê theo (TN, phân bố, N, cutoff)
    tables/A_cutoff_toi_uu.{csv,md}         cutoff tốt nhất, vùng tối ưu, % cải thiện (TN1 theo N, TN2 theo phân bố)
    tables/B1_median_0_7_10.{csv,md}        median và CI 95% của cutoff 0, 7, 10 và tốt nhất
    tables/B2_kiem_dinh_7_10.{csv,md}       chênh lệch % và p-value của các cặp 7–10, 7–tốt nhất, 10–tốt nhất
    tables/C_doubling_tn5.{csv,md}          TN5: T(N), T(N)/T(N/2), độ dốc log-log
    tables/D_lap_lai_tn1.{csv,md}           TN1: so sánh các lần chạy
    tables/E_tn3_so_phep_so_sanh.{csv,md}   TN3: số phép so sánh, đặt cạnh thời gian của TN1 cùng dữ liệu
    tables/F_tn4_insertion_merge.{csv,md}   TN4: insertion so với merge theo n, điểm giao nhau
    figures/tn1_*.png ... figures/tn5_*.png (dpi 200)

Quy ước thống kê:
- Số chính là median (ít bị ảnh hưởng bởi phép đo bất thường). Tỉ lệ T(c)/T(0) = median(c) / median(0);
  % cải thiện = (1 - tỉ lệ) x 100.
- Cutoff tốt nhất = cutoff có median nhỏ nhất. Vùng tối ưu = các cutoff có median <= 1.02 x median tốt nhất.
- CI 95% của mean theo phân phối t. CI 95% của median theo thống kê thứ tự (không giả định dạng phân phối):
  30 trial thì lấy giá trị thứ 10 và thứ 21 sau khi sắp xếp, 20 trial lấy thứ 6 và 15, 10 trial lấy thứ 2 và 9.
- Mỗi trial đo mọi cutoff đúng một lần (thứ tự trộn), nên tỉ lệ T(c)/T(0) còn được tính trong từng trial (so theo
  cặp, nhiễu chung của trial triệt tiêu). Đồ thị vẽ median của tỉ lệ này, error bar là CI 95% của nó.
  TN4 làm tương tự với tỉ lệ merge / insertion.
- So sánh hai cutoff: Mann-Whitney U (kiểm định chính, dựa trên thứ hạng) và Welch t-test (đối chiếu), hai phía.
- Phép đo "lệch" = chậm hơn median của cùng cutoff quá 10%. Không loại bỏ phép đo nào.
Script chỉ tính số liệu và vẽ hình, không viết nhận xét.
"""
import argparse
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FixedLocator, FuncFormatter, NullLocator  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
TABLES = ROOT / "tables"
FIGURES = ROOT / "figures"

VUNG_TOI_UU = 0.02        # vùng tối ưu: median chênh không quá 2% so với cutoff tốt nhất
NGUONG_LECH = 0.10        # phép đo lệch: chậm hơn median cùng cutoff quá 10%
MUC_TIN_CAY = 0.95
MUC_Y_NGHIA = 0.05
DPI = 200
CUTOFF_SO_SANH = (7, 10)
THU_TU_PHAN_BO = ["random", "sorted", "reversed", "nearly", "fewdistinct"]
TICK_CUTOFF = [0, 5, 10, 15, 20, 25, 30, 40, 50, 64, 80, 96, 128]
N_HIEN_THI_TN4 = [2, 3, 4, 5, 6, 8, 10, 12, 16, 20, 24, 32, 40, 48, 64, 80, 96, 112, 128, 160, 192, 256]

# Màu: bảng màu tham chiếu đã kiểm tra mù màu (scripts/validate_palette.js của skill dataviz, nền trắng).
# Phân loại theo thứ tự cố định: màu đi theo đối tượng, không theo thứ hạng. N có thứ tự nên dùng một dải xanh.
MAU_PHAN_LOAI = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
MAU_PHAN_BO = dict(zip(THU_TU_PHAN_BO, MAU_PHAN_LOAI))
DAU_PHAN_BO = dict(zip(THU_TU_PHAN_BO, ["o", "s", "^", "D", "v"]))
RAMP_N = ["#6da7ec", "#3987e5", "#1c5cab", "#0d366b"]
DAU = ["o", "s", "^", "D", "v"]
MUC_IN, MUC_PHU, MUC_NHAT = "#0b0b0b", "#52514e", "#898781"
MAU_LUOI, MAU_TRUC = "#e1e0d9", "#c3c2b7"

TEN_FILE = re.compile(r"^(tn[1-5])_([a-z]+)_(\d+|small)_(\d{8}_\d{6})\.csv$")
SO_MU = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")


# ---------------------------------------------------------------- đọc dữ liệu

def kiem_tra_meta(p):
    meta = p.with_name(p.stem + ".meta.txt")
    if not meta.exists():
        return
    for dong in meta.read_text(encoding="utf-8").splitlines():
        if dong.startswith("status="):
            st = dong.split("=", 1)[1].strip()
            if st != "ok":
                sys.exit(f"LỖI: {meta.name} có status={st} (lần chạy chưa xong hoặc lỗi). "
                         "Chuyển file này ra khỏi results/ rồi chạy lại.")


def doc_ket_qua():
    """Trả về (chính, cũ): mỗi khóa (tn, phân bố, cỡ) -> file mới nhất / danh sách file cũ hơn."""
    nhom = {}
    for p in sorted(RESULTS.glob("tn*.csv")):
        m = TEN_FILE.match(p.name)
        if not m:
            print(f"  bỏ qua file có tên không đúng mẫu: {p.name}")
            continue
        tn, dist, co, ts = m.groups()
        kiem_tra_meta(p)
        nhom.setdefault((tn, dist, co), []).append((ts, p))
    if not nhom:
        sys.exit("LỖI: không có file results/tn*.csv nào.")
    chinh, cu = {}, {}
    for khoa, ds in nhom.items():
        ds.sort()
        chinh[khoa] = ds[-1][1]
        cu[khoa] = [p for _, p in ds[:-1]]
    return chinh, cu


def thoi_diem(p):
    return TEN_FILE.match(p.name).group(4)


# ---------------------------------------------------------------- thống kê

def ci_mean(x):
    x = np.asarray(x, float)
    n = len(x)
    if n < 2:
        return np.nan, np.nan
    h = stats.t.ppf((1 + MUC_TIN_CAY) / 2, n - 1) * x.std(ddof=1) / np.sqrt(n)
    return x.mean() - h, x.mean() + h


def ci_median(x):
    """CI của median theo thống kê thứ tự: [x_(j), x_(n+1-j)], j lớn nhất sao cho độ phủ >= 95%."""
    x = np.sort(np.asarray(x, float))
    n = len(x)
    j = int(stats.binom.ppf((1 - MUC_TIN_CAY) / 2, n, 0.5))
    if j < 1:
        return np.nan, np.nan
    return x[j - 1], x[n - j]


def thong_ke_cutoff(d):
    """d: các dòng của một file TN1/TN2/TN5. Trả về (bảng thống kê theo cutoff, bảng ms theo trial x cutoff)."""
    ms = d.assign(ms=d["ns_per_sort"] / 1e6).pivot(index="trial", columns="cutoff", values="ms")
    if ms.isna().any().any():
        sys.exit("LỖI: có trial thiếu phép đo của một cutoff, không so theo cặp được.")
    ti_le = ms.div(ms[0], axis=0)
    med0 = ms[0].median()
    dong = []
    for c in ms.columns:
        x, r = ms[c].to_numpy(), ti_le[c].to_numpy()
        med = np.median(x)
        lo, hi = ci_median(x)
        mlo, mhi = ci_mean(x)
        rlo, rhi = ci_median(r)
        rmlo, rmhi = ci_mean(r)
        dong.append({
            "cutoff": int(c), "so_trial": len(x),
            "median_ms": med, "median_ci_lo": lo, "median_ci_hi": hi,
            "mean_ms": x.mean(), "sd_ms": x.std(ddof=1), "mean_ci_lo": mlo, "mean_ci_hi": mhi,
            "min_ms": x.min(),
            "ti_le": med / med0, "cai_thien_pct": (1 - med / med0) * 100,
            "ti_le_trial_median": np.median(r), "ti_le_trial_median_ci_lo": rlo, "ti_le_trial_median_ci_hi": rhi,
            "ti_le_trial_mean": r.mean(), "ti_le_trial_mean_ci_lo": rmlo, "ti_le_trial_mean_ci_hi": rmhi,
            "so_do_lech": int((x > (1 + NGUONG_LECH) * med).sum()),
        })
    s = pd.DataFrame(dong).set_index("cutoff")
    s["trong_vung_toi_uu"] = s["median_ms"] <= (1 + VUNG_TOI_UU) * s["median_ms"].min()
    return s, ms


def cutoff_tot_nhat(s):
    return int(s["median_ms"].idxmin())


def vung_toi_uu(s):
    return [int(c) for c in s.index[s["trong_vung_toi_uu"]]]


def kiem_dinh(a, b):
    p_mwu = stats.mannwhitneyu(a, b, alternative="two-sided").pvalue
    p_welch = stats.ttest_ind(a, b, equal_var=False).pvalue
    return float(p_mwu), float(p_welch)


# ---------------------------------------------------------------- định dạng

def ten_N(n):
    n = int(n)
    for co_so in (10, 2):
        k = round(np.log(n) / np.log(co_so))
        if co_so ** k == n and k > 1:
            return f"{co_so}{str(k).translate(SO_MU)}"
    return str(n)


def ten_N_hinh(n):
    n = int(n)
    for co_so in (10, 2):
        k = round(np.log(n) / np.log(co_so))
        if co_so ** k == n and k > 1:
            return f"${co_so}^{{{k}}}$"
    return str(n)


def gop_khoang(cs):
    """[16,17,...,29,40,50] -> '16–29, 40, 50' (chỉ gộp các số nguyên liên tiếp)."""
    cs = sorted(int(c) for c in cs)
    phan, i = [], 0
    while i < len(cs):
        j = i
        while j + 1 < len(cs) and cs[j + 1] == cs[j] + 1:
            j += 1
        phan.append(f"{cs[i]}–{cs[j]}" if j - i >= 2 else ", ".join(str(c) for c in cs[i:j + 1]))
        i = j + 1
    return ", ".join(phan)


def f_ms(v):
    """4 chữ số có nghĩa, giữ số 0 ở cuối (0.4440); từ 1000 trở lên thì làm tròn đến hàng đơn vị."""
    return f"{v:.0f}" if abs(v) >= 1000 else f"{v:#.4g}"


def f_ci(med, lo, hi):
    return f"{f_ms(med)} [{f_ms(lo)}, {f_ms(hi)}]"


def f_p(p):
    return "< 0.001" if p < 0.001 else f"{p:.3f}"


def ghi_bang(ten, df, tieu_de, mo_ta, cot_md, dong_md, can_phai, nguon):
    """Ghi tables/<ten>.csv (số đầy đủ) và tables/<ten>.md (số đã làm tròn)."""
    df.to_csv(TABLES / f"{ten}.csv", index=False, float_format="%.6g")
    can = ["---:" if c else "---" for c in can_phai]
    dong = [f"# {tieu_de}", "", *mo_ta, "",
            "| " + " | ".join(cot_md) + " |", "|" + "|".join(can) + "|"]
    dong += ["| " + " | ".join(str(v) for v in d) + " |" for d in dong_md]
    dong += ["", "Nguồn: " + ", ".join(f"`results/{p.name}`" for p in nguon), ""]
    (TABLES / f"{ten}.md").write_text("\n".join(dong), encoding="utf-8")
    return [TABLES / f"{ten}.csv", TABLES / f"{ten}.md"]


# ---------------------------------------------------------------- bảng

def bang_day_du(cau_hinh):
    phan = []
    for ch in cau_hinh:
        s = ch["s"].reset_index()
        s.insert(0, "file", ch["file"].name)
        s.insert(0, "n", ch["n"])
        s.insert(0, "dist", ch["dist"])
        s.insert(0, "tn", ch["tn"])
        phan.append(s)
    df = pd.concat(phan, ignore_index=True)
    df.to_csv(TABLES / "thong_ke_day_du.csv", index=False, float_format="%.6g")
    return [TABLES / "thong_ke_day_du.csv"]


def bang_A(tn1, tn2):
    dong_csv, dong_md, nguon = [], [], []
    tham_chieu = [ch for ch in tn1 if ch["n"] == 1_000_000]
    nhom = [("TN1", ch, "random") for ch in tn1] + \
           [("TN2", ch, "random (TN1)") for ch in tham_chieu] + [("TN2", ch, ch["dist"]) for ch in tn2]
    for tn, ch, nhan in nhom:
        s = ch["s"]
        best = cutoff_tot_nhat(s)
        vung = vung_toi_uu(s)
        dong_csv.append({
            "tn": tn, "dist": nhan, "n": ch["n"], "so_trial": int(s["so_trial"].iloc[0]),
            "median_cutoff0_ms": s.at[0, "median_ms"], "cutoff_tot_nhat": best,
            "median_tot_nhat_ms": s.at[best, "median_ms"], "ti_le_tot_nhat": s.at[best, "ti_le"],
            "cai_thien_pct": s.at[best, "cai_thien_pct"], "vung_toi_uu": gop_khoang(vung),
            "so_cutoff_trong_vung": len(vung), "so_do_lech": int(s["so_do_lech"].sum()),
            "so_phep_do": int(s["so_trial"].sum()), "file": ch["file"].name,
        })
        dong_md.append([tn, nhan, ten_N(ch["n"]), int(s["so_trial"].iloc[0]), f_ms(s.at[0, "median_ms"]), best,
                        f_ms(s.at[best, "median_ms"]), f"{s.at[best, 'ti_le']:.3f}",
                        f"{s.at[best, 'cai_thien_pct']:.1f}%", gop_khoang(vung),
                        f"{int(s['so_do_lech'].sum())}/{int(s['so_trial'].sum())}"])
        if ch["file"] not in nguon:
            nguon.append(ch["file"])
    mo_ta = [
        "- Cutoff tốt nhất: cutoff có median nhỏ nhất. Cải thiện = 1 − median(tốt nhất) / median(cutoff 0).",
        f"- Vùng tối ưu: các cutoff có median chênh không quá {VUNG_TOI_UU:.0%} so với cutoff tốt nhất "
        "(chỉ gộp thành khoảng a–b khi các cutoff liên tiếp đều được đo).",
        f"- Đo lệch: số phép đo chậm hơn median của cùng cutoff quá {NGUONG_LECH:.0%} / tổng số phép đo "
        "(không bị loại).",
        "- Dòng \"random (TN1)\" ở nhóm TN2 lấy từ TN1, N = 10⁶, để so với các phân bố khác.",
    ]
    cot = ["TN", "phân bố", "N", "trial", "median cutoff 0 (ms)", "cutoff tốt nhất", "median tốt nhất (ms)",
           "T(tốt nhất)/T(0)", "cải thiện", "vùng tối ưu (≤ 2%)", "đo lệch"]
    return ghi_bang("A_cutoff_toi_uu", pd.DataFrame(dong_csv), "Bảng A: cutoff tốt nhất và vùng tối ưu", mo_ta,
                    cot, dong_md, [0, 0, 1, 1, 1, 1, 1, 1, 1, 0, 1], nguon)


def bang_B(cau_hinh):
    b1_csv, b1_md, b2_csv, b2_md, nguon = [], [], [], [], []
    for ch in cau_hinh:
        s, ms = ch["s"], ch["ms"]
        best = cutoff_tot_nhat(s)
        if not all(c in s.index for c in (0, *CUTOFF_SO_SANH)):
            continue
        nguon.append(ch["file"])
        o = []
        for vai_tro, c in (("cutoff 0", 0), ("cutoff 7", 7), ("cutoff 10", 10), ("tốt nhất", best)):
            b1_csv.append({"tn": ch["tn"].upper(), "dist": ch["dist"], "n": ch["n"], "vai_tro": vai_tro, "cutoff": c,
                           "so_trial": int(s.at[c, "so_trial"]), "median_ms": s.at[c, "median_ms"],
                           "median_ci_lo": s.at[c, "median_ci_lo"], "median_ci_hi": s.at[c, "median_ci_hi"],
                           "mean_ms": s.at[c, "mean_ms"], "mean_ci_lo": s.at[c, "mean_ci_lo"],
                           "mean_ci_hi": s.at[c, "mean_ci_hi"]})
            o.append(f_ci(s.at[c, "median_ms"], s.at[c, "median_ci_lo"], s.at[c, "median_ci_hi"]))
        b1_md.append([ch["tn"].upper(), ch["dist"], ten_N(ch["n"]), int(s["so_trial"].iloc[0]), *o[:3],
                      f"{best}: {o[3]}"])
        cap = [(7, 10)] + ([(7, best), (10, best)] if best not in CUTOFF_SO_SANH else [])
        for a, b in cap:
            p_mwu, p_welch = kiem_dinh(ms[a], ms[b])
            chenh = (s.at[b, "median_ms"] / s.at[a, "median_ms"] - 1) * 100
            ten_b = f"{b} (tốt nhất)" if b == best else str(b)
            b2_csv.append({"tn": ch["tn"].upper(), "dist": ch["dist"], "n": ch["n"], "cutoff_a": a, "cutoff_b": b,
                           "b_la_tot_nhat": b == best, "median_a_ms": s.at[a, "median_ms"],
                           "median_b_ms": s.at[b, "median_ms"], "chenh_lech_pct": chenh,
                           "p_mann_whitney": p_mwu, "p_welch": p_welch, "co_y_nghia": p_mwu < MUC_Y_NGHIA})
            b2_md.append([ch["tn"].upper(), ch["dist"], ten_N(ch["n"]), f"{a} → {ten_b}", f_ms(s.at[a, "median_ms"]),
                          f_ms(s.at[b, "median_ms"]), f"{chenh:+.2f}%", f_p(p_mwu), f_p(p_welch),
                          "có" if p_mwu < MUC_Y_NGHIA else "không"])
    mo1 = ["- Mỗi ô: median (ms) [CI 95% của median, theo thống kê thứ tự].",
           "- Mean và CI 95% của mean (phân phối t) có trong file CSV cùng tên.",
           "- Cột cuối: cutoff tốt nhất trong các cutoff đã đo của cấu hình đó (TN5 chỉ đo 0, 7, 10 và một cutoff "
           "tốt nhất lấy từ TN1)."]
    out = ghi_bang("B1_median_0_7_10", pd.DataFrame(b1_csv), "Bảng B1: median của cutoff 0, 7, 10 và tốt nhất",
                   mo1, ["TN", "phân bố", "N", "trial", "cutoff 0", "cutoff 7", "cutoff 10", "tốt nhất"],
                   b1_md, [0, 0, 1, 1, 1, 1, 1, 1], nguon)
    mo2 = ["- Cặp a → b: chênh lệch = median(b) / median(a) − 1. Âm nghĩa là cutoff b nhanh hơn cutoff a.",
           f"- p MWU: Mann-Whitney U hai phía (kiểm định chính). p Welch: Welch t-test hai phía (đối chiếu).",
           f"- \"Khác biệt\" = có nếu p MWU < {MUC_Y_NGHIA}. Nếu không thì không đủ bằng chứng để nói hai cutoff "
           "cho thời gian khác nhau.",
           "- Nếu cutoff tốt nhất chính là 7 hoặc 10 thì chỉ có cặp 7 → 10 (ghi \"(tốt nhất)\" bên cạnh).",
           "- TN5 chỉ có 10 trial mỗi cutoff: một phép đo lệch đủ làm p Welch tăng mạnh, p MWU ít bị ảnh hưởng hơn."]
    out += ghi_bang("B2_kiem_dinh_7_10", pd.DataFrame(b2_csv), "Bảng B2: so sánh cutoff 7, 10 và tốt nhất", mo2,
                    ["TN", "phân bố", "N", "cặp a → b", "median a (ms)", "median b (ms)", "chênh lệch", "p MWU",
                     "p Welch", "khác biệt"], b2_md, [0, 0, 1, 0, 1, 1, 1, 1, 1, 0], nguon)
    return out


def bang_C(tn5):
    tn5 = sorted(tn5, key=lambda ch: ch["n"])
    cutoffs = sorted(set.intersection(*(set(ch["s"].index) for ch in tn5)))
    ns = np.array([ch["n"] for ch in tn5], float)
    med = pd.DataFrame({c: [ch["s"].at[c, "median_ms"] for ch in tn5] for c in cutoffs}, index=ns.astype(int))
    ti_le = med / med.shift(1)
    ly_thuyet = pd.Series(ns * np.log2(ns), index=med.index)
    ly_thuyet = ly_thuyet / ly_thuyet.shift(1)
    do_doc = {c: np.polyfit(np.log2(ns), np.log2(med[c].to_numpy()), 1)[0] for c in cutoffs}
    dong_csv, dong_md = [], []
    for i, n in enumerate(med.index):
        for c in cutoffs:
            dong_csv.append({"n": n, "cutoff": c, "median_ms": med.at[n, c],
                             "ti_le_doubling": ti_le.at[n, c] if i else np.nan,
                             "log2_ti_le": np.log2(ti_le.at[n, c]) if i else np.nan,
                             "ti_le_ly_thuyet_nlogn": ly_thuyet.at[n] if i else np.nan,
                             "ti_le_so_voi_cutoff0": med.at[n, c] / med.at[n, 0] if 0 in cutoffs else np.nan,
                             "do_doc_loglog": do_doc[c]})
        o = [ten_N(n)]
        for c in cutoffs:
            o += [f_ms(med.at[n, c]), f"{ti_le.at[n, c]:.3f}" if i else "—"]
        o.append(f"{ly_thuyet.at[n]:.3f}" if i else "—")
        dong_md.append(o)
    cot = ["N"]
    for c in cutoffs:
        cot += [f"T(c={c}) ms", f"tỉ lệ c={c}"]
    cot.append("tỉ lệ lý thuyết N log₂N")
    mo_ta = ["- T: median thời gian một lần sort (ms). Tỉ lệ doubling = T(N) / T(N/2).",
             "- Tỉ lệ lý thuyết nếu T ~ N log₂N: N log₂N / ((N/2) log₂(N/2)). Nếu T ~ N^b thì tỉ lệ = 2^b.",
             "- Độ dốc log-log (bình phương tối thiểu của log₂T theo log₂N): "
             + ", ".join(f"cutoff {c}: {do_doc[c]:.3f}" for c in cutoffs) + "."]
    return ghi_bang("C_doubling_tn5", pd.DataFrame(dong_csv), "Bảng C: doubling test (TN5, random)", mo_ta, cot,
                    dong_md, [1] * len(cot), [ch["file"] for ch in tn5])


def bang_D(chinh, cu):
    dong_csv, dong_md, nguon = [], [], []
    for khoa in sorted((k for k in chinh if k[0] == "tn1"), key=lambda k: int(k[2])):
        if not cu[khoa]:
            continue
        s_chinh, _ = thong_ke_cutoff(pd.read_csv(chinh[khoa]))
        for vai_tro, p in [("chính", chinh[khoa])] + [("lặp lại", q) for q in cu[khoa]]:
            s = s_chinh if p == chinh[khoa] else thong_ke_cutoff(pd.read_csv(p))[0]
            best = cutoff_tot_nhat(s)
            chung = s.index.intersection(s_chinh.index)
            lech = (s.loc[chung, "median_ms"] / s_chinh.loc[chung, "median_ms"] - 1) * 100
            dong_csv.append({"n": int(khoa[2]), "lan_chay": thoi_diem(p), "vai_tro": vai_tro, "cutoff_tot_nhat": best,
                             "median_tot_nhat_ms": s.at[best, "median_ms"], "cai_thien_pct": s.at[best, "cai_thien_pct"],
                             "vung_toi_uu": gop_khoang(vung_toi_uu(s)),
                             "lech_median_min_pct": lech.min(), "lech_median_tb_pct": lech.mean(),
                             "lech_median_max_pct": lech.max(), "file": p.name})
            dong_md.append([ten_N(khoa[2]), thoi_diem(p), vai_tro, best, f_ms(s.at[best, "median_ms"]),
                            f"{s.at[best, 'cai_thien_pct']:.1f}%", gop_khoang(vung_toi_uu(s)),
                            "—" if vai_tro == "chính" else f"{lech.min():+.2f}% / {lech.mean():+.2f}% / {lech.max():+.2f}%"])
            nguon.append(p)
    if not dong_csv:
        return []
    mo_ta = ["- Lần chạy chính: file mới nhất (dùng cho mọi bảng và hình khác). Lần lặp lại: các file cũ hơn.",
             "- Lệch median: median(lần lặp lại) / median(lần chính) − 1, tính cho từng cutoff; ghi min / trung bình / max."]
    return ghi_bang("D_lap_lai_tn1", pd.DataFrame(dong_csv), "Bảng D: độ lặp lại của TN1 giữa các lần chạy", mo_ta,
                    ["N", "lần chạy", "vai trò", "cutoff tốt nhất", "median tốt nhất (ms)", "cải thiện",
                     "vùng tối ưu (≤ 2%)", "lệch median min / TB / max"], dong_md, [1, 0, 0, 1, 1, 1, 0, 1], nguon)


def doc_tn3(p):
    d = pd.read_csv(p)
    if (d.groupby("cutoff")["compares"].nunique() > 1).any():
        sys.exit(f"LỖI: {p.name} có cutoff với số phép so sánh khác nhau giữa các trial.")
    c = d.groupby("cutoff")["compares"].first()
    n = int(d["n"].iloc[0])
    return c, n


def bang_E(p_tn3, tn1_1e6):
    c, n = doc_tn3(p_tn3)
    nlogn = n * np.log2(n)
    s = tn1_1e6["s"] if tn1_1e6 else None
    dong_csv, dong_md = [], []
    for k, v in c.items():
        tg = s.at[k, "ti_le"] if s is not None and k in s.index else np.nan
        dong_csv.append({"cutoff": int(k), "so_phep_so_sanh": int(v), "chia_nlog2n": v / nlogn,
                         "ti_le_so_voi_cutoff0": v / c[0], "ti_le_thoi_gian_tn1": tg})
        if not np.isnan(tg):
            dong_md.append([int(k), f"{int(v):,}".replace(",", " "), f"{v / nlogn:.4f}", f"{v / c[0]:.3f}", f"{tg:.3f}"])
    mo_ta = [f"- Dữ liệu random, N = {ten_N(n)}. Số phép so sánh do MergeCount.sort trả về (giống nhau ở mọi trial).",
             "- Thời gian tương đối T(c)/T(0) lấy từ TN1 cùng file dữ liệu (median).",
             "- Bảng .md chỉ liệt kê các cutoff có cả ở TN1; file .csv có đủ mọi cutoff của TN3."]
    nguon = [p_tn3] + ([tn1_1e6["file"]] if tn1_1e6 else [])
    return ghi_bang("E_tn3_so_phep_so_sanh", pd.DataFrame(dong_csv), "Bảng E: số phép so sánh theo cutoff (TN3)",
                    mo_ta, ["cutoff", "số phép so sánh", "÷ N log₂N", "so với cutoff 0", "thời gian T(c)/T(0)"],
                    dong_md, [1, 1, 1, 1, 1], nguon)


def thong_ke_tn4(p):
    d = pd.read_csv(p)
    w = d.pivot_table(index=["n", "trial"], columns="method", values="ns_per_sort", aggfunc="first")
    w = w.assign(ti_le=w["merge"] / w["insertion"])
    dong = []
    for n, g in w.groupby(level="n"):
        lo, hi = ci_median(g["ti_le"])
        mlo, mhi = ci_mean(g["ti_le"])
        dong.append({"n": int(n), "so_trial": len(g),
                     "insertion_median_ns": g["insertion"].median(), "merge_median_ns": g["merge"].median(),
                     "insertion_ci_lo": ci_median(g["insertion"])[0], "insertion_ci_hi": ci_median(g["insertion"])[1],
                     "merge_ci_lo": ci_median(g["merge"])[0], "merge_ci_hi": ci_median(g["merge"])[1],
                     "ti_le_trial_median": g["ti_le"].median(), "ti_le_trial_median_ci_lo": lo,
                     "ti_le_trial_median_ci_hi": hi, "ti_le_trial_mean": g["ti_le"].mean(),
                     "ti_le_trial_mean_ci_lo": mlo, "ti_le_trial_mean_ci_hi": mhi})
    t = pd.DataFrame(dong).set_index("n")
    # Điểm giao nhau: n đầu tiên mà merge nhanh hơn (tỉ lệ < 1), nội suy tuyến tính với điểm đo ngay trước
    duoi = t.index[t["ti_le_trial_median"] < 1]
    giao = None
    if len(duoi):
        n1 = int(duoi[0])
        truoc = t.index[t.index < n1]
        if len(truoc):
            n0 = int(truoc[-1])
            r0, r1 = t.at[n0, "ti_le_trial_median"], t.at[n1, "ti_le_trial_median"]
            giao = (n0, n1, n0 + (r0 - 1) / (r0 - r1) * (n1 - n0))
    return t, giao


def bang_F(p_tn4):
    t, giao = thong_ke_tn4(p_tn4)
    dong_md = [[n, f_ms(t.at[n, "insertion_median_ns"]), f_ms(t.at[n, "merge_median_ns"]),
                f"{t.at[n, 'ti_le_trial_median']:.3f} [{t.at[n, 'ti_le_trial_median_ci_lo']:.3f}, "
                f"{t.at[n, 'ti_le_trial_median_ci_hi']:.3f}]"]
               for n in N_HIEN_THI_TN4 if n in t.index]
    mo_ta = ["- Thời gian một lần sort (ns, median). merge = Merge.sort(a, 0): mỗi lần gọi cấp phát mảng aux mới; "
             "insertion = Merge.insertionSort(a, 0, n−1).",
             "- Tỉ lệ = median của merge / insertion tính trong từng trial [CI 95% của median]. Tỉ lệ < 1: merge nhanh hơn.",
             "- Bảng .md chỉ liệt kê một số n; file .csv có đủ mọi n đã đo."]
    if giao:
        mo_ta.append(f"- Điểm giao nhau: tỉ lệ xuống dưới 1 lần đầu ở n = {giao[1]} (n đo ngay trước: {giao[0]}); "
                     f"nội suy tuyến tính giữa hai điểm này: n ≈ {giao[2]:.0f}.")
    return ghi_bang("F_tn4_insertion_merge", t.reset_index(), "Bảng F: insertion sort so với mergesort trên mảng ngắn (TN4)",
                    mo_ta, ["n", "insertion (ns)", "merge (ns)", "merge / insertion"], dong_md, [1, 1, 1, 1],
                    [p_tn4]), t, giao


# ---------------------------------------------------------------- hình

def kieu_chung():
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 9, "axes.titlesize": 9.5, "axes.titleweight": "bold",
        "axes.labelsize": 9, "axes.edgecolor": MAU_TRUC, "axes.linewidth": 0.8, "axes.labelcolor": MUC_PHU,
        "axes.titlecolor": MUC_IN, "axes.titlelocation": "left", "xtick.color": MUC_PHU, "ytick.color": MUC_PHU,
        "xtick.labelsize": 8, "ytick.labelsize": 8, "axes.grid": True, "grid.color": MAU_LUOI,
        "grid.linewidth": 0.6, "grid.linestyle": "-", "axes.spines.top": False, "axes.spines.right": False,
        "axes.axisbelow": True, "legend.frameon": False, "legend.fontsize": 8, "figure.facecolor": "white",
        "axes.facecolor": "white", "savefig.facecolor": "white", "mathtext.default": "regular",
    })


def tieu_de(fig, chinh, phu):
    fig.text(0.012, 0.985, chinh, ha="left", va="top", fontsize=10.5, color=MUC_IN, weight="bold")
    fig.text(0.012, 0.935, phu, ha="left", va="top", fontsize=7.8, color=MUC_PHU, linespacing=1.4)


def ve_duong(ax, x, y, lo=None, hi=None, mau=MAU_PHAN_LOAI[0], dau="o", nhan=None, co_dau=4.5):
    y = np.asarray(y, float)
    yerr = None if lo is None else [np.clip(y - np.asarray(lo, float), 0, None), np.clip(np.asarray(hi, float) - y, 0, None)]
    ax.errorbar(x, y, yerr=yerr, color=mau, marker=dau, markersize=co_dau, markeredgecolor="white",
                markeredgewidth=0.7, linewidth=1.5, elinewidth=0.9, capsize=0, label=nhan, zorder=3)


def danh_dau_7_10(ax, ghi_so=True):
    """Đường dọc ở cutoff 7 và 10; số 7 ghi lệch trái, số 10 lệch phải để hai nhãn không dính nhau."""
    for c, can in zip(CUTOFF_SO_SANH, ("right", "left")):
        ax.axvline(c, color=MUC_NHAT, linewidth=0.8, zorder=1)
        if ghi_so:
            ax.text(c, 1.01, f" {c} " , transform=ax.get_xaxis_transform(), color=MUC_PHU, fontsize=7.5,
                    ha=can, va="bottom")


def truc_cutoff(ax, max_c, hep=False):
    """Trục cutoff; khung hẹp (hai hình cạnh nhau) thì bớt vạch chia cho khỏi chồng chữ."""
    vach = [0, 10, 20, 30, 40, 64, 96, 128] if hep else TICK_CUTOFF
    ax.xaxis.set_major_locator(FixedLocator([c for c in vach if c <= max_c]))
    ax.xaxis.set_minor_locator(NullLocator())
    ax.set_xlim(-3, max_c * 1.16)


def viet_thuong_dau(s):
    return s[:1].lower() + s[1:]


def nhan_cuoi(ax, diem, x, khoang=0.055):
    """Nhãn trực tiếp ở cuối đường. diem: list (y, chữ); giãn theo chiều dọc để các nhãn không chồng nhau."""
    if not diem:
        return
    lo, hi = ax.get_ylim()
    gap = khoang * (hi - lo)
    ds = sorted(diem)
    ys = [y for y, _ in ds]
    for i in range(1, len(ys)):
        ys[i] = max(ys[i], ys[i - 1] + gap)
    tran = ys[-1] - (hi - gap / 2)
    if tran > 0:
        ys = [y - tran for y in ys]
    for (_, chu), y in zip(ds, ys):
        ax.text(x, y, chu, color=MUC_PHU, fontsize=7.8, ha="left", va="center")


def mo_ta_errorbar(che_do, cai_gi="T(c)/T(0)"):
    if che_do == "median":
        return f"Điểm: median của {cai_gi} tính trong từng trial; thanh: CI 95% của median (thống kê thứ tự)."
    return f"Điểm: mean của {cai_gi} tính trong từng trial; thanh: CI 95% của mean (phân phối t)."


def cot_ti_le(s, che_do):
    return s[f"ti_le_trial_{che_do}"], s[f"ti_le_trial_{che_do}_ci_lo"], s[f"ti_le_trial_{che_do}_ci_hi"]


def hinh_tn1(tn1, che_do):
    fig, ax = plt.subplots(figsize=(7.4, 4.8))
    tn1 = sorted(tn1, key=lambda ch: ch["n"])
    max_c = max(max(ch["s"].index) for ch in tn1)
    diem = []
    for i, ch in enumerate(tn1):
        s = ch["s"]
        y, lo, hi = cot_ti_le(s, che_do)
        ve_duong(ax, s.index, y, lo, hi, RAMP_N[i % len(RAMP_N)], DAU[i], f"N = {ten_N_hinh(ch['n'])}")
        diem.append((y.iloc[-1], f"N = {ten_N_hinh(ch['n'])}"))
    ax.axhline(1, color=MAU_TRUC, linewidth=0.9, zorder=1)
    danh_dau_7_10(ax)
    truc_cutoff(ax, max_c)
    ax.set_xlabel("cutoff c (đoạn có độ dài ≤ c dùng insertion sort; c = 0: không dùng)")
    ax.set_ylabel("T(c) / T(0)")
    nhan_cuoi(ax, diem, max_c + 3)
    so_trial = ", ".join(f"{ten_N(ch['n'])}: {int(ch['s']['so_trial'].iloc[0])}" for ch in tn1)
    tieu_de(fig, "TN1 · Thời gian tương đối theo cutoff, dữ liệu random",
            f"{mo_ta_errorbar(che_do)}\nSố trial theo N: {so_trial}. Đường dọc: cutoff 7 và 10.")
    fig.legend(*ax.get_legend_handles_labels(), loc="lower center", ncol=len(tn1), bbox_to_anchor=(0.5, 0.0))
    fig.tight_layout(rect=(0, 0.06, 1, 0.86))
    return luu(fig, "tn1_ti_le_theo_cutoff.png")


def hinh_tn2(tn2, tn1, che_do):
    tham_chieu = [ch for ch in tn1 if ch["n"] == 1_000_000]
    duong = [(f"random (TN1, N = {ten_N_hinh(1_000_000)})", "random", ch) for ch in tham_chieu] + \
            [(ch["dist"], ch["dist"], ch) for ch in sorted(tn2, key=lambda ch: THU_TU_PHAN_BO.index(ch["dist"]))]
    max_c = max(max(ch["s"].index) for _, _, ch in duong)
    gia_tri = np.concatenate([cot_ti_le(ch["s"], che_do)[2].to_numpy() for _, _, ch in duong])
    thap = min(cot_ti_le(ch["s"], che_do)[1].min() for _, _, ch in duong)
    ranh = 1.08
    co_ngat = gia_tri.max() > ranh + 0.05
    if co_ngat:
        fig, (tren, duoi) = plt.subplots(2, 1, sharex=True, figsize=(7.4, 5.6),
                                         gridspec_kw={"height_ratios": [1, 3], "hspace": 0.08})
        cac_truc = [tren, duoi]
    else:
        fig, duoi = plt.subplots(figsize=(7.4, 4.8))
        tren, cac_truc = None, [duoi]
    diem_tren, diem_duoi = [], []
    for nhan, dist, ch in duong:
        s = ch["s"]
        y, lo, hi = cot_ti_le(s, che_do)
        for ax in cac_truc:
            ve_duong(ax, s.index, y, lo, hi, MAU_PHAN_BO[dist], DAU_PHAN_BO[dist], nhan if ax is duoi else None)
        cuoi = y.iloc[-1]
        (diem_tren if co_ngat and cuoi > ranh else diem_duoi).append((cuoi, nhan.split(" (")[0]))
    duoi.set_ylim(min(thap, 1) - 0.03, ranh)
    for ax in cac_truc:
        ax.axhline(1, color=MAU_TRUC, linewidth=0.9, zorder=1)
        danh_dau_7_10(ax, ghi_so=(ax is cac_truc[0]))
        truc_cutoff(ax, max_c)
    if co_ngat:
        tren_lo = min(v for v in gia_tri if v > ranh) - 0.06
        tren.set_ylim(tren_lo, gia_tri.max() + 0.06)
        tren.spines["bottom"].set_visible(False)
        tren.tick_params(axis="x", length=0)
        # dấu ngắt trục: hai gạch chéo ở trục y
        kw = dict(color=MUC_NHAT, clip_on=False, linewidth=0.9)
        for ax, y0 in ((tren, 0), (duoi, 1)):
            ax.plot([-0.012, 0.012], [y0 - 0.025 * (3 if ax is tren else 1), y0 + 0.025 * (3 if ax is tren else 1)],
                    transform=ax.transAxes, **kw)
        nhan_cuoi(tren, diem_tren, max_c + 3, khoang=0.2)
    nhan_cuoi(duoi, diem_duoi, max_c + 3)
    duoi.set_xlabel("cutoff c (đoạn có độ dài ≤ c dùng insertion sort; c = 0: không dùng)")
    duoi.set_ylabel("T(c) / T(0)")
    if co_ngat:
        tren.set_ylabel(" ")
    so_trial = int(tn2[0]["s"]["so_trial"].iloc[0]) if tn2 else 0
    so_trial_rd = int(tham_chieu[0]["s"]["so_trial"].iloc[0]) if tham_chieu else 0
    tieu_de(fig, "TN2 · Thời gian tương đối theo cutoff, theo phân bố dữ liệu (N = 10⁶)",
            f"{mo_ta_errorbar(che_do)}\n{so_trial} trial mỗi phân bố (random: {so_trial_rd} trial, lấy từ TN1). "
            "Đường dọc: cutoff 7 và 10." + (" Trục y bị ngắt (hai gạch chéo)." if co_ngat else ""))
    fig.legend(*duoi.get_legend_handles_labels(), loc="lower center", ncol=len(duong), bbox_to_anchor=(0.5, 0.0))
    fig.subplots_adjust(left=0.09, right=0.98, top=0.84, bottom=0.17)
    return luu(fig, "tn2_ti_le_theo_phan_bo.png")


def hinh_tn3(p_tn3, tn1_1e6, che_do):
    c, n = doc_tn3(p_tn3)
    fig, (trai, phai) = plt.subplots(1, 2, figsize=(7.4, 3.9), sharex=True)
    ve_duong(trai, c.index, c.to_numpy() / (n * np.log2(n)), mau=MAU_PHAN_LOAI[0], dau="o", co_dau=3.5)
    trai.set_title("Số phép so sánh (TN3, MergeCount)", pad=14)
    trai.set_ylabel("số phép so sánh / (N log₂N)")
    max_c = int(c.index.max())
    if tn1_1e6:
        s = tn1_1e6["s"]
        y, lo, hi = cot_ti_le(s, che_do)
        ve_duong(phai, s.index, y, lo, hi, mau=MAU_PHAN_LOAI[0], dau="o", co_dau=3.5)
        phai.axhline(1, color=MAU_TRUC, linewidth=0.9, zorder=1)
        max_c = max(max_c, int(s.index.max()))
    phai.set_title("Thời gian tương đối (TN1, cùng dữ liệu)", pad=14)
    phai.set_ylabel("T(c) / T(0)")
    for ax in (trai, phai):
        danh_dau_7_10(ax)
        truc_cutoff(ax, max_c, hep=True)
        ax.set_xlim(-3, max_c + 5)
        ax.set_xlabel("cutoff c")
    tieu_de(fig, f"TN3 · Số phép so sánh và thời gian theo cutoff (random, N = {ten_N(n)})",
            "Trái: số phép so sánh MergeCount.sort trả về (giống nhau ở mọi trial), chia cho N log₂N.\n"
            f"Phải: {viet_thuong_dau(mo_ta_errorbar(che_do))}\n"
            "Hai bên dùng cùng file dữ liệu. Đường dọc: cutoff 7 và 10.")
    fig.tight_layout(rect=(0, 0, 1, 0.80))
    return luu(fig, "tn3_so_sanh_va_thoi_gian.png")


def hinh_tn4(t, giao, che_do):
    fig, (trai, phai) = plt.subplots(1, 2, figsize=(7.4, 4.0))
    n = t.index.to_numpy()
    for i, (cot, nhan) in enumerate((("insertion", "insertion sort"), ("merge", "Merge.sort(a, 0)"))):
        ve_duong(trai, n, t[f"{cot}_median_ns"], t[f"{cot}_ci_lo"], t[f"{cot}_ci_hi"], MAU_PHAN_LOAI[i], DAU[i],
                 nhan, co_dau=3)
    trai.set_xscale("log", base=2)
    trai.set_yscale("log")
    trai.set_xlabel("độ dài mảng n (thang log)")
    trai.set_ylabel("thời gian một lần sort (ns, thang log)")
    trai.set_title("Thời gian theo n", pad=8)
    trai.legend(loc="upper left")
    ti_le_cot = f"ti_le_trial_{che_do}"
    ve_duong(phai, n, t[ti_le_cot], t[f"{ti_le_cot}_ci_lo"], t[f"{ti_le_cot}_ci_hi"], MAU_PHAN_LOAI[1], "s", co_dau=3)
    phai.set_xscale("log", base=2)
    phai.axhline(1, color=MAU_TRUC, linewidth=0.9, zorder=1)
    if giao:
        phai.axvline(giao[2], color=MUC_NHAT, linewidth=0.8, zorder=1)
        phai.text(giao[2], 1.01, f"n ≈ {giao[2]:.0f}", transform=phai.get_xaxis_transform(), color=MUC_PHU,
                  fontsize=7.5, ha="center", va="bottom")
    phai.set_xlabel("độ dài mảng n (thang log)")
    phai.set_ylabel("merge / insertion")
    phai.set_title("Tỉ lệ thời gian merge / insertion", pad=14)
    for ax in (trai, phai):
        ax.xaxis.set_major_locator(FixedLocator([2, 4, 8, 16, 32, 64, 128, 256]))
        ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
        ax.xaxis.set_minor_locator(NullLocator())
    tieu_de(fig, "TN4 · Insertion sort so với mergesort trên mảng random ngắn",
            "Trái: median thời gian một lần sort, thanh: CI 95% của median.\n"
            "Phải: " + viet_thuong_dau(mo_ta_errorbar(che_do, "merge / insertion")) + "\n"
            "merge = Merge.sort(a, 0), mỗi lần gọi cấp phát mảng aux mới."
            + (f" Đường dọc: nội suy tuyến tính giữa n = {giao[0]} và {giao[1]}." if giao else ""))
    fig.tight_layout(rect=(0, 0, 1, 0.80))
    return luu(fig, "tn4_insertion_va_merge.png")


def hinh_tn5(tn5):
    tn5 = sorted(tn5, key=lambda ch: ch["n"])
    cutoffs = sorted(set.intersection(*(set(ch["s"].index) for ch in tn5)))
    ns = np.array([ch["n"] for ch in tn5], float)
    fig, (trai, phai) = plt.subplots(1, 2, figsize=(7.4, 4.1))
    for i, c in enumerate(cutoffs):
        t = np.array([ch["s"].at[c, "median_ms"] for ch in tn5])
        doc = np.polyfit(np.log2(ns), np.log2(t), 1)[0]
        ve_duong(trai, ns, t, mau=MAU_PHAN_LOAI[i], dau=DAU[i], nhan=f"cutoff {c} (độ dốc {doc:.3f})", co_dau=4)
        ve_duong(phai, ns[1:], t[1:] / t[:-1], mau=MAU_PHAN_LOAI[i], dau=DAU[i], nhan=f"cutoff {c}", co_dau=4)
    ly_thuyet = ns * np.log2(ns)
    phai.plot(ns[1:], ly_thuyet[1:] / ly_thuyet[:-1], color=MUC_NHAT, linewidth=1.2, linestyle=(0, (4, 3)),
              label="lý thuyết N log₂N", zorder=2)
    phai.axhline(2, color=MAU_TRUC, linewidth=0.9, zorder=1)
    phai.text(ns[1], 2, " 2 = tăng tuyến tính", color=MUC_PHU, fontsize=7.5, va="bottom", ha="left")
    for ax in (trai, phai):
        ax.set_xscale("log", base=2)
        ax.xaxis.set_major_locator(FixedLocator(ns))
        ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: ten_N_hinh(v)))
        ax.xaxis.set_minor_locator(NullLocator())
        ax.set_xlabel("N (thang log₂)")
    trai.set_yscale("log", base=2)
    trai.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
    trai.set_ylabel("thời gian một lần sort (ms, thang log₂)")
    trai.set_title("log-log: T theo N", pad=8)
    trai.legend(loc="upper left")
    phai.set_ylabel("T(N) / T(N/2)")
    phai.set_title("Tỉ lệ doubling", pad=8)
    lo, hi = phai.get_ylim()
    phai.set_ylim(min(lo, 1.95), max(hi, 2.25))
    phai.legend(loc="upper right", ncol=2)
    tieu_de(fig, "TN5 · Doubling test, dữ liệu random, N = 2¹⁷ … 2²³",
            "Median thời gian một lần sort, 10 trial mỗi N. Độ dốc: bình phương tối thiểu của log₂T theo log₂N.\n"
            "Phải: T(N)/T(N/2); đường đứt: tỉ lệ nếu T tỉ lệ với N log₂N.")
    fig.tight_layout(rect=(0, 0, 1, 0.85))
    return luu(fig, "tn5_doubling.png")


def luu(fig, ten):
    p = FIGURES / ten
    fig.savefig(p, dpi=DPI)
    plt.close(fig)
    return [p]


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description="Bước 6: thống kê và đồ thị từ results/tn*.csv")
    ap.add_argument("--errorbar", choices=["median", "mean"], default="median",
                    help="error bar trên đồ thị: CI 95%% của median (mặc định) hoặc của mean (phân phối t)")
    args = ap.parse_args()
    TABLES.mkdir(exist_ok=True)
    FIGURES.mkdir(exist_ok=True)
    kieu_chung()

    chinh, cu = doc_ket_qua()
    print("Số liệu chính (file mới nhất của mỗi cấu hình):")
    for khoa in sorted(chinh, key=lambda k: (k[0], THU_TU_PHAN_BO.index(k[1]) if k[1] in THU_TU_PHAN_BO else 9,
                                             int(k[2]) if k[2].isdigit() else 0)):
        them = f"   (+ {len(cu[khoa])} lần chạy cũ hơn)" if cu[khoa] else ""
        print(f"  {chinh[khoa].name}{them}")

    cau_hinh = []
    for (tn, dist, co), p in chinh.items():
        if tn in ("tn1", "tn2", "tn5"):
            s, ms = thong_ke_cutoff(pd.read_csv(p))
            cau_hinh.append({"tn": tn, "dist": dist, "n": int(co), "file": p, "s": s, "ms": ms})
    thu_tu = lambda ch: (ch["tn"], THU_TU_PHAN_BO.index(ch["dist"]), ch["n"])  # noqa: E731
    cau_hinh.sort(key=thu_tu)
    tn1 = [ch for ch in cau_hinh if ch["tn"] == "tn1"]
    tn2 = [ch for ch in cau_hinh if ch["tn"] == "tn2"]
    tn5 = [ch for ch in cau_hinh if ch["tn"] == "tn5"]
    tn1_1e6 = next((ch for ch in tn1 if ch["n"] == 1_000_000), None)
    p_tn3 = next((p for k, p in chinh.items() if k[0] == "tn3"), None)
    p_tn4 = next((p for k, p in chinh.items() if k[0] == "tn4"), None)

    ra = bang_day_du(cau_hinh)
    if tn1 or tn2:
        ra += bang_A(tn1, tn2)
    ra += bang_B(cau_hinh)
    if len(tn5) >= 2:
        ra += bang_C(tn5)
    ra += bang_D(chinh, cu)
    if p_tn3:
        ra += bang_E(p_tn3, tn1_1e6)
    if p_tn4:
        out, t4, giao = bang_F(p_tn4)
        ra += out

    if tn1:
        ra += hinh_tn1(tn1, args.errorbar)
    if tn2:
        ra += hinh_tn2(tn2, tn1, args.errorbar)
    if p_tn3:
        ra += hinh_tn3(p_tn3, tn1_1e6, args.errorbar)
    if p_tn4:
        ra += hinh_tn4(t4, giao, args.errorbar)
    if len(tn5) >= 2:
        ra += hinh_tn5(tn5)

    print(f"\nĐã ghi {len(ra)} file (error bar: CI 95% của {args.errorbar}):")
    for p in ra:
        print(f"  {p.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
