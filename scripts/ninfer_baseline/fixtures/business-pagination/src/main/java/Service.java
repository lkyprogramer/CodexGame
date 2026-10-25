import java.util.*;
public class Service {
record Order(int id, boolean active) {} record Page(java.util.List<Integer> ids,int total) {} static Page page(java.util.List<Order> rows,int p,int size) { if(p<0||size<=0) throw new IllegalArgumentException(); var all=rows.stream().filter(Order::active).sorted(java.util.Comparator.comparingInt(Order::id)).toList(); var ids=all.stream().skip((long)p*size).limit(size).map(Order::id).toList(); return new Page(ids,ids.size()); }
}
