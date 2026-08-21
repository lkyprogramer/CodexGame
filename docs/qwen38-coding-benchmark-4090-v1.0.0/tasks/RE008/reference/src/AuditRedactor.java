import java.util.*;
public final class AuditRedactor{
 private static final List<String>SENSITIVE=List.of("password","secret","token","authorization");
 public static Object redact(Object value){return copy(value,new IdentityHashMap<>());}
 private static Object copy(Object value,IdentityHashMap<Object,Boolean>seen){
  if(value==null||value instanceof String||value instanceof Number||value instanceof Boolean)return value;
  if(seen.put(value,Boolean.TRUE)!=null)throw new IllegalArgumentException("cycle");
  try{
   if(value instanceof Map<?,?> map){Map<String,Object>out=new LinkedHashMap<>();for(var e:map.entrySet()){String key=String.valueOf(e.getKey());String lower=key.toLowerCase(Locale.ROOT);boolean sensitive=SENSITIVE.stream().anyMatch(lower::contains);out.put(key,sensitive?"***":copy(e.getValue(),seen));}return Collections.unmodifiableMap(out);}
   if(value instanceof List<?> list){List<Object>out=new ArrayList<>();for(Object x:list)out.add(copy(x,seen));return Collections.unmodifiableList(out);}
   throw new IllegalArgumentException("unsupported type: "+value.getClass());
  }finally{seen.remove(value);}
 }
}
