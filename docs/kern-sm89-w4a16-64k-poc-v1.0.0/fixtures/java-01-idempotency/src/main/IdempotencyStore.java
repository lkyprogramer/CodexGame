import java.util.concurrent.ConcurrentHashMap;
import java.util.function.Supplier;
public final class IdempotencyStore {
    private final ConcurrentHashMap<String,String> values = new ConcurrentHashMap<>();
    public String execute(String key, Supplier<String> operation) {
        if (key == null || key.trim().isEmpty()) throw new IllegalArgumentException("key");
        String value = operation.get();
        values.put(key, value);
        return value;
    }
}
