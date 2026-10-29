# ttl

Implement Java 8-compatible public class Solution, with no package declaration. Output Java code only, no markdown or explanation. Do not access files, network, processes, reflection or environment. Provide public static boolean alive(long created,long now,long ttl). It is true exactly when ttl>0, now>=created and mathematical (now-created)<ttl. Signed long subtraction must not overflow and change the answer. Expiry at equality is false.
