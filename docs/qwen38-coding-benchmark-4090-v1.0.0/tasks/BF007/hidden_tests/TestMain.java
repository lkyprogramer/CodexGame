import java.util.*;import java.util.concurrent.*;
public class TestMain{
    static void check(boolean v,String m){if(!v)throw new AssertionError(m);}
    public static void main(String[]a)throws Exception{
        ExecutorService pool=Executors.newFixedThreadPool(16);
        try{
            List<Integer> values=new ArrayList<>();for(int i=0;i<100000;i++)values.add(i%7);values.add(null);
            long expected=values.stream().filter(Objects::nonNull).mapToLong(Integer::longValue).sum();
            for(int i=0;i<8;i++)check(ParallelSum.sum(values,pool)==expected,"race");
            check(ParallelSum.sum(List.of(Integer.MAX_VALUE,Integer.MAX_VALUE),pool)==4294967294L,"long sum");
            try{ParallelSum.sum(null,pool);throw new AssertionError();}catch(IllegalArgumentException e){}
            check(!pool.isShutdown(),"must not close executor");
        }finally{pool.shutdownNow();}
        System.out.println("OK");
    }
}
