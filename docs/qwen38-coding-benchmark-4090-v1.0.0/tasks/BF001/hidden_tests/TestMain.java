import java.util.*;
public class TestMain {
    static void eq(Object a,Object b){if(!Objects.equals(a,b))throw new AssertionError(a+" != "+b);} static void bad(Runnable r){try{r.run();throw new AssertionError();}catch(IllegalArgumentException e){}}
    public static void main(String[] args){
        ArrayList<Integer> src=new ArrayList<>(List.of(1,2,3,4,5));
        List<Integer> first=PageSlice.page(src,1,2);eq(first,List.of(1,2));eq(PageSlice.page(src,2,2),List.of(3,4));eq(PageSlice.page(src,3,2),List.of(5));eq(PageSlice.page(src,4,2),List.of());
        src.set(0,99);eq(first,List.of(1,2));
        try{first.add(3);throw new AssertionError();}catch(UnsupportedOperationException expected){}
        eq(PageSlice.page(src,Integer.MAX_VALUE,Integer.MAX_VALUE),List.of());
        bad(()->PageSlice.page(src,0,1));bad(()->PageSlice.page(src,1,0));bad(()->PageSlice.page(null,1,1));
        System.out.println("OK");
    }
}
