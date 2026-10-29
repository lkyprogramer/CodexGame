import java.util.*;
import java.math.*;
public class Harness {
 static void check(boolean b){ if(!b)throw new AssertionError("check failed"); }
 static void eq(Object a,Object b){ if(!Objects.equals(a,b))throw new AssertionError("expected="+b+" actual="+a); }
 static void bad(Runnable r){ boolean seen=false; try{r.run();}catch(IllegalArgumentException e){seen=true;} if(!seen)throw new AssertionError("expected IllegalArgumentException"); }
 public static void main(String[] args) throws Exception {
eq(Solution.cents("1.005"),100L);eq(Solution.cents("1.015"),102L);eq(Solution.cents("-1.005"),-100L);eq(Solution.cents("0"),0L);eq(Solution.cents("1234567890123.45"),123456789012345L);bad(()->Solution.cents(null));bad(()->Solution.cents("x"));bad(()->Solution.cents("92233720368547758.08")); for(int i=-500;i<=500;i++){String s=BigDecimal.valueOf(i,2).toPlainString();eq(Solution.cents(s),(long)i);}
System.out.println("ALL_OK");
}
}
