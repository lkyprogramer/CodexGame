import java.util.*;
public class ServiceTest { static void eq(Object actual,Object expected){if(!Objects.equals(actual,expected))throw new AssertionError("expected="+expected+" actual="+actual);}static void yes(boolean value){if(!value)throw new AssertionError("contract violated");}public static void main(String[]args)throws Exception{
var s=new Service();eq(s.get("p"),null);s.put("p","old");eq(s.get("p"),"old");s.put("p","new");eq(s.get("p"),"new");s.delete("p");eq(s.get("p"),null);s.put("other","x");eq(s.get("other"),"x");
System.out.println("PASS business-cache-invalidation");}}
