import java.util.*;
import java.math.*;
public class Harness {
 static void check(boolean b){ if(!b)throw new AssertionError("check failed"); }
 static void eq(Object a,Object b){ if(!Objects.equals(a,b))throw new AssertionError("expected="+b+" actual="+a); }
 static void bad(Runnable r){ boolean seen=false; try{r.run();}catch(IllegalArgumentException e){seen=true;} if(!seen)throw new AssertionError("expected IllegalArgumentException"); }
 public static void main(String[] args) throws Exception {
Set<String> seen=new HashSet<>();java.util.concurrent.atomic.AtomicInteger won=new java.util.concurrent.atomic.AtomicInteger();java.util.concurrent.CountDownLatch gate=new java.util.concurrent.CountDownLatch(1);List<Thread> ts=new ArrayList<>();for(int i=0;i<20;i++){Thread t=new Thread(()->{try{gate.await();if(Solution.first(seen,"same"))won.incrementAndGet();}catch(InterruptedException e){throw new RuntimeException(e);}});ts.add(t);t.start();}gate.countDown();for(Thread t:ts)t.join();eq(won.get(),1);check(!Solution.first(seen,"same"));check(Solution.first(seen,"other"));bad(()->Solution.first(null,"x"));bad(()->Solution.first(seen,null));
System.out.println("ALL_OK");
}
}
