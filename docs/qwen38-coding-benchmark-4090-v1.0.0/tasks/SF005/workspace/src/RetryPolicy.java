public final class RetryPolicy {
    private final long baseDelayMillis;
    private final long maxDelayMillis;
    public RetryPolicy(long baseDelayMillis, long maxDelayMillis) {
        this.baseDelayMillis = baseDelayMillis;
        this.maxDelayMillis = maxDelayMillis;
    }
    public long delayMillis(int attempt, long retryAfterMillis) {
        long backoff = baseDelayMillis * (1L << (attempt - 1));
        return Math.min(maxDelayMillis, Math.max(backoff, retryAfterMillis));
    }
}
