import java.util.*;
public class ServiceTest { static void eq(Object actual,Object expected){if(!Objects.equals(actual,expected))throw new AssertionError("expected="+expected+" actual="+actual);}static void yes(boolean value){if(!value)throw new AssertionError("contract violated");}public static void main(String[]args)throws Exception{
var r=Service.ingest(List.of("a","bad-1","b","bad-2","c"));eq(r.accepted(),List.of("a","b","c"));eq(r.rejected(),List.of("bad-1","bad-2"));eq(Service.ingest(List.of()).accepted(),List.of());eq(Service.ingest(List.of("bad-x")).accepted(),List.of());
System.out.println("PASS business-batch-failure");}}
