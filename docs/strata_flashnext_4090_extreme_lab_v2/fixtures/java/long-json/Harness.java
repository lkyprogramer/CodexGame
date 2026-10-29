import java.util.*;
public class Harness {
 static void eq(Object a,Object b) { if(!Objects.equals(a,b)) throw new AssertionError("expected="+b+" actual="+a); }
 public static void main(String[] args) {
  eq(Solution.idsJson(new long[]{Long.MAX_VALUE,Long.MIN_VALUE,0}), "[\"9223372036854775807\",\"-9223372036854775808\",\"0\"]");
  eq(Solution.idsJson(null), "[]");
  eq(Solution.idsJson(new long[0]), "[]");
  eq(Solution.idsJson(new long[]{1,-1}), "[\"1\",\"-1\"]");
  System.out.println("ALL_OK");
 }
}
