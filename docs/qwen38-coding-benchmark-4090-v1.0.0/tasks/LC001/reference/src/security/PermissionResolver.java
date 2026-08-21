import java.util.*;
public final class PermissionResolver{
 public boolean allowed(Set<String>grants,String required){
  if(grants==null||required==null||required.isBlank())throw new IllegalArgumentException("invalid permission");String target=PermissionParser.normalize(required);boolean allowed=false;
  for(String raw:grants){if(raw==null)throw new IllegalArgumentException("null grant");String grant=PermissionParser.normalize(raw);boolean deny=grant.startsWith("!");String pattern=deny?grant.substring(1):grant;if(matches(pattern,target)){if(deny)return false;allowed=true;}}
  return allowed;
 }
 private boolean matches(String pattern,String target){if(pattern.equals("*"))return true;if(pattern.endsWith(":*")){String prefix=pattern.substring(0,pattern.length()-1);return target.startsWith(prefix);}return pattern.equals(target);}
}
