import java.util.*;
public class ServiceTest { static void eq(Object actual,Object expected){if(!Objects.equals(actual,expected))throw new AssertionError("expected="+expected+" actual="+actual);}static void yes(boolean value){if(!value)throw new AssertionError("contract violated");}public static void main(String[]args)throws Exception{
var s=new Service();try{s.debit(30,true);throw new AssertionError();}catch(IllegalStateException ok){}eq(s.balance,100);eq(s.ledger.size(),0);s.debit(20,false);eq(s.balance,80);eq(s.ledger,List.of(20));
System.out.println("PASS business-transaction-rollback");}}
