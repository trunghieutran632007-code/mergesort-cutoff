#!/usr/bin/env bash
# Bước 5: chạy các thí nghiệm chính thức TN1–TN5 (ke-hoach-mergesort-cutoff.md, Bước 5).
#
# | TN | Câu hỏi                          | Dữ liệu                                      | Cutoff / độ dài              | Trials        | Harness      |
# | 1  | cutoff nào nhanh nhất, theo N?   | random N = 10^4, 10^5, 10^6, 10^7            | 0–30,40,50,64,80,96,128      | 30 (10^7: 10) | Benchmark    |
# | 2  | phân bố có dịch điểm tối ưu?     | sorted, reversed, nearly, fewdistinct, 10^6  | như TN1                      | 20            | Benchmark    |
# | 3  | vì sao có điểm tối ưu?           | random N = 10^6, đếm số phép so sánh         | 0–64,80,96,128               | 3             | CompareCount |
# | 4  | insertion nhanh hơn đến độ dài?  | mảng random độ dài n                         | n = 2–64 và 80..256          | 30            | SmallBench   |
# | 5  | cutoff chỉ đổi hằng số (doubling)| random N = 2^17 .. 2^23                      | 0, 7, 10, tốt nhất của TN1   | 10            | Benchmark    |
# So với bảng trong kế hoạch: thêm cutoff 80, 96, 128 (TN1–TN3) và độ dài 80..256 (TN4) vì chạy thử cho thấy
# điểm tối ưu và điểm giao nhau nằm gần hoặc vượt 64. Muốn đúng bảng gốc thì sửa các biến *_CUTOFFS, TN4_SIZES.
# "Tốt nhất của TN1" = cutoff có median nhỏ nhất ở TN1, N = 10^6, lấy từ file TN1 mới nhất trong results/.
#
# Cách dùng (từ thư mục gốc):
#   bash scripts/run_all.sh                 chạy lần lượt tn1 tn2 tn3 tn4 tn5
#   bash scripts/run_all.sh tn1             chỉ chạy TN1 (lần chạy lặp lại vào thời điểm khác)
#   DRY_RUN=1 bash scripts/run_all.sh       chỉ in các lệnh sẽ chạy, không chạy gì
#   PAUSE=0 bash scripts/run_all.sh         không nghỉ giữa các TN (mặc định nghỉ 120 s cho máy nguội)
#   BEST_CUTOFF=40 bash scripts/run_all.sh tn5    TN5 dùng cutoff tốt nhất do bạn chỉ định
#
# Mỗi lần gọi harness là một tiến trình JVM riêng, cờ JVM trong scripts/config.sh.
# Đầu ra, TS = thời điểm bắt đầu đợt chạy, chung cho mọi file của đợt:
#   results/<tn>_<dist>_<N>_<TS>.csv (+ .meta.txt)    số liệu thô
#   results/run_<TS>.log                               toàn bộ những gì in ra màn hình
# Trước khi chạy: cắm sạc, tắt Low Power Mode, tắt trình duyệt và ứng dụng nặng, không dùng máy.
# Có thể để qua đêm: caffeinate giữ máy không ngủ, nhưng KHÔNG gập màn hình (gập là máy ngủ).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
source scripts/config.sh

# ---------------- Cấu hình thí nghiệm ----------------
CUTOFFS="0-30,40,50,64,80,96,128"     # TN1, TN2
TN3_CUTOFFS="0-64,80,96,128"
TN4_SIZES="2-64,80,96,112,128,160,192,256"
TN5_FIXED="0 7 10"                    # cộng thêm cutoff tốt nhất của TN1
WARMUP=50
PAUSE="${PAUSE:-120}"
RESULTS="${RESULTS:-results}"         # đổi thư mục kết quả, chỉ dùng khi chạy thử

EXPS="${*:-tn1 tn2 tn3 tn4 tn5}"
TS="$(date +%Y%m%d_%H%M%S)"
if [ -n "${DRY_RUN:-}" ]; then LOG=/dev/null; else LOG="$RESULTS/run_$TS.log"; fi
if [ -x .venv/bin/python ]; then PY=.venv/bin/python; else PY=python3; fi

log() { echo "$*" | tee -a "$LOG"; }
die() { # chỉ ghi vào log nếu log đã được tạo (lỗi tham số lúc đầu thì không tạo file log)
  echo "LỖI: $*" >&2
  if [ -f "$LOG" ]; then echo "LỖI: $*" >> "$LOG"; fi
  exit 1
}

# Chạy một harness Java trong tiến trình JVM riêng
run_java() {
  if [ -n "${DRY_RUN:-}" ]; then
    echo "+ java $JVM_FLAGS -cp out $*"
    return
  fi
  local start=$SECONDS
  $KEEP_AWAKE java $JVM_FLAGS -cp out "$@" 2>&1 | tee -a "$LOG"
  log "  (tiến trình JVM chạy hết $((SECONDS - start)) s)"
  log
}

bench() { # bench <tn> <dist> <N> <cutoffs> <trials>
  run_java Benchmark --exp "$1" --data "data/$2_$3.bin" --cutoffs "$4" --trials "$5" --warmup "$WARMUP" \
    --out "$RESULTS/$1_$2_$3_$TS.csv"
}

need_data() {
  local f
  for f in "$@"; do
    [ -f "data/$f.bin" ] || die "thiếu data/$f.bin, chạy scripts/gen_data.sh trước"
  done
}

# Cutoff có median nhỏ nhất ở TN1, N = 10^6 (file TN1 mới nhất), hoặc BEST_CUTOFF nếu có đặt
best_cutoff() {
  if [ -n "${BEST_CUTOFF:-}" ]; then echo "$BEST_CUTOFF"; return; fi
  local f
  f="$(ls "$RESULTS"/tn1_random_1000000_*.csv 2>/dev/null | sort | tail -1 || true)"
  [ -n "$f" ] || return 1
  "$PY" - "$f" <<'EOF'
import sys
import pandas as pd
d = pd.read_csv(sys.argv[1])
print(int(d.groupby("cutoff")["ns_per_sort"].median().idxmin()))
EOF
}

tn1() {
  need_data random_10000 random_100000 random_1000000 random_10000000
  for n in 10000 100000 1000000; do bench tn1 random "$n" "$CUTOFFS" 30; done
  bench tn1 random 10000000 "$CUTOFFS" 10
}

tn2() {
  need_data sorted_1000000 reversed_1000000 nearly_1000000 fewdistinct_1000000
  for d in sorted reversed nearly fewdistinct; do bench tn2 "$d" 1000000 "$CUTOFFS" 20; done
}

tn3() {
  need_data random_1000000
  run_java CompareCount --exp tn3 --data data/random_1000000.bin --cutoffs "$TN3_CUTOFFS" --trials 3 \
    --out "$RESULTS/tn3_random_1000000_$TS.csv"
}

tn4() {
  run_java SmallBench --exp tn4 --sizes "$TN4_SIZES" --trials 30 --warmup "$WARMUP" \
    --out "$RESULTS/tn4_random_small_$TS.csv"
}

tn5() {
  local best e list
  if ! best="$(best_cutoff)"; then
    if [ -n "${DRY_RUN:-}" ]; then
      best=64; echo "  (chưa có kết quả TN1, giả sử cutoff tốt nhất = $best để in lệnh)"
    else
      die "chưa có results/tn1_random_1000000_*.csv để lấy cutoff tốt nhất; chạy tn1 trước hoặc đặt BEST_CUTOFF"
    fi
  fi
  list="$(printf '%s\n' $TN5_FIXED "$best" | sort -n | uniq | paste -sd, -)"
  log "TN5: cutoff tốt nhất của TN1 (N = 10^6) = $best -> cutoffs $list"
  for e in 17 18 19 20 21 22 23; do need_data "random_$((2 ** e))"; done
  for e in 17 18 19 20 21 22 23; do bench tn5 random "$((2 ** e))" "$list" 10; done
}

# ---------------- Kiểm tra trước khi chạy ----------------
for x in $EXPS; do
  case "$x" in tn1|tn2|tn3|tn4|tn5) ;; *) die "không có thí nghiệm '$x' (chọn trong tn1 tn2 tn3 tn4 tn5)";; esac
done

POWER="$(pmset -g ps 2>/dev/null | head -1 || echo 'không rõ')"
LOWPOWER="$(pmset -g 2>/dev/null | awk '/lowpowermode/ {print $2}' || true)"
if [ -z "${DRY_RUN:-}" ]; then
  case "$POWER" in *"AC Power"*) ;; *) die "máy không cắm sạc ($POWER). Cắm sạc rồi chạy lại.";; esac
  [ "${LOWPOWER:-0}" != "1" ] || die "Low Power Mode đang bật. Tắt trong System Settings > Battery rồi chạy lại."
fi

log "# Bước 5, đợt chạy $TS: $EXPS"
log "Nguồn điện: $POWER | Low Power Mode: ${LOWPOWER:-không rõ} | JVM flags: $JVM_FLAGS | nghỉ giữa các TN: $PAUSE s"
log

echo "Biên dịch src/ vào out/ ..."
compile_java
if [ -z "${DRY_RUN:-}" ]; then
  bash scripts/machine_info.sh | tee -a "$LOG"
  log
  log "Kiểm tra tính đúng trước khi đo (TestCorrectness) ..."
  java -cp out TestCorrectness 2>&1 | tee -a "$LOG" | tail -1
  log
fi

# ---------------- Chạy ----------------
TOTAL_START=$SECONDS
first=1
for x in $EXPS; do
  if [ "$first" = 0 ] && [ "$PAUSE" -gt 0 ] && [ -z "${DRY_RUN:-}" ]; then
    log "Nghỉ $PAUSE s cho máy nguội ..."
    $KEEP_AWAKE sleep "$PAUSE"
  fi
  first=0
  log "================ $(echo "$x" | tr a-z A-Z) bắt đầu lúc $(date '+%H:%M:%S') ================"
  [ -n "${DRY_RUN:-}" ] || pmset -g therm 2>/dev/null | grep -v '^$' | sed 's/^/  nhiệt độ: /' | tee -a "$LOG" || true
  start=$SECONDS
  "$x"
  log "$(echo "$x" | tr a-z A-Z) xong sau $(( (SECONDS - start) / 60 )) phút $(( (SECONDS - start) % 60 )) giây"
  log
done

if [ -z "${DRY_RUN:-}" ]; then
  log "Xong toàn bộ ($EXPS) sau $(( (SECONDS - TOTAL_START) / 60 )) phút. Kết quả:"
  ls -1 "$RESULTS"/*_"$TS".csv | sed 's/^/  /' | tee -a "$LOG"
  log "Log: $LOG"
  log "Kiểm tra nhanh TN1/TN2/TN5 (CV, cutoff 0 so với 1, độ trôi):"
  log "  $PY scripts/check_pilot.py $RESULTS/tn1_*_$TS.csv"
fi
