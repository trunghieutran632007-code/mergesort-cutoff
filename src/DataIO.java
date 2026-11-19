import java.io.BufferedOutputStream;
import java.io.BufferedWriter;
import java.io.DataOutputStream;
import java.io.IOException;
import java.io.OutputStream;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.DigestOutputStream;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;

/**
 * Đọc/ghi bộ dữ liệu thí nghiệm.
 *
 * Định dạng file .bin (giống DataOutputStream, big-endian):
 *   4 byte: N (int)
 *   4N byte: N số int a[0], a[1], ..., a[N-1]
 * Kích thước file luôn đúng 4 + 4N byte.
 *
 * Định dạng file .txt (chỉ để xem bằng mắt): dòng đầu là N, sau đó mỗi dòng một số.
 */
public final class DataIO {

    private DataIO() {}

    /** Đọc một file .bin, trả về mảng int. Báo lỗi nếu kích thước file không khớp với N ghi trong file. */
    public static int[] read(String path) throws IOException {
        Path p = Path.of(path);
        byte[] bytes = Files.readAllBytes(p);
        if (bytes.length < 4) {
            throw new IOException(path + ": file quá ngắn (" + bytes.length + " byte), không đọc được N");
        }
        ByteBuffer buf = ByteBuffer.wrap(bytes); // mặc định big-endian, khớp DataOutputStream
        int n = buf.getInt();
        long expectedBytes = 4L + 4L * n;
        if (n < 0 || bytes.length != expectedBytes) {
            throw new IOException(path + ": N = " + n + " nên file phải có " + expectedBytes
                    + " byte, nhưng file có " + bytes.length + " byte");
        }
        int[] a = new int[n];
        buf.asIntBuffer().get(a);
        return a;
    }

    /** Ghi mảng ra file .bin và trả về mã SHA-256 (dạng hex) của toàn bộ file vừa ghi. */
    public static String write(String path, int[] a) throws IOException {
        MessageDigest sha = sha256();
        try (OutputStream file = Files.newOutputStream(Path.of(path));
             DigestOutputStream digest = new DigestOutputStream(new BufferedOutputStream(file, 1 << 16), sha);
             DataOutputStream out = new DataOutputStream(digest)) {
            out.writeInt(a.length);
            for (int x : a) out.writeInt(x);
        }
        return hex(sha.digest());
    }

    /** Ghi bản .txt để xem bằng mắt: dòng đầu là N, sau đó mỗi dòng một số. */
    public static void writeText(String path, int[] a) throws IOException {
        try (BufferedWriter w = Files.newBufferedWriter(Path.of(path), StandardCharsets.UTF_8)) {
            w.write(Integer.toString(a.length));
            w.newLine();
            for (int x : a) {
                w.write(Integer.toString(x));
                w.newLine();
            }
        }
    }

    /** Mã SHA-256 (hex) của một file có sẵn, dùng để đối chiếu với data/manifest.csv. */
    public static String sha256(String path) throws IOException {
        return hex(sha256().digest(Files.readAllBytes(Path.of(path))));
    }

    private static MessageDigest sha256() {
        try {
            return MessageDigest.getInstance("SHA-256");
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException("JVM không hỗ trợ SHA-256", e);
        }
    }

    private static String hex(byte[] bytes) {
        StringBuilder sb = new StringBuilder(bytes.length * 2);
        for (byte b : bytes) sb.append(String.format("%02x", b));
        return sb.toString();
    }
}
