import java.util.*;
public class TestMain{
    static void check(boolean v){if(!v)throw new AssertionError();}static void bad(Runnable r){try{r.run();throw new AssertionError();}catch(IllegalArgumentException e){}}
    public static void main(String[]a){
        UserId x=new UserId(" Alice "),y=new UserId("ALICE");check(x.equals(y));check(x.hashCode()==y.hashCode());check(x.compareTo(y)==0);check(x.toString().equals("alice"));
        Map<UserId,Integer> map=new HashMap<>();map.put(x,1);check(map.get(y)==1);
        TreeSet<UserId> set=new TreeSet<>();set.add(x);set.add(y);check(set.size()==1);
        bad(()->new UserId(null));bad(()->new UserId("   "));
        System.out.println("OK");
    }
}
