import java.nio.charset.StandardCharsets;import java.util.*;
public final class Paginator{
 private static final Comparator<Item>ORDER=Comparator.comparingLong(Item::score).reversed().thenComparing(Item::id);
 public static Page page(List<Item>input,String cursor,int limit){if(input==null||limit<1||limit>100)throw new IllegalArgumentException("invalid input");List<Item>items=new ArrayList<>(input);if(items.stream().anyMatch(x->x==null||x.id()==null))throw new IllegalArgumentException("invalid item");items.sort(ORDER);int start=0;
  if(cursor!=null){Item key=decode(cursor);int exact=Collections.binarySearch(items,key,ORDER);if(exact<0||!items.get(exact).equals(key))throw new IllegalArgumentException("cursor item not found");start=exact+1;}
  int end=Math.min(items.size(),start+limit);List<Item>slice=List.copyOf(items.subList(start,end));String next=end<items.size()&&!slice.isEmpty()?encode(slice.get(slice.size()-1)):null;return new Page(slice,next);
 }
 private static String encode(Item i){String raw=i.score()+"\n"+i.id();return Base64.getUrlEncoder().withoutPadding().encodeToString(raw.getBytes(StandardCharsets.UTF_8));}
 private static Item decode(String c){try{String raw=new String(Base64.getUrlDecoder().decode(c),StandardCharsets.UTF_8);int n=raw.indexOf('\n');if(n<1)throw new Exception();return new Item(raw.substring(n+1),Long.parseLong(raw.substring(0,n)));}catch(Exception e){throw new IllegalArgumentException("invalid cursor",e);}}
}
