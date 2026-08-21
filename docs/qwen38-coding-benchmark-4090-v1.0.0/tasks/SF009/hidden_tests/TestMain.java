import java.math.BigDecimal;
import java.util.*;
public class TestMain {
    static void check(boolean v,String m){if(!v)throw new AssertionError(m);} static void bad(Runnable r){try{r.run();throw new AssertionError();}catch(IllegalArgumentException e){}}
    public static void main(String[] args){
        Money a=Money.of("12.345","usd"); check(a.toString().equals("USD 12.34"),"half even down");
        Money b=Money.of("0.015","USD"); check(b.toString().equals("USD 0.02"),"half even up");
        check(a.add(b).toString().equals("USD 12.36"),"add");
        check(a.subtract(Money.of("2.34","USD")).toString().equals("USD 10.00"),"subtract");
        check(Money.of("2.00","EUR").multiply(new BigDecimal("1.125")).toString().equals("EUR 2.25"),"multiply");
        check(Money.of("1","usd").equals(Money.of("1.000","USD")),"normalized equals");
        Set<Money> set=new HashSet<>();set.add(Money.of("1","USD"));set.add(Money.of("1.00","usd"));check(set.size()==1,"hash");
        bad(() -> Money.of("x","USD")); bad(() -> Money.of("1","US")); bad(() -> a.add(Money.of("1","EUR"))); bad(() -> a.multiply(null));
        System.out.println("OK");
    }
}
