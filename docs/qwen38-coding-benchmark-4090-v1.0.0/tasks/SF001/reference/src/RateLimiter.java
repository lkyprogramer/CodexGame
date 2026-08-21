import java.util.ArrayDeque;
import java.util.HashMap;
import java.util.Map;

public final class RateLimiter {
    private final int maxRequests;
    private final long windowMillis;
    private final Map<String, ArrayDeque<Long>> requests = new HashMap<>();
    private final Map<String, Long> lastSeen = new HashMap<>();

    public RateLimiter(int maxRequests, long windowMillis) {
        if (maxRequests <= 0 || windowMillis <= 0) {
            throw new IllegalArgumentException("limits must be positive");
        }
        this.maxRequests = maxRequests;
        this.windowMillis = windowMillis;
    }

    public synchronized boolean allow(String key, long nowMillis) {
        if (key == null || key.isEmpty()) {
            throw new IllegalArgumentException("key must not be empty");
        }
        Long previous = lastSeen.get(key);
        if (previous != null && nowMillis < previous) {
            throw new IllegalArgumentException("time moved backwards");
        }
        lastSeen.put(key, nowMillis);
        ArrayDeque<Long> queue = requests.computeIfAbsent(key, ignored -> new ArrayDeque<>());
        long boundary = nowMillis - windowMillis;
        while (!queue.isEmpty() && queue.peekFirst() <= boundary) {
            queue.removeFirst();
        }
        if (queue.size() >= maxRequests) {
            return false;
        }
        queue.addLast(nowMillis);
        return true;
    }
}
