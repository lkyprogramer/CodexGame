public final class OrderService{
 private final OrderRepository repository;private final PaymentGateway gateway;
 public OrderService(OrderRepository repository,PaymentGateway gateway){this.repository=repository;this.gateway=gateway;}
 public Order create(String commandId,String orderId,long amount)throws Exception{
   String paymentId=gateway.charge(orderId,amount);Order order=new Order(commandId,orderId,amount,paymentId);repository.save(order);return order;
 }
}
