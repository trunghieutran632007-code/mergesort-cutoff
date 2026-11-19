import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;

/**
 * Bước 3: sinh bộ dữ liệu thí nghiệm.
 *
 * Năm phân bố:
 *   random       số nguyên ngẫu nhiên đều trên toàn miền int (Random.nextInt())
 *   sorted       0, 1, ..., N-1
 *   reversed     N-1, ..., 0
 *   nearly       0, 1, ..., N-1 rồi thực hiện N/100 lần hoán đổi hai vị trí chọn ngẫu nhiên
 *                (nên tối đa khoảng 2% vị trí bị lệch chỗ)
 *   fewdistinct  giá trị ngẫu nhiên trong 0..9
 *
 * Seed: mỗi (phân bố, N) có một seed cố định
 *   seed = seedBase * 10^9 + mãPhânBố * 10^8 + N
 *   mã: random 0, sorted 1, reversed 2, nearly 3, fewdistinct 4
 * Ví dụ seedBase = 20261109, random, N = 10^6 -> seed = 20261109001000000.
 * sorted và reversed không dùng seed (dữ liệu cố định) nhưng vẫn ghi seed cho thống nhất.
 *
 * Đầu ra cho mỗi (phân bố, N), trong thư mục --out (mặc định data/):
 *   <dist>_<N>.bin   định dạng nhị phân, xem DataIO
 *   <dist>_<N>.txt   chỉ khi N <= 10000, để xem bằng mắt
 *   một dòng trong manifest.csv: file,dist,n,seed,sha256 (dòng cũ cùng tên file được thay thế)
 * Sau khi ghi, file .bin được đọc lại bằng DataIO.read và so với mảng gốc.
 * Nếu manifest đã có dòng cho file đó thì so SHA-256 mới với cũ: khớp nghĩa là tái tạo đúng.
 *
 * Cách dùng (từ thư mục gốc, sau khi javac -d out src/*.java):
 *   java -cp out DataGen --dist random,sorted --n 10000,1000000 [--seed-base 20261109] [--out data]
 * Thông thường chỉ cần chạy scripts/gen_data.sh.
 */
public final class DataGen {

    private static final String[] DISTS = {"random", "sorted", "reversed", "nearly", "fewdistinct"};
    private static final long DEFAULT_SEED_BASE = 20261109L;
    private static final int TEXT_MAX_N = 10_000;
    private static final int MAX_N = 99_999_999; // để N không lấn sang phần mã phân bố trong seed
    private static final String HEADER = "file,dist,n,seed,sha256";

    private DataGen() {}

    public static void main(String[] args) {
        List<String> dists = new ArrayList<>();
        List<Integer> sizes = new ArrayList<>();
        long seedBase = DEFAULT_SEED_BASE;
        Path outDir = Path.of("data");

        try {
            for (int i = 0; i < args.length; i++) {
                String value = (i + 1 < args.length) ? args[i + 1] : null;
                switch (args[i]) {
                    case "--dist" -> { dists.addAll(Arrays.asList(need(value, "--dist").split(","))); i++; }
                    case "--n" -> {
                        for (String s : need(value, "--n").split(",")) sizes.add(Integer.parseInt(s.trim()));
                        i++;
                    }
                    case "--seed-base" -> { seedBase = Long.parseLong(need(value, "--seed-base")); i++; }
                    case "--out" -> { outDir = Path.of(need(value, "--out")); i++; }
                    default -> throw new IllegalArgumentException("Tham số không rõ: " + args[i]);
                }
            }
            if (dists.isEmpty() || sizes.isEmpty()) {
                throw new IllegalArgumentException("Cần ít nhất một --dist và một --n");
            }
            for (String d : dists) distCode(d);
            for (int n : sizes) {
                if (n < 0 || n > MAX_N) throw new IllegalArgumentException("N phải trong 0.." + MAX_N + ": " + n);
            }
        } catch (IllegalArgumentException e) {
            System.out.println("Lỗi tham số: " + e.getMessage());
            System.out.println("Cách dùng: java -cp out DataGen --dist random,sorted --n 10000,1000000"
                    + " [--seed-base " + DEFAULT_SEED_BASE + "] [--out data]");
            System.out.println("Phân bố hợp lệ: " + String.join(", ", DISTS));
            System.exit(1);
        }

        try {
            int mismatches = run(dists, sizes, seedBase, outDir);
            if (mismatches > 0) {
                System.out.println("CẢNH BÁO: " + mismatches + " file cùng seed nhưng SHA-256 khác manifest cũ."
                        + " Generator đã thay đổi nên dữ liệu cũ không còn tái tạo được.");
                System.exit(2);
            }
        } catch (IOException e) {
            System.out.println("Lỗi đọc/ghi: " + e.getMessage());
            System.exit(1);
        }
    }

    /** Sinh mọi tổ hợp (phân bố, N). Trả về số file có cùng seed nhưng SHA-256 khác manifest cũ. */
    private static int run(List<String> dists, List<Integer> sizes, long seedBase, Path outDir) throws IOException {
        Files.createDirectories(outDir);
        Path manifestPath = outDir.resolve("manifest.csv");
        Map<String, String[]> manifest = readManifest(manifestPath);
        int mismatches = 0;

        for (String dist : dists) {
            for (int n : sizes) {
                long seed = seedFor(seedBase, dist, n);
                String name = dist + "_" + n;
                String binFile = name + ".bin";
                String binPath = outDir.resolve(binFile).toString();

                int[] a = generate(dist, n, seed);
                String sha = DataIO.write(binPath, a);
                if (!Arrays.equals(DataIO.read(binPath), a)) {
                    throw new IOException(binPath + ": đọc lại bằng DataIO.read không khớp dữ liệu vừa ghi");
                }
                if (n <= TEXT_MAX_N) {
                    DataIO.writeText(outDir.resolve(name + ".txt").toString(), a);
                }

                String status;
                String[] old = manifest.get(binFile);
                if (old == null) {
                    status = "mới";
                } else if (old[4].equals(sha)) {
                    status = "khớp manifest cũ";
                } else if (old[3].equals(Long.toString(seed))) {
                    status = "KHÁC manifest cũ dù cùng seed!";
                    mismatches++;
                } else {
                    status = "seed đổi (" + old[3] + " -> " + seed + ")";
                }

                manifest.put(binFile, new String[]{binFile, dist, Integer.toString(n), Long.toString(seed), sha});
                writeManifest(manifestPath, manifest); // ghi sau mỗi file để không mất dòng nếu bị dừng giữa chừng

                System.out.printf("%-26s n=%-9d seed=%-18d sha256=%s…  %s%s%n",
                        binFile, n, seed, sha.substring(0, 16), status, n <= TEXT_MAX_N ? "  (+ .txt)" : "");
            }
        }
        return mismatches;
    }

    // ------------------------------------------------------------------
    // Sinh dữ liệu
    // ------------------------------------------------------------------

    static long seedFor(long seedBase, String dist, int n) {
        return seedBase * 1_000_000_000L + distCode(dist) * 100_000_000L + n;
    }

    static int[] generate(String dist, int n, long seed) {
        Random r = new Random(seed);
        int[] a = new int[n];
        switch (dist) {
            case "random" -> { for (int i = 0; i < n; i++) a[i] = r.nextInt(); }
            case "sorted" -> { for (int i = 0; i < n; i++) a[i] = i; }
            case "reversed" -> { for (int i = 0; i < n; i++) a[i] = n - 1 - i; }
            case "nearly" -> {
                for (int i = 0; i < n; i++) a[i] = i;
                int swaps = n / 100;
                for (int s = 0; s < swaps; s++) {
                    int i = r.nextInt(n), j = r.nextInt(n);
                    int tmp = a[i]; a[i] = a[j]; a[j] = tmp;
                }
            }
            case "fewdistinct" -> { for (int i = 0; i < n; i++) a[i] = r.nextInt(10); }
            default -> throw new IllegalArgumentException("Phân bố không rõ: " + dist);
        }
        return a;
    }

    private static int distCode(String dist) {
        for (int i = 0; i < DISTS.length; i++) {
            if (DISTS[i].equals(dist)) return i;
        }
        throw new IllegalArgumentException("Phân bố không rõ: " + dist);
    }

    // ------------------------------------------------------------------
    // manifest.csv
    // ------------------------------------------------------------------

    private static Map<String, String[]> readManifest(Path p) throws IOException {
        Map<String, String[]> rows = new LinkedHashMap<>();
        if (!Files.exists(p)) return rows;
        List<String> lines = Files.readAllLines(p, StandardCharsets.UTF_8);
        for (int i = 1; i < lines.size(); i++) { // bỏ dòng tiêu đề
            String line = lines.get(i).trim();
            if (line.isEmpty()) continue;
            String[] f = line.split(",");
            if (f.length != 5) throw new IOException(p + " dòng " + (i + 1) + " không đúng 5 cột: " + line);
            rows.put(f[0], f);
        }
        return rows;
    }

    /** Ghi manifest, sắp theo thứ tự phân bố trong DISTS rồi theo N tăng dần. */
    private static void writeManifest(Path p, Map<String, String[]> rows) throws IOException {
        List<String[]> sorted = new ArrayList<>(rows.values());
        sorted.sort(Comparator.<String[]>comparingInt(f -> distOrder(f[1]))
                .thenComparingLong(f -> Long.parseLong(f[2])));
        StringBuilder sb = new StringBuilder(HEADER).append('\n');
        for (String[] f : sorted) sb.append(String.join(",", f)).append('\n');

        Path tmp = p.resolveSibling(p.getFileName() + ".tmp");
        Files.writeString(tmp, sb.toString(), StandardCharsets.UTF_8);
        Files.move(tmp, p, StandardCopyOption.REPLACE_EXISTING);
    }

    private static int distOrder(String dist) {
        for (int i = 0; i < DISTS.length; i++) {
            if (DISTS[i].equals(dist)) return i;
        }
        return DISTS.length;
    }

    private static String need(String value, String flag) {
        if (value == null) throw new IllegalArgumentException("Thiếu giá trị sau " + flag);
        return value;
    }
}
