import java.util.*;
public class TestMain{static void eq(Object a,Object b){if(!Objects.equals(a,b))throw new AssertionError(a+" != "+b);}static void bad(Runnable r){try{r.run();throw new AssertionError();}catch(IllegalArgumentException e){}}
 public static void main(String[]a){
  eq(ProfileMapper.fromMap(Map.of("id","1","displayName"," Alice ")),new Profile("1","Alice"));eq(ProfileMapper.fromMap(Map.of("id","1","userName","Bob")),new Profile("1","Bob"));eq(ProfileMapper.fromMap(Map.of("id","1","displayName","A","userName"," A ")),new Profile("1","A"));bad(()->ProfileMapper.fromMap(Map.of("id","1","displayName","A","userName","B")));bad(()->ProfileMapper.fromMap(Map.of("id","1")));bad(()->ProfileMapper.fromMap(Map.of("id","1","displayName",3)));
  Map<String,Object>out=ProfileMapper.toMap(new Profile("2","C"));eq(out,Map.of("id","2","displayName","C"));try{out.put("x",1);throw new AssertionError();}catch(UnsupportedOperationException e){}
  System.out.println("OK");
 }
}
