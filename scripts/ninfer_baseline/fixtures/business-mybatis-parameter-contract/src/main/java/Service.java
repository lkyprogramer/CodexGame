import java.util.*;
public class Service {
record Filter(long tenantId,long id,String status){} static java.util.Map<String,Object> bind(Filter f){var m=new java.util.HashMap<String,Object>();m.put("tenant",f.tenantId());m.put("id",f.id());m.put("status",f.status());return m;}
}
