import java.util.*;import java.util.concurrent.*;
public final class ParallelSum{
    public static long sum(List<Integer> values,ExecutorService executor)throws Exception{
        long[] total={0};List<Future<?>> fs=new ArrayList<>();
        for(Integer v:values)if(v!=null)fs.add(executor.submit(()->total[0]+=v));
        for(Future<?>f:fs)f.get();return total[0];
    }
}
