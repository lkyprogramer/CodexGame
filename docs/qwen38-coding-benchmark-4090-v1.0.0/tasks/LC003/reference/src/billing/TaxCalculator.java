import java.math.*;import java.util.*;
public final class TaxCalculator{private final TaxTable table;public TaxCalculator(TaxTable table){if(table==null)throw new IllegalArgumentException("null table");this.table=table;}
 public long taxCents(List<Line>lines){if(lines==null)throw new IllegalArgumentException("null lines");Map<String,BigDecimal>byCode=new TreeMap<>();for(Line line:lines){if(line==null||line.netAmount()==null||line.taxCode()==null)throw new IllegalArgumentException("invalid line");try{BigDecimal net=new BigDecimal(line.netAmount());if(net.signum()<0)throw new IllegalArgumentException("negative net");byCode.merge(line.taxCode(),net,BigDecimal::add);}catch(NumberFormatException e){throw new IllegalArgumentException("invalid amount",e);}}
  BigDecimal total=BigDecimal.ZERO;for(var e:byCode.entrySet())total=total.add(e.getValue().multiply(table.rate(e.getKey())));return total.setScale(2,RoundingMode.HALF_EVEN).movePointRight(2).longValueExact();
 }
}
