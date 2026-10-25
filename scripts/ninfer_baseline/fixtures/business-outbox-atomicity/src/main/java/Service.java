import java.util.*;
public class Service {
final java.util.Set<String> orders=new java.util.HashSet<>();final java.util.List<String> events=new java.util.ArrayList<>();synchronized void submit(String id,boolean fail){if(orders.contains(id))return;orders.add(id);if(fail)throw new IllegalStateException("outbox write failed");events.add(id);}
}
