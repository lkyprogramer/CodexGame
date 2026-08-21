import java.math.BigDecimal;
public class Money {
    private BigDecimal amount; private String currency;
    public static Money of(String a,String c){ Money m=new Money();m.amount=new BigDecimal(a);m.currency=c;return m; }
    public Money add(Money o){ return of(amount.add(o.amount).toString(),currency); }
    public BigDecimal amount(){return amount;} public String currency(){return currency;}
}
