import java.util.*;
public final class CachedUserRepository{private final UserStore store;private final UserCache cache;public CachedUserRepository(UserStore store,UserCache cache){if(store==null||cache==null)throw new IllegalArgumentException("null dependency");this.store=store;this.cache=cache;}
 private static String id(String id){if(id==null||id.isBlank())throw new IllegalArgumentException("invalid id");return id;}
 public Optional<User>find(String id){id=id(id);Optional<Optional<User>>cached=cache.get(id);if(cached.isPresent())return cached.get();Optional<User>loaded=store.find(id);cache.put(id,loaded);return loaded;}
 public void save(User user){if(user==null||user.id()==null||user.id().isBlank())throw new IllegalArgumentException("invalid user");store.save(user);cache.put(user.id(),Optional.of(user));}
 public void delete(String id){id=id(id);store.delete(id);cache.evict(id);}
}
