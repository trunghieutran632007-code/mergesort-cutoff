import java.io.BufferedWriter;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.time.LocalDateTime;

/**
 * Bước 5, TN3: đếm số phép so sánh của MergeCount.sort theo cutoff (không đo thời gian).
 *
 * Với mỗi trial và mỗi cutoff: sort một bản sao của mảng gốc bằng MergeCount.sort, ghi số phép so sánh
 * hàm trả về, rồi kiểm tra kết quả bằng Merge.isSorted. Số phép so sánh chỉ phụ thuộc input và cutoff,
 * nên mọi trial phải ra cùng một số; nếu khác nhau hoặc sort sai thì dừng với mã thoát 3.
 * Không cần warm-up hay trộn thứ tự vì không đo thời gian.
 *
 * CSV: experiment, dist, n, cutoff, trial, compares
 *
 * Cách dùng (từ thư mục gốc, sau khi javac -encoding UTF-8 -d out src/*.java):
 *   java -Xms4g -Xmx4g -cp out CompareCount --exp tn3 --data data/random_1000000.bin
 *        [--cutoffs 0-64,80,96,128] [--trials 3] [--out results/<tên>_<timestamp>.csv]
 * Mặc định --out là results/<exp>_<dist>_<n>_<yyyyMMdd_HHmmss>.csv. File đã tồn tại thì không ghi đè.
 * Đọc tham số, kiểm tra manifest dùng chung các hàm của Benchmark.
 */
public final class CompareCount {

    private static final String DEFAULT_CUTOFFS = "0-64,80,96,128";
    private static final String CSV_HEADER = "experiment,dist,n,cutoff,trial,compares";
    private static final String USAGE = "Cách dùng: java -Xms4g -Xmx4g -cp out CompareCount --exp <tên>"
            + " --data <file .bin> [--cutoffs " + DEFAULT_CUTOFFS + "] [--trials 3] [--out <file .csv>]";

    private CompareCount() {}

    public static void main(String[] args) {
        String data = null, exp = null, spec = DEFAULT_CUTOFFS, outArg = null;
        int trials = 3;
        int[] cutoffs;
        try {
            for (int i = 0; i < args.length; i++) {
                String value = (i + 1 < args.length) ? args[i + 1] : null;
                switch (args[i]) {
                    case "--data" -> { data = Benchmark.need(value, "--data"); i++; }
                    case "--exp" -> { exp = Benchmark.need(value, "--exp"); i++; }
                    case "--cutoffs" -> { spec = Benchmark.need(value, "--cutoffs"); i++; }
                    case "--trials" -> { trials = Benchmark.atLeast(Benchmark.need(value, "--trials"), 1, "--trials"); i++; }
                    case "--out" -> { outArg = Benchmark.need(value, "--out"); i++; }
                    default -> throw new IllegalArgumentException("Tham số không rõ: " + args[i]);
                }
            }
            if (data == null) throw new IllegalArgumentException("Thiếu --data <file .bin>");
            if (exp == null || !exp.matches("[A-Za-z0-9_-]+")) {
                throw new IllegalArgumentException("Thiếu --exp hoặc --exp có ký tự lạ (chỉ chữ, số, '_', '-')");
            }
            cutoffs = Benchmark.parseCutoffs(spec);
        } catch (IllegalArgumentException e) {
            System.out.println("Lỗi tham số: " + e.getMessage());
            System.out.println(USAGE);
            System.exit(1);
            return;
        }

        try {
            int code = run(exp, data, cutoffs, trials, outArg);
            if (code != 0) System.exit(code);
        } catch (IOException e) {
            System.out.println("Lỗi: " + e.getMessage());
            System.exit(1);
        }
    }

    /** Trả về 0 nếu xong, 3 nếu sort sai hoặc số phép so sánh không ổn định giữa các trial. */
    private static int run(String exp, String data, int[] cutoffs, int trials, String outArg) throws IOException {
        Path dataPath = Path.of(data);
        int[] original = DataIO.read(data);
        int n = original.length;
        String dist = Benchmark.distFromFileName(dataPath.getFileName().toString(), n);
        Benchmark.ManifestInfo manifest = Benchmark.checkManifest(dataPath, DataIO.sha256(data));

        Path out = Path.of(outArg != null ? outArg
                : "results/" + exp + "_" + dist + "_" + n + "_" + LocalDateTime.now().format(Benchmark.STAMP) + ".csv");
        if (Files.exists(out)) throw new IOException(out + " đã tồn tại, không ghi đè. Chọn --out khác.");
        if (out.toAbsolutePath().getParent() != null) Files.createDirectories(out.toAbsolutePath().getParent());

        String tag = "[" + exp + " " + dist + " n=" + n + "]";
        System.out.println("CompareCount " + tag);
        System.out.println("  dữ liệu : " + data + " (" + manifest.status() + ")");
        System.out.println("  cutoffs : " + Benchmark.joinInts(cutoffs) + "  (" + cutoffs.length + " giá trị), trials = " + trials);
        System.out.println("  ghi vào : " + out);

        long[] first = new long[cutoffs.length];
        int[] work = new int[n];
        long start = System.nanoTime();
        try (BufferedWriter w = Files.newBufferedWriter(out, StandardCharsets.UTF_8,
                StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE)) {
            w.write(CSV_HEADER);
            w.newLine();
            for (int trial = 1; trial <= trials; trial++) {
                for (int i = 0; i < cutoffs.length; i++) {
                    int c = cutoffs[i];
                    System.arraycopy(original, 0, work, 0, n);
                    long compares = MergeCount.sort(work, c);
                    if (!Merge.isSorted(work)) {
                        System.out.println("SORT SAI: MergeCount.sort cho mảng chưa tăng dần (cutoff = " + c
                                + ", trial = " + trial + ")");
                        return 3;
                    }
                    if (trial == 1) {
                        first[i] = compares;
                    } else if (compares != first[i]) {
                        System.out.println("LỖI: cutoff = " + c + " ra " + compares + " phép so sánh ở trial " + trial
                                + " nhưng " + first[i] + " ở trial 1 (cùng input phải ra cùng số)");
                        return 3;
                    }
                    w.write(exp + "," + dist + "," + n + "," + c + "," + trial + "," + compares);
                    w.newLine();
                }
                w.flush();
                System.out.println(tag + " trial " + trial + "/" + trials + " xong ("
                        + Benchmark.fmt("%.1f", (System.nanoTime() - start) / 1e9) + " s)");
            }
        }
        System.out.println("Xong " + tag + ": số phép so sánh giống nhau ở cả " + trials + " trial. CSV: " + out);
        return 0;
    }
}
