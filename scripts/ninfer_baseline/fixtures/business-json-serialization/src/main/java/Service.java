import java.util.*;
public class Service {
static String json(String value){ if(value==null)return "null";return "\""+value.replace("\"","\\\"")+"\""; }
}
