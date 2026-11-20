#!/usr/bin/env bash
# Bước 4: chạy thử (pilot) harness đo thời gian.
#   random N = 10^5 và 10^6, cutoffs 0,1,5,10,20, 5 trials, warm-up 50.
#   Mỗi N chạy trong một tiến trình JVM riêng, cờ JVM lấy từ scripts/config.sh.
# Đầu ra (cùng một timestamp cho cả đợt):
#   results/pilot_random_<N>_<timestamp>.csv      số liệu thô
#   results/pilot_random_<N>_<timestamp>.meta.txt tham số, K, cờ JVM, thời gian chạy
#   results/pilot_<timestamp>.log                 toàn bộ những gì in ra màn hình
# Sau đó tự chạy scripts/check_pilot.py để kiểm tra 4 điều trong kế hoạch (nếu có .venv).
#
# Trước khi chạy: cắm sạc, tắt trình duyệt và ứng dụng nặng, không dùng máy trong lúc đo.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
source scripts/config.sh

TS="$(date +%Y%m%d_%H%M%S)"
LOG="results/pilot_$TS.log"
SIZES="100000 1000000"
CUTOFFS="0,1,5,10,20"
TRIALS=5
WARMUP=50

for N in $SIZES; do
  if [ ! -f "data/random_$N.bin" ]; then
    echo "Thiếu data/random_$N.bin. Chạy scripts/gen_data.sh trước." >&2
    exit 1
  fi
done

echo "Biên dịch src/ vào out/ ..."
compile_java

{
  echo "# Pilot $TS"
  echo "Nguồn điện: $(pmset -g ps 2>/dev/null | head -1 || echo 'không rõ')"
  echo "JVM flags: $JVM_FLAGS"
  echo "Cutoffs: $CUTOFFS | trials: $TRIALS | warm-up: $WARMUP | N: $SIZES"
  echo
} | tee "$LOG"

for N in $SIZES; do
  START=$SECONDS
  $KEEP_AWAKE java $JVM_FLAGS -cp out Benchmark \
    --exp pilot --data "data/random_$N.bin" \
    --cutoffs "$CUTOFFS" --trials "$TRIALS" --warmup "$WARMUP" \
    --out "results/pilot_random_${N}_$TS.csv" 2>&1 | tee -a "$LOG"
  echo "Tiến trình JVM cho N = $N chạy hết $((SECONDS - START)) s (kể cả khởi động JVM)" | tee -a "$LOG"
  echo | tee -a "$LOG"
done

echo "Log: $LOG"
if [ -x .venv/bin/python ]; then
  echo
  .venv/bin/python scripts/check_pilot.py results/pilot_random_*_"$TS".csv | tee -a "$LOG"
else
  echo "Không thấy .venv/bin/python; kiểm tra bằng: python3 scripts/check_pilot.py results/pilot_random_*_$TS.csv"
fi
