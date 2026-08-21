import java.util.*;import java.util.concurrent.*;import java.util.function.LongSupplier;
public final class SingleFlightCache{
    private final Map<String,String> cache=new HashMap<>();private final long ttl;private final LongSupplier clock;
    public SingleFlightCache(long ttl,LongSupplier clock){this.ttl=ttl;this.clock=clock;}
    public String get(String key,Callable<String> loader)throws Exception{
        String v=cache.get(key);if(v==null){v=loader.call();cache.put(key,v);}return v;
    }
}
