import java.util.Locale;
import java.util.Objects;
public final class UserId implements Comparable<UserId> {
    private final String value;
    public UserId(String raw){
        if(raw==null)throw new IllegalArgumentException("null id");
        String normalized=raw.trim().toLowerCase(Locale.ROOT);
        if(normalized.isEmpty())throw new IllegalArgumentException("empty id");
        this.value=normalized;
    }
    @Override public boolean equals(Object o){return this==o || (o instanceof UserId u && value.equals(u.value));}
    @Override public int hashCode(){return value.hashCode();}
    @Override public int compareTo(UserId o){return value.compareTo(Objects.requireNonNull(o).value);}
    @Override public String toString(){return value;}
}
