#!/usr/bin/env python3
"""Bước 4: kiểm tra nhanh số liệu chạy thử (pilot) của Benchmark.
Dùng được cho CSV của TN1, TN2, TN5 ở Bước 5 (cùng harness Benchmark); khi đó bỏ qua mục [4].

Cách dùng (từ thư mục gốc project):
    .venv/bin/python scripts/check_pilot.py                     # đợt pilot mới nhất trong results/
    .venv/bin/python scripts/check_pilot.py results/pilot_random_100000_<timestamp>.csv ...

Kiểm tra 4 điều trong kế hoạch (Bước 4):
  [1] CSV đúng định dạng: đủ cột, không thiếu giá trị, mỗi (trial, cutoff) đúng một dòng,
      cùng một K trong một file, file .meta.txt đi kèm có status=ok.
  [2] Cutoff 0 và cutoff 1 tương đương nhau nên thời gian phải gần bằng nhau;
      chênh lệch median giữa hai cutoff này là ước lượng mức nhiễu đo.
  [3] CV = độ lệch chuẩn / trung bình dưới 5%. Kèm theo: độ trôi theo trial (máy nóng lên),
      GC trong vùng tính giờ, thời gian JIT trong lúc đo.
  [4] Ước lượng thời gian chạy TN1, TN2, TN5 ở Bước 5 (cùng harness) từ số đo pilot.
Đây chỉ là kiểm tra nhanh. Thống kê đầy đủ (CI 95%, kiểm định, đồ thị) làm ở Bước 6.
"""
import math
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
COLUMNS = ["experiment", "dist", "n", "cutoff", "trial", "k", "ns_per_sort", "pos", "gc"]
CV_LIMIT = 5.0     # %, ngưỡng trong kế hoạch
DRIFT_LIMIT = 3.0  # %, chênh lệch lớn nhất giữa các trial coi là đáng chú ý
STAMP = re.compile(r"_(\d{8}_\d{6})\.csv$")


def latest_pilot_files():
    stamped = []
    for f in sorted((ROOT / "results").glob("pilot_*.csv")):
        m = STAMP.search(f.name)
        if m:
            stamped.append((m.group(1), f))
    if not stamped:
        sys.exit("Không thấy results/pilot_*.csv. Chạy scripts/run_pilot.sh trước.")
    last = max(s for s, _ in stamped)
    return [f for s, f in stamped if s == last]


def read_meta(csv_path):
    p = csv_path.with_name(csv_path.name[: -len(".csv")] + ".meta.txt")
    meta = {}
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            meta[key] = value
    return meta


def fnum(meta, key, default=float("nan")):
    try:
        return float(meta[key])
    except (KeyError, ValueError):
        return default


# ----------------------------------------------------------------------
# [1] Định dạng
# ----------------------------------------------------------------------

def check_format(files):
    problems, frames, metas = [], [], {}
    for f in files:
        df = pd.read_csv(f)
        missing = [c for c in COLUMNS if c not in df.columns]
        if missing:
            problems.append(f"{f.name}: thiếu cột {missing}")
            continue
        if df[COLUMNS].isna().any().any():
            problems.append(f"{f.name}: có ô trống")
        if (df["ns_per_sort"] <= 0).any():
            problems.append(f"{f.name}: có ns_per_sort <= 0")
        if df["k"].nunique() != 1:
            problems.append(f"{f.name}: K không giống nhau giữa các dòng")
        if df[["dist", "n"]].drop_duplicates().shape[0] != 1:
            problems.append(f"{f.name}: một file chứa nhiều (dist, n)")

        meta = read_meta(f)
        if not meta:
            problems.append(f"{f.name}: không có file .meta.txt đi kèm")
        elif meta.get("status") != "ok":
            problems.append(f"{f.name}: meta status = {meta.get('status')}")
        trials = int(meta["trials"]) if "trials" in meta else int(df["trial"].max())
        cutoffs = ([int(c) for c in meta["cutoffs"].split(",")] if "cutoffs" in meta
                   else sorted(df["cutoff"].unique()))
        if len(df) != trials * len(cutoffs):
            problems.append(f"{f.name}: có {len(df)} dòng, cần {trials} trial x {len(cutoffs)} cutoff"
                            f" = {trials * len(cutoffs)}")
        if df.duplicated(["trial", "cutoff"]).any():
            problems.append(f"{f.name}: có (trial, cutoff) bị lặp")
        if sorted(df["cutoff"].unique()) != sorted(cutoffs):
            problems.append(f"{f.name}: tập cutoff trong CSV khác meta")
        for trial, grp in df.groupby("trial"):
            if sorted(grp["pos"]) != list(range(1, len(cutoffs) + 1)):
                problems.append(f"{f.name}: trial {trial} có cột pos không phải 1..{len(cutoffs)}")
                break

        metas[(df["dist"].iloc[0], int(df["n"].iloc[0]))] = meta
        frames.append(df)
    return problems, frames, metas


# ----------------------------------------------------------------------
# Bảng thống kê
# ----------------------------------------------------------------------

def stats_table(df):
    st = (df.groupby(["dist", "n", "cutoff"])["ms"]
          .agg(trials="count", median="median", mean="mean", sd="std", min="min")
          .reset_index())
    st["cv_pct"] = st["sd"] / st["mean"] * 100
    base = st[st["cutoff"] == 0].set_index(["dist", "n"])["median"]
    st["ratio"] = [m / base.get((d, n), float("nan")) for d, n, m in zip(st["dist"], st["n"], st["median"])]
    return st


def print_table(st, df):
    for (dist, n), grp in st.groupby(["dist", "n"]):
        k = int(df[(df["dist"] == dist) & (df["n"] == n)]["k"].iloc[0])
        print(f"\n  {dist}, n = {n:,} (K = {k} lần sort mỗi phép đo, {int(grp['trials'].iloc[0])} trial)")
        print("    cutoff   median ms     mean ms      sd ms    CV %      min ms   T(c)/T(0)")
        for _, r in grp.iterrows():
            flag = "   <- CV >= 5%" if r["cv_pct"] >= CV_LIMIT else ""
            print(f"    {int(r['cutoff']):>6} {r['median']:>11.4f} {r['mean']:>11.4f} {r['sd']:>10.4f}"
                  f" {r['cv_pct']:>7.2f} {r['min']:>11.4f} {r['ratio']:>11.4f}{flag}")


# ----------------------------------------------------------------------
# [2] Cutoff 0 so với cutoff 1, [3] CV và độ trôi
# ----------------------------------------------------------------------

def check_noise(st, df):
    ok = True
    for (dist, n), grp in st.groupby(["dist", "n"]):
        g = grp.set_index("cutoff")
        if 0 not in g.index or 1 not in g.index:
            print(f"  {dist} n = {n:,}: không có đủ cutoff 0 và 1 để so")
            continue
        diff = (g.loc[1, "median"] / g.loc[0, "median"] - 1) * 100
        sub = df[(df["dist"] == dist) & (df["n"] == n)]
        paired = (sub[sub["cutoff"] == 1].set_index("trial")["ms"]
                  / sub[sub["cutoff"] == 0].set_index("trial")["ms"] - 1) * 100
        best = g["median"].idxmin()
        gain = (1 - g.loc[best, "median"] / g.loc[0, "median"]) * 100
        verdict = "tốt" if abs(diff) <= 1 else ("chấp nhận được" if abs(diff) <= 2 else "NHIỄU LỚN")
        ok &= abs(diff) <= 2
        print(f"  {dist} n = {n:,}: median cutoff 1 so với cutoff 0: {diff:+.2f}%  ({verdict});"
              f" từng trial: {paired.min():+.2f}% .. {paired.max():+.2f}%")
        ratio = gain / abs(diff) if abs(diff) > 0.01 else float("inf")
        print(f"      để so sánh: cutoff tốt nhất trong pilot là {best}, nhanh hơn cutoff 0 {gain:.1f}%"
              f" (gấp {ratio:.0f} lần mức nhiễu trên)" if math.isfinite(ratio) else
              f"      để so sánh: cutoff tốt nhất trong pilot là {best}, nhanh hơn cutoff 0 {gain:.1f}%")
    return ok


def check_cv(st, df, metas):
    ok = True
    for (dist, n), grp in st.groupby(["dist", "n"]):
        worst = grp.loc[grp["cv_pct"].idxmax()]
        bad = grp[grp["cv_pct"] >= CV_LIMIT]
        ok &= bad.empty
        status = "OK" if bad.empty else f"VƯỢT 5% ở cutoff {', '.join(str(int(c)) for c in bad['cutoff'])}"
        print(f"  {dist} n = {n:,}: CV lớn nhất {worst['cv_pct']:.2f}% (cutoff {int(worst['cutoff'])}) -> {status}")

        sub = df[(df["dist"] == dist) & (df["n"] == n)].copy()
        sub["rel"] = sub["ms"] / sub.groupby("cutoff")["ms"].transform("median")
        by_trial = sub.groupby("trial")["rel"].median()
        by_pos = sub.groupby("pos")["rel"].median()
        spread = (by_trial.max() - by_trial.min()) * 100
        third = max(1, math.ceil(len(by_trial) / 3))
        trend = (by_trial.iloc[-third:].median() - by_trial.iloc[:third].median()) * 100
        if trend > DRIFT_LIMIT:
            note = f"   <- các trial cuối chậm hơn các trial đầu {trend:.1f}%, có thể máy nóng lên"
        elif spread > DRIFT_LIMIT:
            note = f"   <- có trial lệch {spread:.1f}% nhưng không chậm dần: nhiễu tức thời"
        else:
            note = ""
        print(f"      theo trial (thời gian / median của cutoff đó): "
              + " ".join(f"{v:.3f}" for v in by_trial) + note)
        print(f"      theo vị trí trong trial (pos):                 " + " ".join(f"{v:.3f}" for v in by_pos))
        meta = metas.get((dist, n), {})
        gc = int(sub["gc"].sum())
        print(f"      GC trong vùng tính giờ: {gc} lần"
              f" | JIT trong lúc đo: {meta.get('jit_ms_measure', '?')} ms"
              f" (warm-up: {meta.get('warmup_sorts', '?')} lần sort, {meta.get('warmup_seconds', '?')} s,"
              f" JIT {meta.get('jit_ms_warmup', '?')} ms)")
    return ok


# ----------------------------------------------------------------------
# [4] Ước lượng thời gian Bước 5
# ----------------------------------------------------------------------

def estimate(st, df, metas):
    """Ước lượng thời gian TN1, TN2, TN5 (cùng harness Benchmark) từ số đo random trong pilot."""
    rnd = st[st["dist"] == "random"]
    if rnd.empty:
        print("  Không có số đo random để ước lượng.")
        return
    refs = {}
    min_ms = 20.0
    for n, grp in rnd.groupby("n"):
        meta = metas.get(("random", n), {})
        sub = df[(df["dist"] == "random") & (df["n"] == n)]
        timed = (sub["ns_per_sort"] * sub["k"]).sum() / 1e9  # tổng thời gian trong vùng tính giờ
        wall = fnum(meta, "measure_seconds")
        other = fnum(meta, "jvm_uptime_seconds", 0) - fnum(meta, "warmup_seconds", 0) - fnum(meta, "measure_seconds", 0)
        min_ms = fnum(meta, "min_batch_ms", min_ms)
        refs[int(n)] = {
            "t_mean": grp["median"].mean() / 1e3,  # giây mỗi lần sort, trung bình qua các cutoff pilot
            "t_fast": grp["median"].min() / 1e3,
            "f": wall / timed if timed > 0 and math.isfinite(wall) else 1.1,  # tính cả chép mảng, isSorted
            "other": max(other, 0) + 0.5,  # đọc dữ liệu, SHA-256, khởi động JVM
        }

    def nlogn(x):
        return x * math.log2(x)

    def ref_for(n):
        """Số đo pilot có N gần n nhất (theo thang log)."""
        ref_n = min(refs, key=lambda r: abs(math.log(r) - math.log(n)))
        return refs[ref_n], ref_n

    def run_seconds(n, n_cutoffs, trials, warmup=50, warmup_min=1.0):
        r, ref_n = ref_for(n)
        scale = nlogn(n) / nlogn(ref_n)
        t, t_fast = r["t_mean"] * scale, r["t_fast"] * scale
        k = max(1, math.ceil(min_ms / 1e3 / t_fast))
        measure = trials * n_cutoffs * k * t * r["f"]
        warm = max(max(warmup, n_cutoffs) * t, warmup_min)
        return measure + warm + r["other"]

    dists2 = ["sorted", "reversed", "nearly", "fewdistinct"]
    plan = [
        ("TN1", "random N = 10^4, 10^5, 10^6 (30 trial), 10^7 (10 trial); 34 cutoff",
         sum(run_seconds(n, 34, 30) for n in (10**4, 10**5, 10**6)) + run_seconds(10**7, 34, 10)),
        ("TN2", "4 phân bố, N = 10^6, 34 cutoff, 20 trial (tính như random)",
         sum(run_seconds(10**6, 34, 20) for _ in dists2)),
        ("TN5", "random N = 2^17..2^23, 4 cutoff, 10 trial",
         sum(run_seconds(2**e, 4, 10) for e in range(17, 24))),
    ]
    total = 0.0
    for name, desc, sec in plan:
        total += sec
        print(f"  {name}  ~ {sec / 60:5.1f} phút   {desc}")
    tn1 = plan[0][2]
    print(f"  Tổng TN1 + TN2 + TN5 ~ {total / 60:.0f} phút; chạy lại TN1 lần 2 thêm ~ {tn1 / 60:.0f} phút."
          " Chưa tính TN3, TN4 (dùng harness khác) và thời gian nghỉ giữa các TN.")
    print("  (Thời gian một lần sort ngoại suy theo N log N từ pilot gần nhất; phân bố khác random"
          " có thể nhanh/chậm hơn.)")


def main():
    files = [Path(a) for a in sys.argv[1:]] or latest_pilot_files()
    print("Kiểm tra pilot: " + ", ".join(f.name for f in files))

    problems, frames, metas = check_format(files)
    print("\n[1] Định dạng CSV và meta:", "OK" if not problems else "CÓ VẤN ĐỀ")
    for p in problems:
        print("  - " + p)
    if not frames:
        sys.exit(1)

    df = pd.concat(frames, ignore_index=True)
    df["ms"] = df["ns_per_sort"] / 1e6
    st = stats_table(df)
    print(f"  {len(df)} phép đo, {df[['dist', 'n']].drop_duplicates().shape[0]} cấu hình (dist, n).")
    print_table(st, df)

    print("\n[2] Cutoff 0 so với cutoff 1 (tương đương nhau, chênh lệch = mức nhiễu đo):")
    ok2 = check_noise(st, df)
    print("\n[3] CV = sd / mean (yêu cầu < 5%), độ trôi, GC, JIT:")
    ok3 = check_cv(st, df, metas)
    is_pilot = (df["experiment"] == "pilot").all()
    if is_pilot:  # với file của TN1, TN2, TN5 (Bước 5) thì không cần ước lượng
        print("\n[4] Ước lượng thời gian chạy Bước 5:")
        estimate(st, df, metas)

    print("\nTóm tắt: [1] " + ("OK" if not problems else "LỖI")
          + " | [2] " + ("OK" if ok2 else "xem lại") + " | [3] " + ("OK" if ok3 else "xem lại")
          + (" | [4] xem ước lượng ở trên" if is_pilot else ""))
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
