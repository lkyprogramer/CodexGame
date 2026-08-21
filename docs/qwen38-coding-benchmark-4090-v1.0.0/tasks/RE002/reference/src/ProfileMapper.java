import java.util.*;
public final class ProfileMapper{
 public static Profile fromMap(Map<String,Object> map){
  if(map==null)throw new IllegalArgumentException("null map");String id=string(map.get("id"),"id");
  String modern=optional(map.get("displayName"));String legacy=optional(map.get("userName"));
  if(modern==null&&legacy==null)throw new IllegalArgumentException("missing display name");
  if(modern!=null&&legacy!=null&&!modern.equals(legacy))throw new IllegalArgumentException("conflicting names");
  return new Profile(id,modern!=null?modern:legacy);
 }
 public static Map<String,Object>toMap(Profile p){if(p==null)throw new IllegalArgumentException("null profile");return Map.of("id",p.id(),"displayName",p.displayName());}
 private static String string(Object v,String name){String s=optional(v);if(s==null)throw new IllegalArgumentException("invalid "+name);return s;}
 private static String optional(Object v){if(v==null)return null;if(!(v instanceof String s))throw new IllegalArgumentException("expected string");s=s.trim();if(s.isEmpty())throw new IllegalArgumentException("empty string");return s;}
}
