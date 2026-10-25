import java.util.*;
public class ServiceTest { static void eq(Object actual,Object expected){if(!Objects.equals(actual,expected))throw new AssertionError("expected="+expected+" actual="+actual);}static void yes(boolean value){if(!value)throw new AssertionError("contract violated");}public static void main(String[]args)throws Exception{
var m=Service.bind(new Service.Filter(7,99,null));eq(m.get("tenantId"),7L);eq(m.get("id"),99L);yes(m.containsKey("status"));eq(m.get("status"),null);eq(Service.bind(new Service.Filter(8,3,"OPEN")).get("status"),"OPEN");String xml=java.nio.file.Files.readString(java.nio.file.Path.of("mapper.xml"));yes(xml.contains("#{tenantId}")&&xml.contains("#{id}"));
System.out.println("PASS business-mybatis-parameter-contract");}}
