# Project: Thí nghiệm CUTOFF cho Mergesort (môn CTDL&GT, UET)

Kế hoạch chi tiết từng bước: xem ke-hoach-mergesort-cutoff.md ở thư mục gốc.
Máy đo: macOS, cấu hình ghi trong results/machine.txt.

## Quy tắc bắt buộc
- src/Merge.java và src/MergeCount.java do tôi tự viết từ bài giảng.
  KHÔNG viết mới, sửa, refactor hay "tối ưu" các file này.
  Nếu thấy lỗi: chỉ mô tả lỗi và vị trí để tôi tự sửa.
- Không dùng hay tham khảo cài đặt mergesort khác (algs4 Merge/MergeX, mã trên mạng).
  Arrays.sort chỉ được dùng trong test để đối chiếu kết quả.
- Được phép: test tính đúng, harness đo thời gian, script sinh dữ liệu,
  script phân tích và vẽ đồ thị, góp ý báo cáo.

## Quy ước
- Java chuẩn: System.out.println, Scanner/BufferedReader.
  Không dùng thư viện algs4 (StdIn, StdOut, StdRandom).
- Python 3 + pandas, matplotlib, scipy cho phân tích (môi trường ảo .venv).
- API: Merge.sort(int[] a, int cutoff). Đoạn con có độ dài <= cutoff thì dùng insertion sort.
  cutoff = 0 nghĩa là không dùng insertion sort (baseline).
- Dữ liệu ngẫu nhiên luôn sinh bằng seed cố định, ghi seed vào output.
- Kết quả đo ghi CSV thô vào results/, tên file có timestamp, không ghi đè file cũ.
