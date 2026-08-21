import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Future;
public final class ParallelSum{
    public static long sum(List<Integer> values,ExecutorService executor)throws Exception{
        if(values==null||executor==null)throw new IllegalArgumentException("null argument");
        List<Future<Long>> futures=new ArrayList<>();
        for(Integer value:values)if(value!=null)futures.add(executor.submit(()->value.longValue()));
        long total=0;
        try{
            for(Future<Long> future:futures)total=Math.addExact(total,future.get());
            return total;
        }catch(ExecutionException e){
            Throwable cause=e.getCause();
            if(cause instanceof Exception ex)throw ex;
            throw e;
        }
    }
}
