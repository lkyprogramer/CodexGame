import java.util.*;
public class ServiceTest { static void eq(Object actual,Object expected){if(!Objects.equals(actual,expected))throw new AssertionError("expected="+expected+" actual="+actual);}static void yes(boolean value){if(!value)throw new AssertionError("contract violated");}public static void main(String[]args)throws Exception{
eq(Service.total(List.of(new java.math.BigDecimal("0.005"),new java.math.BigDecimal("0.005"))).toPlainString(),"0.01");eq(Service.total(List.of()).toPlainString(),"0.00");eq(Service.total(List.of(new java.math.BigDecimal("1.234"),new java.math.BigDecimal("2.345"))).toPlainString(),"3.58");
System.out.println("PASS business-money-rounding");}}
