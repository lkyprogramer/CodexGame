import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;

public class TestMain {
    private static void check(boolean value, String message) {
        if (!value) throw new AssertionError(message);
    }
    private static void expectIAE(Runnable r) {
        try { r.run(); throw new AssertionError("expected IllegalArgumentException"); }
        catch (IllegalArgumentException expected) { }
    }
    public static void main(String[] args) throws Exception {
        expectIAE(() -> new RateLimiter(0, 10));
        expectIAE(() -> new RateLimiter(1, 0));
        RateLimiter limiter = new RateLimiter(2, 1000);
        check(limiter.allow("a", 1000), "first");
        check(limiter.allow("a", 1000), "second");
        check(!limiter.allow("a", 1500), "quota");
        check(limiter.allow("a", 2000), "left boundary expires");
        check(limiter.allow("b", 1500), "independent key");
        expectIAE(() -> limiter.allow("a", 1999));
        expectIAE(() -> limiter.allow("", 1));

        RateLimiter concurrent = new RateLimiter(3, 1000);
        ExecutorService pool = Executors.newFixedThreadPool(12);
        CountDownLatch start = new CountDownLatch(1);
        AtomicInteger allowed = new AtomicInteger();
        Future<?>[] futures = new Future<?>[24];
        for (int i = 0; i < futures.length; i++) {
            futures[i] = pool.submit(() -> {
                try { start.await(); } catch (InterruptedException e) { throw new RuntimeException(e); }
                if (concurrent.allow("same", 5000)) allowed.incrementAndGet();
            });
        }
        start.countDown();
        for (Future<?> f : futures) f.get();
        pool.shutdownNow();
        check(allowed.get() == 3, "concurrent quota: " + allowed.get());
        System.out.println("OK");
    }
}
