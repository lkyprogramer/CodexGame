public final class RetryPolicy {
 private final int maxAttempts;
 public RetryPolicy(int maxAttempts){if(maxAttempts<1)throw new IllegalArgumentException("maxAttempts");this.maxAttempts=maxAttempts;}
 public int maxAttempts(){return maxAttempts;}
}
