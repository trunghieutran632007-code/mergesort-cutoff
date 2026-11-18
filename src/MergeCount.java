public class MergeCount {
    // Tổng số phép so sánh phần tử trong lần sort gần nhất
    private static long compares = 0;

    private MergeCount() {
    }

    /**
     * Trộn hai nửa đã sắp xếp a[lo..mid] và a[mid+1..hi].
     * Phép so sánh phần tử được đếm qua hàm less().
     */
    private static void merge(int[] a, int[] aux, int lo, int mid, int hi) {
        for (int k = lo; k <= hi; k++) {
            aux[k] = a[k];
        }

        int i = lo, j = mid + 1;
        for (int k = lo; k <= hi; k++) {
            if (i > mid) a[k] = aux[j++];
            else if (j > hi) a[k] = aux[i++];
            else if (less(aux[j], aux[i])) a[k] = aux[j++];
            else a[k] = aux[i++];
        }
    }

    public static long sort(int[] a, int cutoff) {
        compares = 0;
        int n = a.length;
        int[] aux = new int[n];
        sort(a, aux, 0, n - 1, cutoff);
        return compares;
    }

    private static void sort(int[] a, int[] aux, int lo, int hi, int cutoff) {
        if (hi <= lo) return;
        if (hi <= lo + cutoff - 1) {
            insertionSort(a, lo, hi);
            return;
        }
        int mid = lo + (hi - lo) / 2;
        sort(a, aux, lo, mid, cutoff);
        sort(a, aux, mid + 1, hi, cutoff);
        merge(a, aux, lo, mid, hi);
    }

    private static void insertionSort(int[] a, int lo, int hi) {
        for (int i = lo + 1; i <= hi; i++) {
            int key = a[i];
            int j = i - 1;
            while (j >= lo && less(key, a[j])) {
                a[j + 1] = a[j];
                j--;
            }
            a[j + 1] = key;
        }
    }

    /**
     * So sánh hai phần tử và tăng biến đếm.
     * Mọi phép so sánh khóa đều đi qua hàm này nên được đếm đầy đủ.
     */
    private static boolean less(int v, int w) {
        compares++;
        return v < w;
    }
}