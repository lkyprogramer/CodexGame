import java.util.*;
public class ServiceTest { static void eq(Object actual,Object expected){if(!Objects.equals(actual,expected))throw new AssertionError("expected="+expected+" actual="+actual);}static void yes(boolean value){if(!value)throw new AssertionError("contract violated");}public static void main(String[]args)throws Exception{
eq(Service.resolve(Map.of("orderId","legacy")),"legacy");eq(Service.resolve(Map.of("id","new","orderId","old")),"new");eq(Service.resolve(Map.of("id"," ","orderId","old")),"old");try{Service.resolve(Map.of());throw new AssertionError();}catch(IllegalArgumentException ok){}
System.out.println("PASS business-api-compatibility");}}
