import java.util.*; public class Solution {public static boolean first(Set<String> s,String k){if(s==null||k==null)throw new IllegalArgumentException();synchronized(s){return s.add(k);}}}
