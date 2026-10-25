import java.util.*;
public class Service {
final java.util.Map<String,String> db=new java.util.HashMap<>(); final java.util.Map<String,java.util.Optional<String>> cache=new java.util.HashMap<>(); String get(String id){return cache.computeIfAbsent(id,k->java.util.Optional.ofNullable(db.get(k))).orElse(null);} void put(String id,String value){db.put(id,value);} void delete(String id){db.remove(id);cache.remove(id);}
}
