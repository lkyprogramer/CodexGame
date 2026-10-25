import java.util.*;
public class ServiceTest { static void eq(Object actual,Object expected){if(!Objects.equals(actual,expected))throw new AssertionError("expected="+expected+" actual="+actual);}static void yes(boolean value){if(!value)throw new AssertionError("contract violated");}public static void main(String[]args)throws Exception{
var s=new Service();s.users.add(new Service.User(1,"alice",true));s.create(1,"alice");eq(s.users.size(),2);s.create(2,"alice");eq(s.users.size(),3);try{s.create(1,"alice");throw new AssertionError();}catch(IllegalStateException ok){}eq(s.users.size(),3);
System.out.println("PASS business-soft-delete");}}
