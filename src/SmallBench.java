import java.io.BufferedWriter;
import java.io.IOException;
import java.lang.management.ManagementFactory;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.time.LocalDateTime;
import java.util.LinkedHashMap;
import java.util.Locale;
import java.util.Map;
import java.util.Random;

/**
 * Bước 5, TN4: insertion sort nhanh hơn mergesort đến độ dài nào?
 *
 * So sánh hai cách sắp xếp một mảng ngắn độ dài n (mặc định n = 2..64):
 *   insertion  Merge.insertionSort(a, 0, n - 1)
 *   merge      Merge.sort(a, 0)   (mergesort thuần, không cutoff; tính cả việc cấp phát aux mỗi lần gọi)
 *
 * Dữ liệu: với mỗi n, một "kho" P mảng ngẫu nhiên độ dài n (Random(seed + n).nextInt(), như phân bố random
 * của DataGen), P = ceil(16384 / n) nên mỗi kho khoảng 64 KB, nằm gọn trong cache. Đo trên P mảng khác nhau
 * để lấy thời gian trung bình theo input, không phụ thuộc một mảng cụ thể.
 *
 * Cách đo theo đúng 7 nguyên tắc của Benchmark:
 *   1. Warm-up: ít nhất --warmup vòng (mặc định 50) qua mọi cấu hình (n, cách sort) và ít nhất 1 giây.
 *   2. Cùng input: cả hai cách sort cùng một kho mảng, chép lại (ngoài vùng tính giờ) trước mỗi lượt.
 *   3. Trial, thứ tự ngẫu nhiên: --trials trial (mặc định 30), mỗi trial trộn thứ tự các cấu hình.
 *   4. Đo theo lô: một lượt sort cả P mảng; một phép đo gồm R lượt, cộng thời gian các lượt (không tính
 *      lúc chép lại mảng) rồi chia cho R * P. R chọn sau warm-up để mỗi phép đo kéo dài ít nhất --min-ms
 *      (mặc định 20 ms); cùng một n thì hai cách sort dùng chung R.
 *   5. Sau mỗi lượt kiểm tra mọi mảng bằng Merge.isSorted (ngoài vùng tính giờ), sai thì dừng, mã thoát 3.
 *   6. Cờ JVM do script truyền vào, ghi vào .meta.txt.  7. Ghi số liệu thô, không tính trung bình.
 *
 * CSV: experiment, dist, n, method, trial, k, ns_per_sort, pos, gc
 *   method  insertion hoặc merge;  k = R * P = số lần sort trong phép đo;  gc = số lần GC trong phép đo.
 * Kèm file .meta.txt: seed, P và R theo từng n, cờ JVM, thời gian chạy.
 *
 * Cách dùng (từ thư mục gốc, sau khi javac -encoding UTF-8 -d out src/*.java):
 *   java -Xms4g -Xmx4g -cp out SmallBench --exp tn4 [--sizes 2-64] [--trials 30] [--warmup 50]
 *        [--min-ms 20] [--seed 20261109] [--out results/<tên>_<timestamp>.csv]
 * Mặc định --out là results/<exp>_random_small_<yyyyMMdd_HHmmss>.csv. File đã tồn tại thì không ghi đè.
 */
public final class SmallBench {

    private static final String DEFAULT_SIZES = "2-64";
    private static final int POOL_INTS = 16384; // mỗi kho khoảng 16384 số int = 64 KB
    private static final String[] METHODS = {"insertion", "merge"};
    private static final String CSV_HEADER = "experiment,dist,n,method,trial,k,ns_per_sort,pos,gc";
    private static final String USAGE = "Cách dùng: java -Xms4g -Xmx4g -cp out SmallBench --exp <tên>"
            + " [--sizes " + DEFAULT_SIZES + "] [--trials 30] [--warmup 50] [--min-ms 20]"
            + " [--seed " + Benchmark.DEFAULT_SEED + "] [--out <file .csv>]";

    private SmallBench() {}

    /** Một cấu hình đo: độ dài n và cách sort, cùng kho mảng gốc và mảng làm việc. */
    private static final class Config {
        final int n;
        final int method; // 0 = insertion, 1 = merge
        final int[][] src;
        final int[][] work;
        long fastestPass = Long.MAX_VALUE;
        int passes; // R

        Config(int n, int method, int[][] src, int[][] work) {
            this.n = n;
            this.method = method;
            this.src = src;
            this.work = work;
        }
    }

    public static void main(String[] args) {
        String exp = null, sizeSpec = DEFAULT_SIZES, outArg = null;
        int trials = 30, warmup = 50;
        double minMs = 20;
        long seed = Benchmark.DEFAULT_SEED;
        int[] sizes;
        try {
            for (int i = 0; i < args.length; i++) {
                String value = (i + 1 < args.length) ? args[i + 1] : null;
                switch (args[i]) {
                    case "--exp" -> { exp = Benchmark.need(value, "--exp"); i++; }
                    case "--sizes" -> { sizeSpec = Benchmark.need(value, "--sizes"); i++; }
                    case "--trials" -> { trials = Benchmark.atLeast(Benchmark.need(value, "--trials"), 1, "--trials"); i++; }
                    case "--warmup" -> { warmup = Benchmark.atLeast(Benchmark.need(value, "--warmup"), 0, "--warmup"); i++; }
                    case "--min-ms" -> {
                        minMs = Double.parseDouble(Benchmark.need(value, "--min-ms"));
                        if (!(minMs > 0)) throw new IllegalArgumentException("--min-ms phải > 0");
                        i++;
                    }
                    case "--seed" -> { seed = Long.parseLong(Benchmark.need(value, "--seed")); i++; }
                    case "--out" -> { outArg = Benchmark.need(value, "--out"); i++; }
                    default -> throw new IllegalArgumentException("Tham số không rõ: " + args[i]);
                }
            }
            if (exp == null || !exp.matches("[A-Za-z0-9_-]+")) {
                throw new IllegalArgumentException("Thiếu --exp hoặc --exp có ký tự lạ (chỉ chữ, số, '_', '-')");
            }
            sizes = Benchmark.parseCutoffs(sizeSpec); // cùng cú pháp "2-64" hoặc "2,4,8"
            for (int n : sizes) {
                if (n < 1) throw new IllegalArgumentException("--sizes: độ dài phải >= 1");
            }
        } catch (IllegalArgumentException e) {
            System.out.println("Lỗi tham số: " + e.getMessage());
            System.out.println(USAGE);
            System.exit(1);
            return;
        }

        try {
            run(exp, sizes, trials, warmup, minMs, seed, outArg);
        } catch (IllegalStateException e) {
            System.out.println("SORT SAI, dừng thí nghiệm: " + e.getMessage());
            System.exit(3);
        } catch (IOException e) {
            System.out.println("Lỗi: " + e.getMessage());
            System.exit(1);
        }
    }

    private static void run(String exp, int[] sizes, int trials, int warmup, double minMs, long seed,
                            String outArg) throws IOException {
        LocalDateTime start = LocalDateTime.now();
        Path out = Path.of(outArg != null ? outArg
                : "results/" + exp + "_random_small_" + start.format(Benchmark.STAMP) + ".csv");
        Path metaPath = Benchmark.metaPathFor(out);
        if (Files.exists(out) || Files.exists(metaPath)) {
            throw new IOException(out + " (hoặc file .meta.txt) đã tồn tại, không ghi đè. Chọn --out khác.");
        }
        if (out.toAbsolutePath().getParent() != null) Files.createDirectories(out.toAbsolutePath().getParent());

        // Kho mảng ngẫu nhiên cho từng n; hai cách sort dùng chung kho và mảng làm việc
        Config[] configs = new Config[sizes.length * METHODS.length];
        StringBuilder pools = new StringBuilder();
        for (int s = 0; s < sizes.length; s++) {
            int n = sizes[s];
            int p = (POOL_INTS + n - 1) / n;
            Random r = new Random(seed + n);
            int[][] src = new int[p][n];
            int[][] work = new int[p][n];
            for (int[] a : src) for (int i = 0; i < n; i++) a[i] = r.nextInt();
            for (int m = 0; m < METHODS.length; m++) configs[s * METHODS.length + m] = new Config(n, m, src, work);
            pools.append(s > 0 ? "," : "").append(n).append(':').append(p);
        }

        Map<String, String> meta = new LinkedHashMap<>();
        meta.put("experiment", exp);
        meta.put("status", "đang chạy");
        meta.put("start", start.toString());
        meta.put("sizes", Benchmark.joinInts(sizes));
        meta.put("methods", "insertion = Merge.insertionSort(a, 0, n-1); merge = Merge.sort(a, 0)");
        meta.put("array_seed", "Random(" + seed + " + n).nextInt()");
        meta.put("pool_per_n", pools.toString());
        meta.put("trials", Integer.toString(trials));
        meta.put("warmup_min_rounds", Integer.toString(warmup));
        meta.put("min_batch_ms", Benchmark.fmt("%.1f", minMs));
        meta.put("shuffle_seed", Long.toString(seed));
        meta.put("jvm_args", String.join(" ", ManagementFactory.getRuntimeMXBean().getInputArguments()));
        meta.put("java_version", System.getProperty("java.version"));
        meta.put("os", System.getProperty("os.name") + " " + System.getProperty("os.version")
                + " " + System.getProperty("os.arch"));
        meta.put("csv", out.toString());

        String tag = "[" + exp + " n=" + sizes[0] + ".." + sizes[sizes.length - 1] + "]";
        System.out.println("SmallBench " + tag);
        System.out.println("  độ dài  : " + Benchmark.joinInts(sizes) + " | cách sort: insertion, merge"
                + " | " + configs.length + " cấu hình");
        System.out.println("  trials = " + trials + ", seed = " + seed + " | JVM: " + meta.get("jvm_args"));
        Benchmark.writeMeta(metaPath, meta);

        try {
            // ---- 1. Warm-up, đồng thời lấy thời gian lượt nhanh nhất của từng cấu hình ----
            long jitStart = Benchmark.jitMillis();
            long warmStart = System.nanoTime();
            int rounds = 0;
            while (rounds < warmup || System.nanoTime() - warmStart < Benchmark.WARMUP_MIN_NS) {
                for (Config c : configs) {
                    long t = timedPass(c, "warm-up", 0);
                    if (t < c.fastestPass) c.fastestPass = t;
                }
                rounds++;
            }
            double warmSeconds = (System.nanoTime() - warmStart) / 1e9;

            // ---- 4. Chọn R cho từng n: lấy cách sort nhanh hơn làm chuẩn để mỗi phép đo >= minMs ----
            StringBuilder rs = new StringBuilder();
            for (int i = 0; i < configs.length; i += METHODS.length) {
                long fastest = Math.max(1, Math.min(configs[i].fastestPass, configs[i + 1].fastestPass));
                int passes = (int) Math.max(1, Math.ceil(minMs * 1e6 / fastest));
                configs[i].passes = passes;
                configs[i + 1].passes = passes;
                rs.append(i > 0 ? "," : "").append(configs[i].n).append(':').append(passes);
            }
            meta.put("warmup_rounds", Integer.toString(rounds));
            meta.put("warmup_seconds", Benchmark.fmt("%.3f", warmSeconds));
            meta.put("jit_ms_warmup", Long.toString(Benchmark.jitMillis() - jitStart));
            meta.put("passes_per_n", rs.toString());
            System.out.printf(Locale.ROOT, "  warm-up : %d vòng, %.2f s%n", rounds, warmSeconds);
            System.out.println("  ghi vào : " + out);

            // ---- 2, 3, 5, 7. Đo ----
            Random rng = new Random(seed);
            int[] order = new int[configs.length];
            long jitMeasureStart = Benchmark.jitMillis();
            long measureStart = System.nanoTime();
            long gcTotal = 0;
            try (BufferedWriter w = Files.newBufferedWriter(out, StandardCharsets.UTF_8,
                    StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE)) {
                w.write(CSV_HEADER);
                w.newLine();
                for (int trial = 1; trial <= trials; trial++) {
                    for (int i = 0; i < order.length; i++) order[i] = i;
                    Benchmark.shuffle(order, rng);
                    for (int pos = 0; pos < order.length; pos++) {
                        Config c = configs[order[pos]];
                        long gc0 = Benchmark.gcCount();
                        long total = 0;
                        for (int r = 0; r < c.passes; r++) total += timedPass(c, "đo", trial);
                        long gc = Benchmark.gcCount() - gc0;
                        gcTotal += gc;
                        long k = (long) c.passes * c.src.length;
                        w.write(exp + ",random," + c.n + "," + METHODS[c.method] + "," + trial + "," + k + ","
                                + Benchmark.fmt("%.2f", (double) total / k) + "," + (pos + 1) + "," + gc);
                        w.newLine();
                    }
                    w.flush();
                    double done = (System.nanoTime() - measureStart) / 1e9;
                    System.out.printf(Locale.ROOT, "%s trial %d/%d xong  (đã đo %.1f s, còn khoảng %.1f s)%n",
                            tag, trial, trials, done, done / trial * (trials - trial));
                }
            }
            meta.put("status", "ok");
            meta.put("end", LocalDateTime.now().toString());
            meta.put("measure_seconds", Benchmark.fmt("%.3f", (System.nanoTime() - measureStart) / 1e9));
            meta.put("jit_ms_measure", Long.toString(Benchmark.jitMillis() - jitMeasureStart));
            meta.put("gc_in_measure", Long.toString(gcTotal));
            Benchmark.writeMeta(metaPath, meta);
            System.out.println("Xong " + tag + ". GC trong lúc đo: " + gcTotal + " lần. CSV: " + out);
        } catch (IllegalStateException | IOException e) {
            meta.put("status", "LỖI: " + e.getMessage());
            meta.put("end", LocalDateTime.now().toString());
            Benchmark.writeMeta(metaPath, meta);
            throw e;
        }
    }

    /** Một lượt: chép lại P mảng (không tính giờ), sort cả P mảng (tính giờ), kiểm tra. Trả về ns. */
    private static long timedPass(Config c, String phase, int trial) {
        int[][] src = c.src, work = c.work;
        int n = c.n;
        for (int j = 0; j < src.length; j++) System.arraycopy(src[j], 0, work[j], 0, n);
        long elapsed = c.method == 0 ? passInsertion(work, n) : passMerge(work);
        for (int[] a : work) {
            if (!Merge.isSorted(a)) {
                throw new IllegalStateException("Merge.isSorted trả về false (" + phase + ", n = " + n
                        + ", " + METHODS[c.method] + (trial > 0 ? ", trial = " + trial : "") + ")");
            }
        }
        return elapsed;
    }

    private static long passInsertion(int[][] work, int n) {
        long t0 = System.nanoTime();
        for (int[] a : work) Merge.insertionSort(a, 0, n - 1);
        return System.nanoTime() - t0;
    }

    private static long passMerge(int[][] work) {
        long t0 = System.nanoTime();
        for (int[] a : work) Merge.sort(a, 0);
        return System.nanoTime() - t0;
    }
}
