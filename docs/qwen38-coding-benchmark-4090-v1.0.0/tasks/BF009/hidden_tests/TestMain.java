import java.util.*;import java.util.concurrent.*;import java.util.concurrent.atomic.*;
public class TestMain{
    static void check(boolean v,String m){if(!v)throw new AssertionError(m);}
    public static void main(String[]a)throws Exception{
        AtomicLong clock=new AtomicLong();SingleFlightCache cache=new SingleFlightCache(10,clock::get);AtomicInteger loads=new AtomicInteger();ExecutorService pool=Executors.newFixedThreadPool(20);
        try{
            CountDownLatch start=new CountDownLatch(1);List<Future<String>> fs=new ArrayList<>();
            for(int i=0;i<20;i++)fs.add(pool.submit(()->{start.await();return cache.get("k",()->{loads.incrementAndGet();Thread.sleep(50);return "v";});}));
            start.countDown();for(Future<String> f:fs)check(f.get().equals("v"),"value");check(loads.get()==1,"single flight "+loads);
            check(cache.get("k",()->"bad").equals("v"),"cached");clock.set(10);check(cache.get("k",()->{loads.incrementAndGet();return "v2";}).equals("v2"),"expiry boundary");
            AtomicInteger failures=new AtomicInteger();List<Future<?>> bads=new ArrayList<>();CountDownLatch s2=new CountDownLatch(1);
            for(int i=0;i<5;i++)bads.add(pool.submit(()->{s2.await();try{cache.get("bad",()->{failures.incrementAndGet();Thread.sleep(30);throw new IllegalStateException("boom");});throw new AssertionError();}catch(IllegalStateException expected){check(expected.getMessage().equals("boom"),"cause");}return null;}));
            s2.countDown();for(Future<?> f:bads)f.get();check(failures.get()==1,"one failing load");check(cache.get("bad",()->"recovered").equals("recovered"),"retry after failure");
            long t=System.nanoTime();Future<String> a1=pool.submit(()->cache.get("a",()->{Thread.sleep(120);return "a";}));Future<String>b1=pool.submit(()->cache.get("b",()->{Thread.sleep(120);return "b";}));a1.get();b1.get();check((System.nanoTime()-t)/1_000_000<220,"different keys serialized");
        }finally{pool.shutdownNow();}
        System.out.println("OK");
    }
}
