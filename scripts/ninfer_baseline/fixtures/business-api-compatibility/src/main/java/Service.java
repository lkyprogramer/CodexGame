import java.util.*;
public class Service {
static String resolve(java.util.Map<String,String> body){if(body.containsKey("id"))return body.get("id");String old=body.get("orderId");if(old==null||old.isBlank())throw new IllegalArgumentException("missing id");return old;}
}
