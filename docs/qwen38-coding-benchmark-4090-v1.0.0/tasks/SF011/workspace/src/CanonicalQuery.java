import java.net.URLEncoder; import java.nio.charset.StandardCharsets; import java.util.*;
public final class CanonicalQuery {
    public static String canonicalize(Map<String,List<String>> p){
        List<String> out=new ArrayList<>();
        p.forEach((k,vs)->vs.forEach(v->out.add(URLEncoder.encode(k,StandardCharsets.UTF_8)+"="+URLEncoder.encode(v,StandardCharsets.UTF_8))));
        Collections.sort(out); return String.join("&",out);
    }
}
