import java.util.Arrays;
import java.util.HashMap;
import java.util.Map;
import java.util.Random;

/**
 * Bước 2: kiểm tra tính đúng của Merge.sort(int[] a, int cutoff) và MergeCount.sort.
 *
 * Nội dung kiểm tra:
 *   [1] Merge.isSorted trên vài mảng nhỏ viết tay (harness ở Bước 4 dựa vào hàm này).
 *   [2] Merge.insertionSort(a, lo, hi) trên đoạn con: sắp đúng a[lo..hi] và không đụng
 *       phần còn lại của mảng (TN4 gọi trực tiếp hàm này).
 *   [3] Merge.sort với mọi cutoff trong {0, 1, ..., 40, 64, 100}, mọi n từ 0 đến 300
 *       và n = 1000, 4096, 100000, trên 9 loại dữ liệu; đối chiếu với bản sao sắp bằng Arrays.sort.
 *       MergeCount.sort trên cùng các ca: kiểm tra kết quả sắp xếp và số phép so sánh trả về:
 *         - gọi lần hai trên cùng input phải ra cùng số (biến đếm được đặt lại về 0),
 *         - cutoff 0 và cutoff 1 phải ra cùng số (hai cách này tương đương),
 *         - phải nằm trong [cận dưới, cận trên] tính bằng công thức truy hồi,
 *         - với dữ liệu sorted, equal, reversed: phải khớp chính xác công thức truy hồi.
 *           Đây là phép kiểm tra duy nhất bắt được lỗi lệch 1 ở điều kiện cutoff
 *           (độ dài <= cutoff so với < cutoff), vì lỗi đó không làm sai kết quả sắp xếp.
 *
 * Gặp ca sai đầu tiên: in (n, cutoff, loại dữ liệu, seed) rồi dừng với mã thoát 1.
 * Arrays.sort chỉ dùng để tạo kết quả đối chiếu.
 *
 * Biên dịch và chạy từ thư mục gốc của project:
 *   javac -d out src/*.java
 *   java -cp out TestCorrectness            (seed mặc định)
 *   java -cp out TestCorrectness 12345      (seed khác, để thử thêm bộ input ngẫu nhiên)
 */
public class TestCorrectness {

    private static final long DEFAULT_SEED = 20261109L;
    private static final int MAX_SMALL_N = 300;
    private static final int[] LARGE_N = {1000, 4096, 100000};
    private static final int[] CUTOFFS = makeCutoffs();
    private static final String[] TYPES = {
            "random",      // số nguyên ngẫu nhiên trên toàn miền int
            "sorted",      // 0, 1, ..., n-1
            "reversed",    // n-1, ..., 0
            "equal",       // toàn phần tử bằng nhau
            "twovalues",   // chỉ có 2 giá trị 0 và 1
            "negative",    // số âm lẫn dương trong [-1000, 1000]
            "fewdistinct", // giá trị trong 0..9
            "extremes",    // Integer.MIN_VALUE, MAX_VALUE và lân cận
            "nearly"       // đã sắp xếp, hoán đổi ngẫu nhiên 1% phần tử (ít nhất 1 lần)
    };
    private static final int[] EXTREMES = {
            Integer.MIN_VALUE, Integer.MIN_VALUE + 1, -1, 0, 1,
            Integer.MAX_VALUE - 1, Integer.MAX_VALUE
    };

    // Các mô hình đếm số phép so sánh dùng trong compareCost
    private static final int SORTED = 0, REVERSED = 1, LOWER = 2, UPPER = 3;

    /** Một ca kiểm tra: loại dữ liệu, n, cutoff, seed sinh input và chính input đó. */
    private record Case(String type, int n, int cutoff, long seed, int[] original) {}

    private static long seed;
    private static long checks = 0;

    public static void main(String[] args) {
        seed = args.length > 0 ? Long.parseLong(args[0]) : DEFAULT_SEED;
        System.out.println("TestCorrectness | seed = " + seed);
        System.out.println("cutoff: 0..40, 64, 100 | n: 0.." + MAX_SMALL_N + " và "
                + Arrays.toString(LARGE_N) + " | " + TYPES.length + " loại dữ liệu");
        long start = System.nanoTime();

        testIsSorted();
        System.out.println("[1/3] Merge.isSorted: OK");

        testInsertionSortRange();
        System.out.println("[2/3] Merge.insertionSort trên đoạn con: OK");

        System.out.println("[3/3] Merge.sort và MergeCount.sort:");
        for (int n = 0; n <= MAX_SMALL_N; n++) {
            testSize(n);
        }
        System.out.println("      n = 0.." + MAX_SMALL_N + ": OK");
        for (int n : LARGE_N) {
            testSize(n);
            System.out.println("      n = " + n + ": OK");
        }

        double seconds = (System.nanoTime() - start) / 1e9;
        System.out.printf("TẤT CẢ ĐỀU ĐÚNG: %d phép kiểm tra, seed = %d, %.1f s%n", checks, seed, seconds);
    }

    // ------------------------------------------------------------------
    // [3] Merge.sort và MergeCount.sort
    // ------------------------------------------------------------------

    /** Chạy mọi loại dữ liệu và mọi cutoff cho một kích thước n. */
    private static void testSize(int n) {
        // Số phép so sánh theo công thức chỉ phụ thuộc (n, cutoff), tính một lần cho mọi loại dữ liệu
        long[][] cost = new long[4][CUTOFFS.length];
        for (int c = 0; c < CUTOFFS.length; c++) {
            for (int model = SORTED; model <= UPPER; model++) {
                cost[model][c] = compareCost(n, CUTOFFS[c], model, new HashMap<>());
            }
        }

        for (int t = 0; t < TYPES.length; t++) {
            long caseSeed = caseSeed(t, n);
            int[] original = generate(TYPES[t], n, caseSeed);
            int[] expected = original.clone();
            Arrays.sort(expected);

            long countCutoff0 = -1;
            for (int c = 0; c < CUTOFFS.length; c++) {
                Case k = new Case(TYPES[t], n, CUTOFFS[c], caseSeed, original);
                checkMerge(k, expected);
                long count = checkMergeCount(k, expected, cost, c);

                if (k.cutoff() == 0) {
                    countCutoff0 = count;
                } else if (k.cutoff() == 1 && count != countCutoff0) {
                    fail("MergeCount: cutoff 0 và cutoff 1 phải tương đương nhưng số phép so sánh khác nhau ("
                            + countCutoff0 + " với cutoff 0, " + count + " với cutoff 1)", k, null);
                }
            }
        }
    }

    private static void checkMerge(Case k, int[] expected) {
        int[] a = k.original().clone();
        try {
            Merge.sort(a, k.cutoff());
        } catch (Throwable e) {
            fail("Merge.sort ném ngoại lệ " + describe(e), k, null);
        }
        int bad = firstDifference(a, expected);
        if (bad >= 0) {
            fail("Merge.sort cho kết quả sai", k, mismatchDetail(a, expected, bad));
        }
        checks++;
    }

    /** Kiểm tra MergeCount.sort trên một ca, trả về số phép so sánh đếm được. */
    private static long checkMergeCount(Case k, int[] expected, long[][] cost, int c) {
        int[] b = k.original().clone();
        long count = 0;
        try {
            count = MergeCount.sort(b, k.cutoff());
        } catch (Throwable e) {
            fail("MergeCount.sort ném ngoại lệ " + describe(e), k, null);
        }
        int bad = firstDifference(b, expected);
        if (bad >= 0) {
            fail("MergeCount.sort cho kết quả sai", k, mismatchDetail(b, expected, bad));
        }

        long again = MergeCount.sort(k.original().clone(), k.cutoff());
        if (again != count) {
            fail("MergeCount.sort gọi hai lần trên cùng input trả về số phép so sánh khác nhau ("
                    + count + " rồi " + again + "); biến đếm có được đặt lại về 0 mỗi lần sort không?", k, null);
        }

        long lower = cost[LOWER][c], upper = cost[UPPER][c];
        if (count < lower || count > upper) {
            fail("MergeCount: số phép so sánh " + count + " nằm ngoài khoảng cho phép ["
                    + lower + ", " + upper + "]", k, null);
        }

        long exact = switch (k.type()) {
            case "sorted", "equal" -> cost[SORTED][c];
            case "reversed" -> cost[REVERSED][c];
            default -> -1;
        };
        if (exact >= 0 && count != exact) {
            fail("MergeCount: với dữ liệu " + k.type() + " số phép so sánh phải đúng bằng " + exact
                    + " nhưng nhận được " + count, k,
                    "Gợi ý: so sánh với ca cutoff = n (chỉ insertion sort) để kiểm tra điều kiện "
                            + "\"độ dài <= cutoff\" và vị trí tăng biến đếm.");
        }
        checks++;
        return count;
    }

    /**
     * Số phép so sánh của mergesort top-down có cutoff trên một đoạn độ dài m, tính bằng công thức truy hồi.
     * Giả định chia đôi như bài giảng: mid = lo + (hi - lo) / 2, nên nửa trái có ceil(m/2) phần tử.
     *
     *   m <= 1        : 0
     *   m <= cutoff   : insertion sort; SORTED và LOWER: m - 1, REVERSED và UPPER: m(m-1)/2
     *   còn lại       : C(trái) + C(phải) + số phép so sánh khi merge, trong đó merge tốn
     *                   SORTED   : |trái|  (lấy hết nửa trái, nửa phải chép không cần so sánh)
     *                   REVERSED : |phải|  (lấy hết nửa phải trước)
     *                   LOWER    : min(|trái|, |phải|) = |phải|
     *                   UPPER    : m - 1
     *
     * SORTED cũng đúng cho mảng toàn phần tử bằng nhau, vì khi bằng nhau merge lấy bên trái
     * và insertion sort dừng ngay sau một phép so sánh.
     */
    private static long compareCost(int m, int cutoff, int model, Map<Integer, Long> memo) {
        if (m <= 1) return 0;
        Long known = memo.get(m);
        if (known != null) return known;

        long result;
        if (m <= cutoff) {
            result = (model == SORTED || model == LOWER) ? m - 1 : (long) m * (m - 1) / 2;
        } else {
            int left = (m + 1) / 2;
            int right = m / 2;
            long mergeCost = switch (model) {
                case SORTED -> left;
                case REVERSED, LOWER -> right;
                default -> m - 1;
            };
            result = compareCost(left, cutoff, model, memo)
                    + compareCost(right, cutoff, model, memo)
                    + mergeCost;
        }
        memo.put(m, result);
        return result;
    }

    // ------------------------------------------------------------------
    // [1] isSorted và [2] insertionSort trên đoạn con
    // ------------------------------------------------------------------

    private static void testIsSorted() {
        int[][] sorted = {
                {}, {5}, {1, 2, 2, 3}, {-3, -1, 0, 0, 7}, {4, 4, 4},
                {Integer.MIN_VALUE, 0, Integer.MAX_VALUE}
        };
        int[][] unsorted = {
                {2, 1}, {3, 1, 2}, {1, 2, 3, 0}, {1, 1, 0, 1},
                {Integer.MAX_VALUE, Integer.MIN_VALUE}
        };
        for (int[] a : sorted) {
            if (!Merge.isSorted(a)) failSimple("Merge.isSorted(" + Arrays.toString(a) + ") phải là true");
            checks++;
        }
        for (int[] a : unsorted) {
            if (Merge.isSorted(a)) failSimple("Merge.isSorted(" + Arrays.toString(a) + ") phải là false");
            checks++;
        }
    }

    private static void testInsertionSortRange() {
        Random r = new Random(seed ^ 0x5DEECE66DL);
        for (int trial = 0; trial < 5000; trial++) {
            int n = 1 + r.nextInt(80);
            int[] a = new int[n];
            for (int i = 0; i < n; i++) a[i] = r.nextInt(51) - 25; // nhiều phần tử trùng, có số âm
            int lo = r.nextInt(n);
            int hi = lo - 1 + r.nextInt(n - lo + 1);                // từ lo - 1 (đoạn rỗng) đến n - 1

            int[] original = a.clone();
            int[] expected = a.clone();
            Arrays.sort(expected, lo, hi + 1);

            String call = "Merge.insertionSort(a, " + lo + ", " + hi + ") với n = " + n;
            try {
                Merge.insertionSort(a, lo, hi);
            } catch (Throwable e) {
                failSimple(call + " ném ngoại lệ " + describe(e) + "\n  input: " + Arrays.toString(original));
            }
            int bad = firstDifference(a, expected);
            if (bad >= 0) {
                String why = (bad < lo || bad > hi)
                        ? "đã thay đổi phần tử nằm ngoài đoạn [lo, hi]"
                        : "đoạn [lo, hi] chưa được sắp đúng";
                failSimple(call + ": " + why
                        + "\n  input    : " + Arrays.toString(original)
                        + "\n  mong đợi : " + Arrays.toString(expected)
                        + "\n  nhận được: " + Arrays.toString(a));
            }
            checks++;
        }
    }

    // ------------------------------------------------------------------
    // Sinh dữ liệu
    // ------------------------------------------------------------------

    private static int[] makeCutoffs() {
        int[] c = new int[43];
        for (int i = 0; i <= 40; i++) c[i] = i;
        c[41] = 64;
        c[42] = 100;
        return c;
    }

    /** Seed riêng cho mỗi (loại dữ liệu, n), suy ra từ seed gốc để chạy lại ra đúng input đó. */
    private static long caseSeed(int typeIndex, int n) {
        return (seed * 31 + typeIndex) * 1_000_003L + n;
    }

    private static int[] generate(String type, int n, long caseSeed) {
        Random r = new Random(caseSeed);
        int[] a = new int[n];
        switch (type) {
            case "random" -> { for (int i = 0; i < n; i++) a[i] = r.nextInt(); }
            case "sorted" -> { for (int i = 0; i < n; i++) a[i] = i; }
            case "reversed" -> { for (int i = 0; i < n; i++) a[i] = n - 1 - i; }
            case "equal" -> Arrays.fill(a, 7);
            case "twovalues" -> { for (int i = 0; i < n; i++) a[i] = r.nextBoolean() ? 1 : 0; }
            case "negative" -> { for (int i = 0; i < n; i++) a[i] = r.nextInt(2001) - 1000; }
            case "fewdistinct" -> { for (int i = 0; i < n; i++) a[i] = r.nextInt(10); }
            case "extremes" -> { for (int i = 0; i < n; i++) a[i] = EXTREMES[r.nextInt(EXTREMES.length)]; }
            case "nearly" -> {
                for (int i = 0; i < n; i++) a[i] = i;
                if (n >= 2) {
                    int swaps = Math.max(1, n / 100);
                    for (int s = 0; s < swaps; s++) {
                        int i = r.nextInt(n), j = r.nextInt(n);
                        int tmp = a[i]; a[i] = a[j]; a[j] = tmp;
                    }
                }
            }
            default -> throw new IllegalArgumentException("Loại dữ liệu không rõ: " + type);
        }
        return a;
    }

    // ------------------------------------------------------------------
    // Báo lỗi
    // ------------------------------------------------------------------

    /** Vị trí đầu tiên hai mảng khác nhau, hoặc -1 nếu giống hệt. */
    private static int firstDifference(int[] a, int[] b) {
        if (a.length != b.length) return 0;
        for (int i = 0; i < a.length; i++) {
            if (a[i] != b[i]) return i;
        }
        return -1;
    }

    private static String mismatchDetail(int[] got, int[] expected, int bad) {
        String s = "vị trí sai đầu tiên: i = " + bad + ", mong đợi " + expected[bad] + ", nhận được " + got[bad];
        if (got.length <= 40) {
            s += "\n  mong đợi : " + Arrays.toString(expected)
                    + "\n  nhận được: " + Arrays.toString(got);
        }
        return s;
    }

    private static String describe(Throwable e) {
        StackTraceElement[] st = e.getStackTrace();
        return e + (st.length > 0 ? " tại " + st[0] : "");
    }

    private static void fail(String what, Case k, String detail) {
        System.out.println();
        System.out.println("SAI: " + what);
        System.out.println("  n = " + k.n() + ", cutoff = " + k.cutoff() + ", loại dữ liệu = " + k.type());
        System.out.println("  seed của ca = " + k.seed() + " (seed gốc = " + seed + ")");
        if (k.n() <= 40) System.out.println("  input    : " + Arrays.toString(k.original()));
        if (detail != null) System.out.println("  " + detail);
        System.out.println("Đã qua " + checks + " phép kiểm tra trước ca này.");
        System.exit(1);
    }

    private static void failSimple(String what) {
        System.out.println();
        System.out.println("SAI: " + what);
        System.out.println("  seed gốc = " + seed);
        System.out.println("Đã qua " + checks + " phép kiểm tra trước ca này.");
        System.exit(1);
    }
}
