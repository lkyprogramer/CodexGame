import java.util.*;
public class Service {
static boolean expired(java.time.OffsetDateTime expiry,java.time.OffsetDateTime now){return expiry.toLocalDateTime().isBefore(now.toLocalDateTime());}
}
