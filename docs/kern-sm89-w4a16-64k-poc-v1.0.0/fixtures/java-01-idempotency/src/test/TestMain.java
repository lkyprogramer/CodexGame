import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;
public final class TestMain {
 static void check(boolean c,String m){if(!c)throw new AssertionError(m);}
 public static void main(String[] args)throws Exception{
  IdempotencyStore s=new IdempotencyStore();AtomicInteger n=new AtomicInteger();
  check(s.execute("a",()->"v"+n.incrementAndGet()).equals("v1"),"first result");
  check(s.execute("a",()->"v"+n.incrementAndGet()).equals("v1"),"same key must reuse original result");
  check(n.get()==1,"sequential duplicate side effect");
  try{s.execute("fail",()->{throw new IllegalStateException("retryable later");});throw new AssertionError("exception swallowed");}catch(IllegalStateException expected){}
  check(s.execute("fail",()->"ok").equals("ok"),"failed operation cached");
  try{s.execute("  ",()->"x");throw new AssertionError("blank key accepted");}catch(IllegalArgumentException expected){}
  ExecutorService e=Executors.newFixedThreadPool(12);
  try{
   AtomicInteger count=new AtomicInteger();CountDownLatch go=new CountDownLatch(1);List<Future<String>> fs=new ArrayList<>();
   for(int i=0;i<12;i++)fs.add(e.submit(()->{go.await();return s.execute("parallel",()->{count.incrementAndGet();try{Thread.sleep(40);}catch(InterruptedException x){Thread.currentThread().interrupt();throw new RuntimeException(x);}return "one";});}));
   go.countDown();for(Future<String> f:fs)check(f.get(4,TimeUnit.SECONDS).equals("one"),"parallel value");
   check(count.get()==1,"parallel duplicate side effects: "+count.get());
   CountDownLatch entered=new CountDownLatch(1),release=new CountDownLatch(1);
   Future<String> first=e.submit(()->s.execute("slow-key",()->{entered.countDown();try{release.await();}catch(InterruptedException x){throw new RuntimeException(x);}return "slow";}));
   check(entered.await(2,TimeUnit.SECONDS),"slow key never started");
   try{Future<String> other=e.submit(()->s.execute("independent-key",()->"fast"));check(other.get(2,TimeUnit.SECONDS).equals("fast"),"global serialization");}finally{release.countDown();}
   first.get(3,TimeUnit.SECONDS);
  }finally{e.shutdownNow();}
  System.out.println("PASS idempotency");
 }
}
