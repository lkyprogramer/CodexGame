import java.util.concurrent.*;
import java.util.function.LongSupplier;
public final class SingleFlightCache{
    private record Entry(String value,long expiresAt){}
    private final ConcurrentHashMap<String,Entry> cache=new ConcurrentHashMap<>();
    private final ConcurrentHashMap<String,CompletableFuture<String>> inFlight=new ConcurrentHashMap<>();
    private final long ttl;private final LongSupplier clock;
    public SingleFlightCache(long ttl,LongSupplier clock){if(ttl<=0||clock==null)throw new IllegalArgumentException("invalid config");this.ttl=ttl;this.clock=clock;}
    public String get(String key,Callable<String> loader)throws Exception{
        if(key==null||key.isEmpty()||loader==null)throw new IllegalArgumentException("invalid input");
        long now=clock.getAsLong();Entry entry=cache.get(key);if(entry!=null&&entry.expiresAt()>now)return entry.value();
        CompletableFuture<String> mine=new CompletableFuture<>();CompletableFuture<String> existing=inFlight.putIfAbsent(key,mine);
        if(existing==null){
            try{
                String value=loader.call();if(value==null)throw new IllegalStateException("loader returned null");
                cache.put(key,new Entry(value,Math.addExact(clock.getAsLong(),ttl)));mine.complete(value);return value;
            }catch(Throwable t){mine.completeExceptionally(t);if(t instanceof Exception e)throw e;if(t instanceof Error e)throw e;throw new RuntimeException(t);}
            finally{inFlight.remove(key,mine);}
        }
        try{return existing.get();}
        catch(ExecutionException e){Throwable c=e.getCause();if(c instanceof Exception x)throw x;if(c instanceof Error x)throw x;throw new RuntimeException(c);}
    }
}
