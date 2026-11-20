# Cấu hình chung cho các script đo thời gian (Bước 4, 5).
# Dùng trong script khác:  source "$ROOT/scripts/config.sh"   (cần biến ROOT = thư mục gốc project)
# Đổi cờ JVM ở đây rồi chạy lại scripts/machine_info.sh để results/machine.txt ghi đúng cờ đang dùng.

# Nguyên tắc 6 (cố định JVM), máy 16 GB RAM: heap cố định 4 GB (-Xms = -Xmx)
# để JVM không co giãn heap giữa chừng. GC giữ mặc định của JDK (G1).
JVM_FLAGS="-Xms4g -Xmx4g"

# Không cho máy ngủ khi đang đo (macOS: caffeinate). Máy không có caffeinate thì bỏ qua.
if command -v caffeinate >/dev/null 2>&1; then
  KEEP_AWAKE="caffeinate -i"
else
  KEEP_AWAKE=""
fi

# Biên dịch toàn bộ src/ vào out/
compile_java() {
  javac -encoding UTF-8 -d "$ROOT/out" "$ROOT"/src/*.java
}
