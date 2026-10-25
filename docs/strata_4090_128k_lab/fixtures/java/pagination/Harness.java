import java.util.*;
import java.math.*;
public class Harness {
 static void check(boolean b){ if(!b)throw new AssertionError("check failed"); }
 static void eq(Object a,Object b){ if(!Objects.equals(a,b))throw new AssertionError("expected="+b+" actual="+a); }
 static void bad(Runnable r){ boolean seen=false; try{r.run();}catch(IllegalArgumentException e){seen=true;} if(!seen)throw new AssertionError("expected IllegalArgumentException"); }
 public static void main(String[] args) throws Exception {
eq(Solution.offset(1,20),0L);eq(Solution.offset(2,500),500L);eq(Solution.offset(Long.MAX_VALUE,1),Long.MAX_VALUE-1);bad(()->Solution.offset(0,1));bad(()->Solution.offset(1,0));bad(()->Solution.offset(1,501));bad(()->Solution.offset(Long.MAX_VALUE,500));for(long i=1;i<1000;i++)eq(Solution.offset(i,17),(i-1)*17);
System.out.println("ALL_OK");
}
}
