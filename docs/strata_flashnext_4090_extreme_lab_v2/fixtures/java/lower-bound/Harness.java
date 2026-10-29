import java.util.*;
import java.math.*;
public class Harness {
 static void check(boolean b){ if(!b)throw new AssertionError("check failed"); }
 static void eq(Object a,Object b){ if(!Objects.equals(a,b))throw new AssertionError("expected="+b+" actual="+a); }
 static void bad(Runnable r){ boolean seen=false; try{r.run();}catch(IllegalArgumentException e){seen=true;} if(!seen)throw new AssertionError("expected IllegalArgumentException"); }
 public static void main(String[] args) throws Exception {
int[] a={-3,0,0,5,Integer.MAX_VALUE};eq(Solution.lowerBound(a,0),1);eq(Solution.lowerBound(a,1),3);eq(Solution.lowerBound(a,Integer.MIN_VALUE),0);eq(Solution.lowerBound(new int[0],9),0);bad(()->Solution.lowerBound(null,1));Random r=new Random(71);for(int t=0;t<100;t++){int[] b=new int[150];for(int i=0;i<b.length;i++)b[i]=r.nextInt(100);Arrays.sort(b);int x=r.nextInt(120)-10;int e=0;while(e<b.length&&b[e]<x)e++;eq(Solution.lowerBound(b,x),e);}
System.out.println("ALL_OK");
}
}
