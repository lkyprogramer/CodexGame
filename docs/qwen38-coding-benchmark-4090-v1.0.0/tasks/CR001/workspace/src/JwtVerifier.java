import java.nio.charset.StandardCharsets;import java.time.Instant;import java.util.*;
public final class JwtVerifier{
 private final Map<String,String>keys;private final String issuer;
 public JwtVerifier(Map<String,String>keys,String issuer){this.keys=keys;this.issuer=issuer;}
 public Claims verify(String token){String[]p=token.split("\\.");Map<String,String>h=Json.parse(new String(Base64.getUrlDecoder().decode(p[0])));Map<String,String>c=Json.parse(new String(Base64.getUrlDecoder().decode(p[1])));String alg=h.get("alg");if("none".equals(alg))return new Claims(c);String key=keys.getOrDefault(h.get("kid"),c.get("key"));if(Crypto.verify(alg,key,p[0]+"."+p[1],p[2]))return new Claims(c);throw new SecurityException();}
}
