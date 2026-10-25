import java.util.*;
public class ServiceTest { static void eq(Object actual,Object expected){if(!Objects.equals(actual,expected))throw new AssertionError("expected="+expected+" actual="+actual);}static void yes(boolean value){if(!value)throw new AssertionError("contract violated");}public static void main(String[]args)throws Exception{
var rows=List.of(new Service.Order(3,true),new Service.Order(1,true),new Service.Order(2,false),new Service.Order(4,true)); var a=Service.page(rows,0,2); eq(a.ids(),List.of(1,3));eq(a.total(),3);eq(Service.page(rows,1,2).ids(),List.of(4));eq(Service.page(rows,9,2).total(),3);try{Service.page(rows,-1,2);throw new AssertionError();}catch(IllegalArgumentException ok){}
System.out.println("PASS business-pagination");}}
