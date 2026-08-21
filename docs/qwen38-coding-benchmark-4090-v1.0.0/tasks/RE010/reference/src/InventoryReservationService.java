import java.util.*;
public final class InventoryReservationService{private final InventoryRepository repo;public InventoryReservationService(InventoryRepository repo){if(repo==null)throw new IllegalArgumentException("null repo");this.repo=repo;}
 public Map<String,Integer>reserve(Map<String,Integer>requested){if(requested==null||requested.isEmpty())throw new IllegalArgumentException("empty request");Map<String,Integer>copy=new TreeMap<>();for(var e:requested.entrySet()){if(e.getKey()==null||e.getKey().isBlank()||e.getValue()==null||e.getValue()<=0)throw new IllegalArgumentException("invalid quantity");copy.put(e.getKey(),e.getValue());}
  return repo.transaction(tx->{Map<String,Integer>after=new LinkedHashMap<>();for(var e:copy.entrySet()){Integer current=tx.get(e.getKey());if(current==null)throw new IllegalArgumentException("unknown sku "+e.getKey());if(current<e.getValue())throw new IllegalStateException("insufficient "+e.getKey());after.put(e.getKey(),current-e.getValue());}for(var e:after.entrySet())tx.set(e.getKey(),e.getValue());return Collections.unmodifiableMap(new LinkedHashMap<>(after));});
 }
}
