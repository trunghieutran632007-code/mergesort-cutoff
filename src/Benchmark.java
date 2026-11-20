import java.io.BufferedWriter;
import java.io.IOException;
import java.lang.management.CompilationMXBean;
import java.lang.management.GarbageCollectorMXBean;
import java.lang.management.ManagementFactory;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.nio.file.StandardOpenOption;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Random;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Bước 4: harness đo thời gian Merge.sort(int[] a, int cutoff).
 *
 * Bảy nguyên tắc đo (ke-hoach-mergesort-cutoff.md, Bước 4) và cách harness thực hiện:
 *   1. Warm-up: trước khi đo, sort ít nhất --warmup lần (mặc định 50), xoay vòng qua mọi cutoff
 *      trong danh sách, và kéo dài ít nhất 1 giây để JIT biên dịch xong cả khi N nhỏ
 *      (50 lần sort N = 10^4 chỉ mất khoảng 25 ms).
 *   2. Cùng input: mọi phép sort chạy trên bản sao của cùng một mảng gốc đọc từ --data.
 *      Việc chép (System.arraycopy vào mảng cấp phát sẵn, tương đương clone) nằm ngoài vùng tính giờ.
 *   3. Nhiều trial, thứ tự ngẫu nhiên: --trials trial (mặc định 30); mỗi trial trộn thứ tự các cutoff
 *      bằng Random(--seed), nên chạy lại với cùng seed thì ra cùng thứ tự.
 *   4. Đo theo lô: mỗi phép đo sort K bản sao chuẩn bị sẵn rồi chia thời gian cho K.
 *      K chọn sau warm-up sao cho K lần sort với cutoff nhanh nhất kéo dài ít nhất --min-ms (mặc định 20 ms);
 *      N lớn (một lần sort đã >= 20 ms) thì K = 1. Mọi cutoff dùng chung một K.
 *   5. Kiểm tra kết quả: sau mỗi phép đo (ngoài vùng tính giờ), mọi bản sao phải qua Merge.isSorted.
 *      Sai thì dừng chương trình với mã thoát 3. Warm-up cũng được kiểm tra như vậy.
 *   6. Cố định JVM: cờ heap do script chạy truyền vào (scripts/config.sh: -Xms4g -Xmx4g);
 *      cờ thực tế được ghi vào file .meta.txt. Mỗi lần chạy harness là một tiến trình JVM riêng.
 *   7. Ghi số liệu thô: mỗi phép đo một dòng CSV, không tính trung bình trong Java.
 *
 * Cột CSV:
 *   experiment, dist, n, cutoff, trial, k, ns_per_sort   (theo kế hoạch; ns_per_sort = thời gian lô / K)
 *   pos   vị trí của phép đo này trong thứ tự đã trộn của trial (1 = đo đầu tiên)
 *   gc    số lần GC xảy ra trong vùng tính giờ (thường là 0; khác 0 thì phép đo đó có thể bị chậm)
 * Kèm theo là file cùng tên, đuôi .meta.txt (key=value): tham số, seed trộn, K, cờ JVM, phiên bản Java,
 * SHA-256 dữ liệu đối chiếu data/manifest.csv, thời gian warm-up/đo, thời gian JIT lúc đo.
 *
 * Harness chỉ gọi Merge.sort và Merge.isSorted, không tự cài thuật toán sắp xếp nào.
 * Các hàm tiện ích (đọc tham số, manifest, file meta, đếm GC/JIT) để mức package, không private,
 * để CompareCount (TN3) và SmallBench (TN4) dùng lại.
 *
 * Cách dùng (từ thư mục gốc, sau khi javac -encoding UTF-8 -d out src/*.java):
 *   java -Xms4g -Xmx4g -cp out Benchmark --exp tn1 --data data/random_1000000.bin
 *        [--cutoffs 0-30,40,50,64] [--trials 30] [--warmup 50] [--min-ms 20] [--seed 20261109]
 *        [--out results/<tên>_<timestamp>.csv]
 * Mặc định --out là results/<exp>_<dist>_<n>_<yyyyMMdd_HHmmss>.csv. File đã tồn tại thì không ghi đè.
 * Mã thoát: 0 xong, 1 lỗi tham số hoặc đọc/ghi, 3 sort cho kết quả sai.
 */
public final class Benchmark {

    private static final String DEFAULT_CUTOFFS = "0-30,40,50,64";
    static final long DEFAULT_SEED = 20261109L;
    static final long WARMUP_MIN_NS = 1_000_000_000L; // warm-up kéo dài ít nhất 1 giây
    private static final long MAX_K = 1_000_000L;
    private static final long MAX_BUFFER_BYTES = 1L << 30; // tổng K bản sao không quá 1 GB
    private static final String CSV_HEADER = "experiment,dist,n,cutoff,trial,k,ns_per_sort,pos,gc";
    private static final Pattern DATA_NAME = Pattern.compile("([A-Za-z]+)_(\\d{1,10})\\.bin");
    static final DateTimeFormatter STAMP = DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss");
    private static final String USAGE = "Cách dùng: java -Xms4g -Xmx4g -cp out Benchmark --exp <tên> --data <file .bin>"
            + " [--cutoffs " + DEFAULT_CUTOFFS + "] [--trials 30] [--warmup 50] [--min-ms 20]"
            + " [--seed " + DEFAULT_SEED + "] [--out <file .csv>]";

    private static final List<GarbageCollectorMXBean> GCS = ManagementFactory.getGarbageCollectorMXBeans();
    private static final CompilationMXBean JIT = ManagementFactory.getCompilationMXBean();

    private Benchmark() {}

    /** Tham số dòng lệnh, kèm giá trị mặc định. */
    private static final class Options {
        String data;
        String exp;
        String cutoffSpec = DEFAULT_CUTOFFS;
        int[] cutoffs;
        int trials = 30;
        int warmup = 50;
        double minMs = 20;
        long seed = DEFAULT_SEED;
        String out;
    }

    /** Sort cho kết quả sai: dừng toàn bộ thí nghiệm. */
    private static final class SortError extends RuntimeException {
        SortError(String message) { super(message); }
    }

    record ManifestInfo(String status, String seed) {}

    public static void main(String[] args) {
        Options o;
        try {
            o = parse(args);
        } catch (IllegalArgumentException e) {
            System.out.println("Lỗi tham số: " + e.getMessage());
            System.out.println(USAGE);
            System.exit(1);
            return;
        }
        try {
            run(o);
        } catch (SortError e) {
            System.out.println("SORT SAI, dừng thí nghiệm: " + e.getMessage());
            System.exit(3);
        } catch (IOException | IllegalStateException e) {
            System.out.println("Lỗi: " + e.getMessage());
            System.exit(1);
        }
    }

    // ------------------------------------------------------------------
    // Chạy thí nghiệm
    // ------------------------------------------------------------------

    private static void run(Options o) throws IOException {
        LocalDateTime start = LocalDateTime.now();
        Path dataPath = Path.of(o.data);
        int[] original = DataIO.read(o.data);
        int n = original.length;
        String dist = distFromFileName(dataPath.getFileName().toString(), n);
        String sha = DataIO.sha256(o.data);
        ManifestInfo manifest = checkManifest(dataPath, sha);

        Path out = Path.of(o.out != null ? o.out
                : "results/" + o.exp + "_" + dist + "_" + n + "_" + start.format(STAMP) + ".csv");
        Path metaPath = metaPathFor(out);
        if (Files.exists(out)) throw new IOException(out + " đã tồn tại, không ghi đè. Chọn --out khác.");
        if (Files.exists(metaPath)) throw new IOException(metaPath + " đã tồn tại, không ghi đè. Chọn --out khác.");
        if (out.toAbsolutePath().getParent() != null) Files.createDirectories(out.toAbsolutePath().getParent());

        int[] cutoffs = o.cutoffs;
        int m = cutoffs.length;
        Map<String, String> meta = new LinkedHashMap<>();
        meta.put("experiment", o.exp);
        meta.put("status", "đang chạy");
        meta.put("start", start.toString());
        meta.put("data", o.data);
        meta.put("dist", dist);
        meta.put("n", Integer.toString(n));
        meta.put("data_sha256", sha);
        meta.put("manifest", manifest.status());
        meta.put("data_seed", manifest.seed());
        meta.put("cutoffs", joinInts(cutoffs));
        meta.put("trials", Integer.toString(o.trials));
        meta.put("warmup_min_sorts", Integer.toString(o.warmup));
        meta.put("min_batch_ms", fmt("%.1f", o.minMs));
        meta.put("shuffle_seed", Long.toString(o.seed));
        meta.put("jvm_args", String.join(" ", ManagementFactory.getRuntimeMXBean().getInputArguments()));
        meta.put("java_version", System.getProperty("java.version"));
        meta.put("java_vm", System.getProperty("java.vm.name") + " " + System.getProperty("java.vm.version"));
        meta.put("os", System.getProperty("os.name") + " " + System.getProperty("os.version")
                + " " + System.getProperty("os.arch"));
        meta.put("cpus", Integer.toString(Runtime.getRuntime().availableProcessors()));
        meta.put("max_heap_mb", Long.toString(Runtime.getRuntime().maxMemory() / (1024 * 1024)));
        meta.put("csv", out.toString());

        String tag = "[" + o.exp + " " + dist + " n=" + n + "]";
        System.out.println("Benchmark " + tag);
        System.out.println("  dữ liệu : " + o.data + " (" + manifest.status() + ")");
        System.out.println("  cutoffs : " + joinInts(cutoffs) + "  (" + m + " giá trị)");
        System.out.println("  trials = " + o.trials + ", seed trộn = " + o.seed);
        System.out.println("  JVM     : " + meta.get("jvm_args") + " | Java " + meta.get("java_version")
                + " | heap tối đa " + meta.get("max_heap_mb") + " MB");
        writeMeta(metaPath, meta);

        try {
            // ---- 1. Warm-up, đồng thời lấy thời gian sort nhanh nhất của từng cutoff để chọn K ----
            long jitStart = jitMillis();
            long warmStart = System.nanoTime();
            long[] fastest = new long[m];
            Arrays.fill(fastest, Long.MAX_VALUE);
            int[] work = new int[n];
            int minSorts = Math.max(o.warmup, m); // mỗi cutoff ít nhất một lần
            int warmSorts = 0;
            while (warmSorts < minSorts || System.nanoTime() - warmStart < WARMUP_MIN_NS) {
                int idx = warmSorts % m;
                System.arraycopy(original, 0, work, 0, n);
                long t0 = System.nanoTime();
                Merge.sort(work, cutoffs[idx]);
                long t = System.nanoTime() - t0;
                if (t < fastest[idx]) fastest[idx] = t;
                verify(work, "warm-up", cutoffs[idx], 0);
                warmSorts++;
            }
            double warmSeconds = (System.nanoTime() - warmStart) / 1e9;
            long jitWarm = jitMillis() - jitStart;
            long fastestNs = Math.max(1, Arrays.stream(fastest).min().getAsLong());

            // ---- 4. Chọn K ----
            long k = Math.max(1, (long) Math.ceil(o.minMs * 1e6 / fastestNs));
            if (k > MAX_K || k * 4L * n > MAX_BUFFER_BYTES) {
                throw new IllegalStateException("K = " + k + " bản sao của " + n + " phần tử là quá nhiều"
                        + " (tối đa " + MAX_K + " bản sao, " + (MAX_BUFFER_BYTES >> 20) + " MB); giảm --min-ms");
            }
            String kNote = fmt("sort nhanh nhất lúc warm-up %.3f ms, mỗi phép đo >= %.0f ms", fastestNs / 1e6, o.minMs);
            meta.put("warmup_sorts", Integer.toString(warmSorts));
            meta.put("warmup_seconds", fmt("%.3f", warmSeconds));
            meta.put("warmup_fastest_ms", fmt("%.4f", fastestNs / 1e6));
            meta.put("jit_ms_warmup", Long.toString(jitWarm));
            meta.put("k", Long.toString(k));
            System.out.printf(Locale.ROOT, "  warm-up : %d lần sort, %.2f s, JIT %d ms%n", warmSorts, warmSeconds, jitWarm);
            System.out.println("  K = " + k + " (" + kNote + ")");
            System.out.println("  ghi vào : " + out);

            int kk = (int) k;
            int[][] buf = new int[kk][];
            buf[0] = work;
            for (int j = 1; j < kk; j++) buf[j] = new int[n];

            // ---- 2, 3, 5, 7. Đo: mỗi trial một thứ tự cutoff ngẫu nhiên ----
            Random rng = new Random(o.seed);
            long jitMeasureStart = jitMillis();
            long measureStart = System.nanoTime();
            long gcInTimed = 0;
            int measurements = 0;
            try (BufferedWriter w = Files.newBufferedWriter(out, StandardCharsets.UTF_8,
                    StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE)) {
                w.write(CSV_HEADER);
                w.newLine();
                for (int trial = 1; trial <= o.trials; trial++) {
                    int[] order = cutoffs.clone();
                    shuffle(order, rng);
                    for (int pos = 0; pos < m; pos++) {
                        int c = order[pos];
                        for (int j = 0; j < kk; j++) System.arraycopy(original, 0, buf[j], 0, n);

                        long gc0 = gcCount();
                        long t0 = System.nanoTime();
                        for (int j = 0; j < kk; j++) Merge.sort(buf[j], c);
                        long elapsed = System.nanoTime() - t0;
                        long gc = gcCount() - gc0;

                        for (int j = 0; j < kk; j++) verify(buf[j], "đo", c, trial);
                        gcInTimed += gc;
                        measurements++;
                        w.write(o.exp + "," + dist + "," + n + "," + c + "," + trial + "," + kk + ","
                                + fmt("%.1f", (double) elapsed / kk) + "," + (pos + 1) + "," + gc);
                        w.newLine();
                    }
                    w.flush(); // dừng giữa chừng vẫn giữ được các trial đã xong
                    double done = (System.nanoTime() - measureStart) / 1e9;
                    double left = done / trial * (o.trials - trial);
                    System.out.printf(Locale.ROOT, "%s trial %d/%d xong  (đã đo %.1f s, còn khoảng %.1f s)%n",
                            tag, trial, o.trials, done, left);
                }
            }
            double measureSeconds = (System.nanoTime() - measureStart) / 1e9;
            long jitMeasure = jitMillis() - jitMeasureStart;

            meta.put("status", "ok");
            meta.put("end", LocalDateTime.now().toString());
            meta.put("measurements", Integer.toString(measurements));
            meta.put("measure_seconds", fmt("%.3f", measureSeconds));
            meta.put("jit_ms_measure", Long.toString(jitMeasure));
            meta.put("gc_in_timed", Long.toString(gcInTimed));
            meta.put("jvm_uptime_seconds", fmt("%.3f", ManagementFactory.getRuntimeMXBean().getUptime() / 1e3));
            writeMeta(metaPath, meta);

            System.out.printf(Locale.ROOT, "Xong %s: %d phép đo trong %.1f s, warm-up %.1f s.%n",
                    tag, measurements, measureSeconds, warmSeconds);
            System.out.println("  JIT biên dịch thêm trong lúc đo: " + jitMeasure + " ms"
                    + " | GC trong vùng tính giờ: " + gcInTimed + " lần"
                    + (gcInTimed > 0 ? "  <- xem cột gc để biết phép đo nào bị ảnh hưởng" : ""));
            System.out.println("  CSV : " + out);
            System.out.println("  meta: " + metaPath);
        } catch (SortError | IOException | IllegalStateException e) {
            meta.put("status", "LỖI: " + e.getMessage());
            meta.put("end", LocalDateTime.now().toString());
            writeMeta(metaPath, meta);
            throw e;
        }
    }

    /** Kiểm tra một bản sao sau khi sort (nguyên tắc 5). */
    private static void verify(int[] a, String phase, int cutoff, int trial) {
        if (!Merge.isSorted(a)) {
            throw new SortError("Merge.isSorted trả về false (" + phase + ", cutoff = " + cutoff
                    + (trial > 0 ? ", trial = " + trial : "") + ", n = " + a.length + ")");
        }
    }

    /** Trộn Fisher–Yates. */
    static void shuffle(int[] a, Random r) {
        for (int i = a.length - 1; i > 0; i--) {
            int j = r.nextInt(i + 1);
            int t = a[i];
            a[i] = a[j];
            a[j] = t;
        }
    }

    static long gcCount() {
        long total = 0;
        for (GarbageCollectorMXBean gc : GCS) {
            long c = gc.getCollectionCount();
            if (c > 0) total += c;
        }
        return total;
    }

    /** Tổng thời gian JIT đã biên dịch (ms), -1 nếu JVM không hỗ trợ đo. */
    static long jitMillis() {
        return (JIT != null && JIT.isCompilationTimeMonitoringSupported()) ? JIT.getTotalCompilationTime() : -1;
    }

    // ------------------------------------------------------------------
    // Dữ liệu, manifest, file kết quả
    // ------------------------------------------------------------------

    /** Lấy tên phân bố từ tên file <dist>_<N>.bin và kiểm tra N trong tên khớp số phần tử. */
    static String distFromFileName(String fileName, int n) throws IOException {
        Matcher mt = DATA_NAME.matcher(fileName);
        if (!mt.matches()) {
            return fileName.replaceFirst("\\.bin$", "").replaceAll("[^A-Za-z0-9]", "_");
        }
        if (Long.parseLong(mt.group(2)) != n) {
            throw new IOException(fileName + ": tên file ghi N = " + mt.group(2) + " nhưng file chứa " + n + " phần tử");
        }
        return mt.group(1);
    }

    /** Đối chiếu SHA-256 của file dữ liệu với manifest.csv cùng thư mục. Khác manifest thì báo lỗi. */
    static ManifestInfo checkManifest(Path dataPath, String sha) throws IOException {
        Path manifest = dataPath.toAbsolutePath().getParent().resolve("manifest.csv");
        if (!Files.exists(manifest)) return new ManifestInfo("không có manifest.csv", "");
        String fileName = dataPath.getFileName().toString();
        for (String line : Files.readAllLines(manifest, StandardCharsets.UTF_8)) {
            String[] f = line.trim().split(",");
            if (f.length == 5 && f[0].equals(fileName)) {
                if (!f[4].equals(sha)) {
                    throw new IOException(fileName + ": SHA-256 " + sha + " khác manifest (" + f[4]
                            + "). Dữ liệu đã bị thay đổi; sinh lại bằng scripts/gen_data.sh.");
                }
                return new ManifestInfo("SHA-256 khớp manifest, seed " + f[3], f[3]);
            }
        }
        return new ManifestInfo("không có trong manifest", "");
    }

    static Path metaPathFor(Path csv) {
        String name = csv.getFileName().toString().replaceFirst("\\.csv$", "");
        return csv.resolveSibling(name + ".meta.txt");
    }

    static void writeMeta(Path p, Map<String, String> meta) throws IOException {
        StringBuilder sb = new StringBuilder("# Thông tin lần chạy (key=value), đi kèm ")
                .append(meta.get("csv")).append('\n');
        for (Map.Entry<String, String> e : meta.entrySet()) {
            sb.append(e.getKey()).append('=').append(e.getValue().replace('\n', ' ')).append('\n');
        }
        Path tmp = p.resolveSibling(p.getFileName() + ".tmp");
        Files.writeString(tmp, sb.toString(), StandardCharsets.UTF_8);
        Files.move(tmp, p, StandardCopyOption.REPLACE_EXISTING);
    }

    // ------------------------------------------------------------------
    // Tham số dòng lệnh
    // ------------------------------------------------------------------

    private static Options parse(String[] args) {
        Options o = new Options();
        for (int i = 0; i < args.length; i++) {
            String value = (i + 1 < args.length) ? args[i + 1] : null;
            switch (args[i]) {
                case "--data" -> { o.data = need(value, "--data"); i++; }
                case "--exp" -> { o.exp = need(value, "--exp"); i++; }
                case "--cutoffs" -> { o.cutoffSpec = need(value, "--cutoffs"); i++; }
                case "--trials" -> { o.trials = atLeast(need(value, "--trials"), 1, "--trials"); i++; }
                case "--warmup" -> { o.warmup = atLeast(need(value, "--warmup"), 0, "--warmup"); i++; }
                case "--min-ms" -> {
                    o.minMs = Double.parseDouble(need(value, "--min-ms"));
                    if (!(o.minMs > 0)) throw new IllegalArgumentException("--min-ms phải > 0");
                    i++;
                }
                case "--seed" -> { o.seed = Long.parseLong(need(value, "--seed")); i++; }
                case "--out" -> { o.out = need(value, "--out"); i++; }
                default -> throw new IllegalArgumentException("Tham số không rõ: " + args[i]);
            }
        }
        if (o.data == null) throw new IllegalArgumentException("Thiếu --data <file .bin>");
        if (o.exp == null) throw new IllegalArgumentException("Thiếu --exp <tên thí nghiệm>");
        if (!o.exp.matches("[A-Za-z0-9_-]+")) {
            throw new IllegalArgumentException("--exp chỉ gồm chữ, số, '_' hoặc '-': " + o.exp);
        }
        o.cutoffs = parseCutoffs(o.cutoffSpec);
        return o;
    }

    /** "0-30,40,50,64" -> 0, 1, ..., 30, 40, 50, 64 (giữ thứ tự, không cho lặp, cutoff >= 0). */
    static int[] parseCutoffs(String spec) {
        Set<Integer> set = new LinkedHashSet<>();
        for (String part : spec.split(",")) {
            String s = part.trim();
            if (s.isEmpty()) throw new IllegalArgumentException("--cutoffs có phần tử rỗng: \"" + spec + "\"");
            int dash = s.indexOf('-', 1);
            int from = Integer.parseInt((dash > 0 ? s.substring(0, dash) : s).trim());
            int to = dash > 0 ? Integer.parseInt(s.substring(dash + 1).trim()) : from;
            if (from < 0 || to < from) throw new IllegalArgumentException("cutoff không hợp lệ: \"" + s + "\"");
            for (int c = from; c <= to; c++) {
                if (!set.add(c)) throw new IllegalArgumentException("cutoff " + c + " bị lặp trong --cutoffs");
            }
        }
        return set.stream().mapToInt(Integer::intValue).toArray();
    }

    static int atLeast(String s, int min, String flag) {
        int v = Integer.parseInt(s.trim());
        if (v < min) throw new IllegalArgumentException(flag + " phải >= " + min + ": " + v);
        return v;
    }

    static String need(String value, String flag) {
        if (value == null) throw new IllegalArgumentException("Thiếu giá trị sau " + flag);
        return value;
    }

    static String joinInts(int[] a) {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < a.length; i++) {
            if (i > 0) sb.append(',');
            sb.append(a[i]);
        }
        return sb.toString();
    }

    /** Định dạng số luôn dùng dấu chấm thập phân, bất kể locale của máy. */
    static String fmt(String pattern, Object... args) {
        return String.format(Locale.ROOT, pattern, args);
    }
}
