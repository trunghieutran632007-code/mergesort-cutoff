#!/usr/bin/env bash
# Ghi cấu hình máy vào results/machine.txt (macOS).
# Chạy lại trước mỗi đợt đo chính thức để số liệu đi kèm đúng cấu hình.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/results/machine.txt"
source "$ROOT/scripts/config.sh"
{
  echo "# Cấu hình máy, ghi lúc $(date '+%Y-%m-%d %H:%M:%S')"
  echo
  echo "## Hệ điều hành"
  sw_vers
  echo
  echo "## CPU"
  echo "Model: $(sysctl -n machdep.cpu.brand_string)"
  echo "Mã máy: $(sysctl -n hw.model)"
  echo "Kiến trúc: $(uname -m)"
  echo "Số nhân vật lý: $(sysctl -n hw.physicalcpu)"
  echo "Số luồng logic: $(sysctl -n hw.logicalcpu)"
  if sysctl -n hw.perflevel0.physicalcpu >/dev/null 2>&1; then
    echo "Nhân hiệu năng (P-core): $(sysctl -n hw.perflevel0.physicalcpu)"
    echo "Nhân tiết kiệm (E-core): $(sysctl -n hw.perflevel1.physicalcpu 2>/dev/null || echo 0)"
  fi
  echo
  echo "## Bộ nhớ"
  MEM_BYTES="$(sysctl -n hw.memsize 2>/dev/null || echo 0)"
  echo "RAM: $(( MEM_BYTES / 1024 / 1024 / 1024 )) GB"
  echo
  echo "## Java"
  java -version 2>&1 || echo "Chưa cài Java"
  echo
  echo "## Python"
  python3 --version 2>&1 || echo "Chưa cài Python 3"
  echo
  echo "## Nguồn điện lúc ghi"
  pmset -g ps | head -1
  echo
  echo "## JVM flags dùng khi đo"
  echo "$JVM_FLAGS"
  echo "(lấy từ scripts/config.sh; mỗi lần chạy Benchmark còn ghi cờ thực tế vào file .meta.txt đi kèm CSV)"
} > "$OUT"
echo "Đã ghi $OUT:"
echo
cat "$OUT"
