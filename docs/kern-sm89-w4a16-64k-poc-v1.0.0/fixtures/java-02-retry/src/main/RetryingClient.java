import java.util.concurrent.Callable;
public final class RetryingClient {
 private final RetryPolicy policy;
 public RetryingClient(RetryPolicy p){this.policy=p;}
 public <T>T call(Callable<T> operation)throws Exception{
  Exception last=null;
  for(int i=0;i<=policy.maxAttempts();i++){
   try{return operation.call();}catch(Exception x){last=x;}
  }
  throw last;
 }
}
