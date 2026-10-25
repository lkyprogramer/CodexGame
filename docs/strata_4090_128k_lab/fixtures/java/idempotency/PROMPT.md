# idempotency

Implement Java 8-compatible public class Solution, with no package declaration. Output Java code only, no markdown or explanation. Do not access files, network, processes, reflection or environment. Provide public static boolean first(java.util.Set<String> seen,String key). Atomically insert a non-null key and return true only to the first caller, even when seen is an ordinary HashSet shared by multiple threads. Null seen or null key throws IllegalArgumentException.
