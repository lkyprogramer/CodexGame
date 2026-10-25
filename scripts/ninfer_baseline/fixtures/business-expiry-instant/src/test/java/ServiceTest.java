import java.util.*;
public class ServiceTest { static void eq(Object actual,Object expected){if(!Objects.equals(actual,expected))throw new AssertionError("expected="+expected+" actual="+actual);}static void yes(boolean value){if(!value)throw new AssertionError("contract violated");}public static void main(String[]args)throws Exception{
var exp=java.time.OffsetDateTime.parse("2026-10-20T10:00:00+08:00");yes(Service.expired(exp,java.time.OffsetDateTime.parse("2026-10-20T02:00:00Z")));yes(!Service.expired(exp,java.time.OffsetDateTime.parse("2026-10-20T01:59:59Z")));yes(Service.expired(exp,java.time.OffsetDateTime.parse("2026-10-20T02:00:01Z")));
System.out.println("PASS business-expiry-instant");}}
