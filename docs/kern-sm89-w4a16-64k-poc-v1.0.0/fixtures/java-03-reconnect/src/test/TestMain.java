public final class TestMain {
 static void check(boolean c,String m){if(!c)throw new AssertionError(m);}
 public static void main(String[] a){
  HeartbeatPolicy p=new HeartbeatPolicy(30);
  check(!p.expired(100000,101000),"one second is not thirty seconds");
  check(!p.expired(100000,129999),"premature expiry");
  check(p.expired(100000,130000),"boundary must expire");
  check(!p.expired(100000,99999),"clock rollback");
  try{new HeartbeatPolicy(Long.MAX_VALUE);throw new AssertionError("conversion overflow accepted");}catch(ArithmeticException expected){}
  SessionRegistry r=new SessionRegistry();Session old=new Session("x",1),fresh=new Session("x",2);
  r.register(old);r.register(fresh);check(!r.removeIfCurrent("x",old),"stale cleanup removed fresh session");
  check(r.find("x")==fresh,"fresh lost");check(r.removeIfCurrent("x",fresh),"current cleanup failed");check(r.find("x")==null,"current remains");
  check(!r.removeIfCurrent("x",old),"missing removal must be false");
  System.out.println("PASS reconnect");
 }
}
