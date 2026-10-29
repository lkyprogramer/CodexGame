import java.util.*;
import java.math.*;
public class Harness {
 static void check(boolean b){ if(!b)throw new AssertionError("check failed"); }
 static void eq(Object a,Object b){ if(!Objects.equals(a,b))throw new AssertionError("expected="+b+" actual="+a); }
 static void bad(Runnable r){ boolean seen=false; try{r.run();}catch(IllegalArgumentException e){seen=true;} if(!seen)throw new AssertionError("expected IllegalArgumentException"); }
 public static void main(String[] args) throws Exception {
int[][] a={{5,7},{1,4},{3,6},{7,8}};eq(Arrays.deepToString(Solution.merge(a)),"[[1, 7], [7, 8]]");eq(Arrays.deepToString(a),"[[5, 7], [1, 4], [3, 6], [7, 8]]");eq(Solution.merge(new int[0][]).length,0);eq(Arrays.deepToString(Solution.merge(new int[][]{{Integer.MIN_VALUE,-1},{0,Integer.MAX_VALUE}})),"[[-2147483648, -1], [0, 2147483647]]");bad(()->Solution.merge(null));bad(()->Solution.merge(new int[][]{{2,2}}));bad(()->Solution.merge(new int[][]{{1}}));
System.out.println("ALL_OK");
}
}
