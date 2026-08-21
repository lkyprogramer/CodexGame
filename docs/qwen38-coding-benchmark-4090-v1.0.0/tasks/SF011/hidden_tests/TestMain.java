import java.util.*;
public class TestMain {
    static void eq(String a,String b){if(!a.equals(b))throw new AssertionError(a+" != "+b);} static void bad(Runnable r){try{r.run();throw new AssertionError();}catch(IllegalArgumentException e){}}
    public static void main(String[] args){
        eq(CanonicalQuery.canonicalize(Map.of()),"");
        LinkedHashMap<String,List<String>> m=new LinkedHashMap<>();m.put("z",List.of("2","1"));m.put("a b",List.of("x/y","~"));
        eq(CanonicalQuery.canonicalize(m),"a%20b=x%2Fy&a%20b=~&z=1&z=2");
        eq(CanonicalQuery.canonicalize(Map.of("汉",List.of("字"))),"%E6%B1%89=%E5%AD%97");
        eq(CanonicalQuery.canonicalize(Map.of("k",List.of("",""))),"k=&k=");
        bad(() -> CanonicalQuery.canonicalize(null));
        Map<String,List<String>> nullList=new HashMap<>();nullList.put("a",null);bad(() -> CanonicalQuery.canonicalize(nullList));
        Map<String,List<String>> nullValue=new HashMap<>();nullValue.put("a",Arrays.asList("x",null));bad(() -> CanonicalQuery.canonicalize(nullValue));
        System.out.println("OK");
    }
}
