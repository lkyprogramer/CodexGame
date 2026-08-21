import java.util.concurrent.*;
public final class OrderService{
 private final OrderRepository repository;private final PaymentGateway gateway;
 private final ConcurrentHashMap<String,CompletableFuture<Order>> inFlight=new ConcurrentHashMap<>();
 public OrderService(OrderRepository repository,PaymentGateway gateway){if(repository==null||gateway==null)throw new IllegalArgumentException("null dependency");this.repository=repository;this.gateway=gateway;}
 public Order create(String commandId,String orderId,long amount)throws Exception{
   if(commandId==null||commandId.isBlank()||orderId==null||orderId.isBlank()||amount<=0)throw new IllegalArgumentException("invalid command");
   var persisted=repository.findByCommandId(commandId);if(persisted.isPresent())return persisted.get();
   CompletableFuture<Order> mine=new CompletableFuture<>();CompletableFuture<Order> existing=inFlight.putIfAbsent(commandId,mine);
   if(existing!=null)return await(existing);
   try{
     var second=repository.findByCommandId(commandId);if(second.isPresent()){mine.complete(second.get());return second.get();}
     String paymentId=gateway.charge(orderId,amount);if(paymentId==null)throw new IllegalStateException("null payment id");
     Order order=new Order(commandId,orderId,amount,paymentId);repository.save(order);mine.complete(order);return order;
   }catch(Throwable t){mine.completeExceptionally(t);if(t instanceof Exception e)throw e;if(t instanceof Error e)throw e;throw new RuntimeException(t);}
   finally{inFlight.remove(commandId,mine);}
 }
 private static Order await(CompletableFuture<Order> future)throws Exception{
   try{return future.get();}catch(ExecutionException e){Throwable c=e.getCause();if(c instanceof Exception x)throw x;if(c instanceof Error x)throw x;throw new RuntimeException(c);}
 }
}
