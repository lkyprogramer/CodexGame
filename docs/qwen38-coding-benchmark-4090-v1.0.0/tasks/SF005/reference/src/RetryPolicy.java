public final class RetryPolicy {
    private final long baseDelayMillis;
    private final long maxDelayMillis;
    public RetryPolicy(long baseDelayMillis, long maxDelayMillis) {
        if (baseDelayMillis <= 0 || maxDelayMillis < baseDelayMillis) throw new IllegalArgumentException("invalid delays");
        this.baseDelayMillis = baseDelayMillis;
        this.maxDelayMillis = maxDelayMillis;
    }
    public long delayMillis(int attempt, long retryAfterMillis) {
        if (attempt < 1) throw new IllegalArgumentException("attempt starts at one");
        if (retryAfterMillis < -1) throw new IllegalArgumentException("invalid retry-after");
        long backoff = baseDelayMillis;
        for (int i = 1; i < attempt && backoff < maxDelayMillis; i++) {
            if (backoff > maxDelayMillis / 2) backoff = maxDelayMillis;
            else backoff *= 2;
        }
        long candidate = retryAfterMillis == -1 ? backoff : Math.max(backoff, retryAfterMillis);
        return Math.min(maxDelayMillis, candidate);
    }
}
