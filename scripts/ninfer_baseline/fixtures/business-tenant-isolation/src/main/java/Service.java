import java.util.*;
public class Service {
record Row(long tenant,String id,String value){}static String find(java.util.List<Row> rows,long tenant,String id){return rows.stream().filter(r->r.id().equals(id)).map(Row::value).findFirst().orElse(null);}
}
