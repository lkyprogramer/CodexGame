import java.util.*;import java.util.function.Function;
public class TestMain{
 static void check(boolean v,String m){if(!v)throw new AssertionError(m);}static final class Fake implements Store{Map<String,Account>accounts=new HashMap<>();List<OutboxEvent>events=new ArrayList<>();boolean inTx;boolean failAppend;int outsideWrites;
  public Account load(String id){return accounts.get(id);}public void save(Account a){if(!inTx)outsideWrites++;accounts.put(a.id(),a);}public void append(OutboxEvent e){if(!inTx)outsideWrites++;if(failAppend)throw new IllegalStateException("outbox down");events.add(e);}
  public <T>T transaction(Function<Store,T>w){Map<String,Account>before=new HashMap<>(accounts);List<OutboxEvent>ev=new ArrayList<>(events);inTx=true;try{return w.apply(this);}catch(RuntimeException x){accounts=before;events=ev;throw x;}finally{inTx=false;}}
 }
 public static void main(String[]a){Fake f=new Fake();f.accounts.put("1",new Account("1","old"));AccountService s=new AccountService(f,()->"evt-1");Account n=s.rename("1"," New ");check(n.name().equals("New"),"trim");check(f.accounts.get("1").equals(n),"saved");check(f.events.size()==1&&f.events.get(0).type().equals("AccountRenamed")&&f.events.get(0).payload().equals("New"),"event");check(f.outsideWrites==0,"outside transaction");
  f.failAppend=true;try{s.rename("1","broken");throw new AssertionError();}catch(IllegalStateException e){}check(f.accounts.get("1").name().equals("New"),"rollback account");check(f.events.size()==1,"rollback event");System.out.println("OK");}
}
