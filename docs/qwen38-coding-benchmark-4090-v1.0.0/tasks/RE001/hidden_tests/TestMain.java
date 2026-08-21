import java.util.*;import java.util.concurrent.*;import java.util.concurrent.atomic.*;
public class TestMain{
 static void check(boolean v,String m){if(!v)throw new AssertionError(m);}
 static final class Repo implements OrderRepository{final ConcurrentHashMap<String,Order> data=new ConcurrentHashMap<>();final AtomicInteger saves=new AtomicInteger();public Optional<Order> findByCommandId(String c){return Optional.ofNullable(data.get(c));}public void save(Order o)throws Exception{saves.incrementAndGet();Thread.sleep(20);if(data.putIfAbsent(o.commandId(),o)!=null)throw new IllegalStateException("duplicate");}}
 public static void main(String[]a)throws Exception{
   Repo repo=new Repo();AtomicInteger charges=new AtomicInteger();PaymentGateway gateway=(id,amount)->{charges.incrementAndGet();Thread.sleep(40);return "p-"+id;};OrderService service=new OrderService(repo,gateway);ExecutorService pool=Executors.newFixedThreadPool(16);
   try{CountDownLatch start=new CountDownLatch(1);List<Future<Order>> fs=new ArrayList<>();for(int i=0;i<16;i++)fs.add(pool.submit(()->{start.await();return service.create("cmd","o1",100);}));start.countDown();Order first=fs.get(0).get();for(Future<Order>f:fs)check(f.get().equals(first),"same result");check(charges.get()==1,"charges "+charges);check(repo.saves.get()==1,"saves");check(service.create("cmd","ignored",999).equals(first),"repeat");
     AtomicInteger attempts=new AtomicInteger();OrderService flaky=new OrderService(new Repo(),(id,amt)->{if(attempts.incrementAndGet()==1)throw new IllegalStateException("boom");return "ok";});try{flaky.create("retry","o",1);throw new AssertionError();}catch(IllegalStateException expected){}check(flaky.create("retry","o",1).paymentId().equals("ok"),"retry after failure");
     long t=System.nanoTime();Future<Order>x=pool.submit(()->service.create("a","a",1));Future<Order>y=pool.submit(()->service.create("b","b",1));x.get();y.get();check((System.nanoTime()-t)/1_000_000<115,"different commands serialized");
   }finally{pool.shutdownNow();}
   System.out.println("OK");
 }
}
