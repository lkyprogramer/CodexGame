import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.Locale;
import java.util.Objects;

public final class Money {
    private final BigDecimal amount;
    private final String currency;
    private Money(BigDecimal amount, String currency) { this.amount=amount; this.currency=currency; }
    public static Money of(String rawAmount, String rawCurrency) {
        if (rawAmount == null || rawCurrency == null || !rawCurrency.matches("[A-Za-z]{3}")) throw new IllegalArgumentException("invalid money");
        try {
            return new Money(new BigDecimal(rawAmount).setScale(2, RoundingMode.HALF_EVEN), rawCurrency.toUpperCase(Locale.ROOT));
        } catch (NumberFormatException ex) { throw new IllegalArgumentException("invalid amount", ex); }
    }
    private void requireSame(Money other) {
        if (other == null || !currency.equals(other.currency)) throw new IllegalArgumentException("currency mismatch");
    }
    public Money add(Money other) { requireSame(other); return new Money(amount.add(other.amount).setScale(2, RoundingMode.HALF_EVEN), currency); }
    public Money subtract(Money other) { requireSame(other); return new Money(amount.subtract(other.amount).setScale(2, RoundingMode.HALF_EVEN), currency); }
    public Money multiply(BigDecimal factor) {
        if (factor == null) throw new IllegalArgumentException("factor is null");
        return new Money(amount.multiply(factor).setScale(2, RoundingMode.HALF_EVEN), currency);
    }
    public BigDecimal amount(){ return amount; }
    public String currency(){ return currency; }
    @Override public boolean equals(Object o){ return o instanceof Money m && amount.equals(m.amount) && currency.equals(m.currency); }
    @Override public int hashCode(){ return Objects.hash(amount,currency); }
    @Override public String toString(){ return currency+" "+amount.toPlainString(); }
}
