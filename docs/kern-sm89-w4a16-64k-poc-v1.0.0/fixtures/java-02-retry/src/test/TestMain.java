import java.io.IOException;
import java.util.concurrent.atomic.AtomicInteger;
public final class TestMain {
 static void check(boolean c,String m){if(!c)throw new AssertionError(m);}
 public static void main(String[] a)throws Exception{
  RetryingClient c=new RetryingClient(new RetryPolicy(3));AtomicInteger n=new AtomicInteger();IOException finalError=new IOException("persistent");
  try{c.call(()->{n.incrementAndGet();throw finalError;});throw new AssertionError("failure swallowed");}catch(IOException x){check(x==finalError,"last exception identity");}
  check(n.get()==3,"maxAttempts includes first call; got "+n.get());
  n.set(0);String value=c.call(()->{if(n.incrementAndGet()<3)throw new IOException("temporary");return "ok";});check(value.equals("ok")&&n.get()==3,"third attempt success");
  n.set(0);IllegalArgumentException fatal=new IllegalArgumentException("terminal");
  try{c.call(()->{n.incrementAndGet();throw fatal;});throw new AssertionError("fatal swallowed");}catch(IllegalArgumentException x){check(x==fatal,"fatal changed");}
  check(n.get()==1,"fatal exception retried");
  n.set(0);try{c.call(()->{n.incrementAndGet();throw new InterruptedException("cancel");});throw new AssertionError("interrupt swallowed");}catch(InterruptedException x){check(n.get()==1,"interrupt retried");check(Thread.currentThread().isInterrupted(),"interrupt flag missing");}finally{Thread.interrupted();}
  try{new RetryPolicy(0);throw new AssertionError("zero accepted");}catch(IllegalArgumentException expected){}
  check(new RetryingClient(new RetryPolicy(1)).call(()->"first").equals("first"),"single call");
  System.out.println("PASS retry");
 }
}
