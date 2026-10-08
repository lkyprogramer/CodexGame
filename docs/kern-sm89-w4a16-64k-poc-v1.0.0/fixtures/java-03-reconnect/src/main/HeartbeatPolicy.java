public final class HeartbeatPolicy {
 private final long timeoutMillis;
 public HeartbeatPolicy(long timeoutSeconds){if(timeoutSeconds<1)throw new IllegalArgumentException("timeoutSeconds");this.timeoutMillis=timeoutSeconds;}
 public boolean expired(long lastSeenMillis,long nowMillis){return nowMillis-lastSeenMillis>timeoutMillis;}
}
