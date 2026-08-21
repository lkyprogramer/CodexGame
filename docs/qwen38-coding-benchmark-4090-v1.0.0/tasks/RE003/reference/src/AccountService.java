public final class AccountService{
 private final Store store;private final IdGenerator ids;
 public AccountService(Store store,IdGenerator ids){if(store==null||ids==null)throw new IllegalArgumentException("null dependency");this.store=store;this.ids=ids;}
 public Account rename(String id,String name){if(id==null||id.isBlank()||name==null||name.isBlank())throw new IllegalArgumentException("invalid input");
  return store.transaction(tx->{Account current=tx.load(id);if(current==null)throw new IllegalArgumentException("unknown account");Account next=new Account(id,name.trim());tx.save(next);tx.append(new OutboxEvent(ids.next(),"AccountRenamed",id,next.name()));return next;});
 }
}
