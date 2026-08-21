import java.util.Objects;
public final class UserId implements Comparable<UserId> {
    private final String value;
    public UserId(String value){this.value=value.trim();}
    public boolean equals(Object o){return o instanceof UserId u && value.equalsIgnoreCase(u.value);}
    public int hashCode(){return Objects.hash(value);}
    public int compareTo(UserId o){return value.compareTo(o.value);}
    public String toString(){return value;}
}
