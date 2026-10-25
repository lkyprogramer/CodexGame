import java.util.*;
import java.math.*;
public class Harness {
 static void check(boolean b){ if(!b)throw new AssertionError("check failed"); }
 static void eq(Object a,Object b){ if(!Objects.equals(a,b))throw new AssertionError("expected="+b+" actual="+a); }
 static void bad(Runnable r){ boolean seen=false; try{r.run();}catch(IllegalArgumentException e){seen=true;} if(!seen)throw new AssertionError("expected IllegalArgumentException"); }
 public static void main(String[] args) throws Exception {
check(Solution.alive(100,105,6));check(!Solution.alive(100,106,6));check(!Solution.alive(100,99,6));check(!Solution.alive(1,1,0));check(!Solution.alive(Long.MIN_VALUE,Long.MAX_VALUE,Long.MAX_VALUE));check(Solution.alive(Long.MIN_VALUE,Long.MIN_VALUE+10,11));check(!Solution.alive(-5,5,10));
System.out.println("ALL_OK");
}
}
