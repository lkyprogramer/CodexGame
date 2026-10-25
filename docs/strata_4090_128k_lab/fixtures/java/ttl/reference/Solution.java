public class Solution {public static boolean alive(long c,long n,long t){if(t<=0||n<c)return false;long d=n-c;return d>=0&&d<t;}}
