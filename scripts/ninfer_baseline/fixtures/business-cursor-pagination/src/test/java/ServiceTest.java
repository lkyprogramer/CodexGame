import java.util.*;
public class ServiceTest { static void eq(Object actual,Object expected){if(!Objects.equals(actual,expected))throw new AssertionError("expected="+expected+" actual="+actual);}static void yes(boolean value){if(!value)throw new AssertionError("contract violated");}public static void main(String[]args)throws Exception{
var rows=List.of(new Service.Row(10,3),new Service.Row(11,1),new Service.Row(10,1),new Service.Row(10,2));eq(Service.next(rows,10,1,2),List.of(new Service.Row(10,2),new Service.Row(10,3)));eq(Service.next(rows,10,3,2),List.of(new Service.Row(11,1)));eq(Service.next(rows,11,1,2),List.of());
System.out.println("PASS business-cursor-pagination");}}
