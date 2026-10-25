import java.util.*;
import java.math.*;
public class Harness {
 static void check(boolean b){ if(!b)throw new AssertionError("check failed"); }
 static void eq(Object a,Object b){ if(!Objects.equals(a,b))throw new AssertionError("expected="+b+" actual="+a); }
 static void bad(Runnable r){ boolean seen=false; try{r.run();}catch(IllegalArgumentException e){seen=true;} if(!seen)throw new AssertionError("expected IllegalArgumentException"); }
 public static void main(String[] args) throws Exception {
List<String> in=Arrays.asList(" A ",null,"", "a", "B", " b "," I ");Locale old=Locale.getDefault();try{Locale.setDefault(new Locale("tr","TR"));eq(Solution.normalize(in),Arrays.asList("a","b","i"));}finally{Locale.setDefault(old);}eq(in.get(0)," A ");eq(Solution.normalize(null),Collections.emptyList());
System.out.println("ALL_OK");
}
}
