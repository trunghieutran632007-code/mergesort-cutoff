#!/usr/bin/env bash
# Sinh toàn bộ dữ liệu cho các thí nghiệm (Bước 3), ghi vào data/ và data/manifest.csv.
#   TN1: random N = 10^4, 10^5, 10^6, 10^7
#   TN5: random N = 2^17 .. 2^23 (doubling test)
#   TN2: sorted, reversed, nearly, fewdistinct N = 10^6
#   Thêm: sorted, reversed, nearly, fewdistinct N = 10^4 (kèm .txt) để xem bằng mắt từng phân bố.
# Seed cố định nên chạy lại bao nhiêu lần cũng ra đúng dữ liệu cũ;
# DataGen báo SHA-256 của từng file có khớp với data/manifest.csv không.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

SEED_BASE=20261109

echo "Biên dịch src/ vào out/ ..."
javac -encoding UTF-8 -d out src/*.java

DOUBLING=""
for k in $(seq 17 23); do DOUBLING="$DOUBLING,$((2 ** k))"; done

gen() { java -Xmx2g -cp out DataGen --seed-base "$SEED_BASE" --out data "$@"; }

echo "Sinh dữ liệu, seed gốc = $SEED_BASE"
gen --dist random --n "10000,100000,1000000,10000000$DOUBLING"
gen --dist sorted,reversed,nearly,fewdistinct --n 10000,1000000

echo
echo "Dung lượng data/: $(du -sh data | cut -f1)"
echo "Manifest: data/manifest.csv"
