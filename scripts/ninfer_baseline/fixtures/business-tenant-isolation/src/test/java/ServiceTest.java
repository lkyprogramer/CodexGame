import java.util.*;
public class ServiceTest { static void eq(Object actual,Object expected){if(!Objects.equals(actual,expected))throw new AssertionError("expected="+expected+" actual="+actual);}static void yes(boolean value){if(!value)throw new AssertionError("contract violated");}public static void main(String[]args)throws Exception{
var rows=List.of(new Service.Row(1,"o","one"),new Service.Row(2,"o","two"));eq(Service.find(rows,2,"o"),"two");eq(Service.find(rows,1,"o"),"one");eq(Service.find(rows,3,"o"),null);eq(Service.find(rows,1,"missing"),null);
System.out.println("PASS business-tenant-isolation");}}
