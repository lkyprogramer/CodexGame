import java.util.*;
public class ServiceTest { static void eq(Object actual,Object expected){if(!Objects.equals(actual,expected))throw new AssertionError("expected="+expected+" actual="+actual);}static void yes(boolean value){if(!value)throw new AssertionError("contract violated");}public static void main(String[]args)throws Exception{
var original=new IllegalArgumentException("driver failure");try{Service.load(id->{throw original;},"o-42");throw new AssertionError();}catch(IllegalStateException e){eq(e.getCause(),original);yes(e.getMessage().contains("o-42"));}eq(Service.load(id->"value","ok"),"value");
System.out.println("PASS business-exception-cause");}}
