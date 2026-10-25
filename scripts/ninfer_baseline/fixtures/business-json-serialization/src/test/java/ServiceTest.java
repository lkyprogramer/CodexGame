import java.util.*;
public class ServiceTest { static void eq(Object actual,Object expected){if(!Objects.equals(actual,expected))throw new AssertionError("expected="+expected+" actual="+actual);}static void yes(boolean value){if(!value)throw new AssertionError("contract violated");}public static void main(String[]args)throws Exception{
eq(Service.json(null),"null");eq(Service.json("plain"),"\"plain\"");eq(Service.json("a\"b"),"\"a\\\"b\"");eq(Service.json("\\"),"\"\\\\\"");eq(Service.json("\n\t"),"\"\\n\\t\"");eq(Service.json("\u0001"),"\"\\u0001\"");
System.out.println("PASS business-json-serialization");}}
