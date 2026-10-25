import java.util.*;
public class Service {
static java.math.BigDecimal total(java.util.List<java.math.BigDecimal> amounts){var sum=java.math.BigDecimal.ZERO;for(var a:amounts)sum=sum.add(a.setScale(2,java.math.RoundingMode.HALF_UP));return sum.setScale(2,java.math.RoundingMode.HALF_UP);}
}
