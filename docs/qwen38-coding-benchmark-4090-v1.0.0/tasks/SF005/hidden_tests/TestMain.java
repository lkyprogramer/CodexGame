public class TestMain {
    static void eq(long a,long b){if(a!=b)throw new AssertionError(a+" != "+b);} 
    static void bad(Runnable r){try{r.run();throw new AssertionError();}catch(IllegalArgumentException e){}}
    public static void main(String[] args){
        bad(() -> new RetryPolicy(0, 10)); bad(() -> new RetryPolicy(20, 10));
        RetryPolicy p=new RetryPolicy(100,10_000);
        eq(p.delayMillis(1,-1),100); eq(p.delayMillis(4,-1),800);
        eq(p.delayMillis(4,2_000),2_000); eq(p.delayMillis(20,-1),10_000);
        eq(p.delayMillis(Integer.MAX_VALUE,Long.MAX_VALUE),10_000);
        bad(() -> p.delayMillis(0,-1)); bad(() -> p.delayMillis(1,-2));
        RetryPolicy huge=new RetryPolicy(Long.MAX_VALUE/2,Long.MAX_VALUE-1);
        eq(huge.delayMillis(3,-1),Long.MAX_VALUE-1);
        System.out.println("OK");
    }
}
