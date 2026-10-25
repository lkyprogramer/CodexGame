public class Solution {public static int lowerBound(int[] a,int x){if(a==null)throw new IllegalArgumentException();int l=0,r=a.length;while(l<r){int m=l+(r-l)/2;if(a[m]<x)l=m+1;else r=m;}return l;}}
