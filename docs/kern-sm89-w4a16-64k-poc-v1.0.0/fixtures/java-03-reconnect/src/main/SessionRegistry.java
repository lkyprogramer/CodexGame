import java.util.concurrent.ConcurrentHashMap;
public final class SessionRegistry {
 private final ConcurrentHashMap<String,Session> sessions=new ConcurrentHashMap<>();
 public void register(Session s){sessions.put(s.id,s);}
 public Session find(String id){return sessions.get(id);}
 public boolean removeIfCurrent(String id,Session expected){return sessions.remove(id)!=null;}
}
