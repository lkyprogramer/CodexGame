import java.util.*;
public class ServiceTest { static void eq(Object actual,Object expected){if(!Objects.equals(actual,expected))throw new AssertionError("expected="+expected+" actual="+actual);}static void yes(boolean value){if(!value)throw new AssertionError("contract violated");}public static void main(String[]args)throws Exception{
var s=new Service();try{s.submit("o",true);throw new AssertionError();}catch(IllegalStateException ok){}yes(!s.orders.contains("o"));eq(s.events.size(),0);s.submit("o",false);s.submit("o",false);eq(s.orders.size(),1);eq(s.events,List.of("o"));
System.out.println("PASS business-outbox-atomicity");}}
