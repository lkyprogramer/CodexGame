import java.util.*;
public class Service {
record Row(long time,long id){}static java.util.List<Row> next(java.util.List<Row> rows,long time,long id,int limit){return rows.stream().filter(r->r.time()>time).sorted(java.util.Comparator.comparingLong(Row::time).thenComparingLong(Row::id)).limit(limit).toList();}
}
