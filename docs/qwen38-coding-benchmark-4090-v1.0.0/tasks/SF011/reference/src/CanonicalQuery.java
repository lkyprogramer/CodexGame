import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;

public final class CanonicalQuery {
    private record Pair(String key, String value) { }
    public static String canonicalize(Map<String, List<String>> params) {
        if (params == null) throw new IllegalArgumentException("params is null");
        List<Pair> pairs = new ArrayList<>();
        for (Map.Entry<String,List<String>> entry : params.entrySet()) {
            if (entry.getKey() == null || entry.getValue() == null) throw new IllegalArgumentException("null key/list");
            String key = encode(entry.getKey());
            for (String raw : entry.getValue()) {
                if (raw == null) throw new IllegalArgumentException("null value");
                pairs.add(new Pair(key, encode(raw)));
            }
        }
        pairs.sort(Comparator.comparing(Pair::key).thenComparing(Pair::value));
        List<String> output = new ArrayList<>();
        for (Pair pair : pairs) output.add(pair.key()+"="+pair.value());
        return String.join("&", output);
    }
    private static String encode(String value) {
        byte[] bytes = value.getBytes(StandardCharsets.UTF_8);
        StringBuilder out = new StringBuilder();
        char[] hex = "0123456789ABCDEF".toCharArray();
        for (byte raw : bytes) {
            int b = raw & 0xFF;
            if ((b>='A'&&b<='Z')||(b>='a'&&b<='z')||(b>='0'&&b<='9')||b=='-'||b=='.'||b=='_'||b=='~') out.append((char)b);
            else out.append('%').append(hex[b>>>4]).append(hex[b&15]);
        }
        return out.toString();
    }
}
