import java.util.*;
public class Service {
int balance=100; final java.util.List<Integer> ledger=new java.util.ArrayList<>(); void debit(int amount,boolean fail) { int old=balance; balance-=amount; try { if(fail)throw new IllegalStateException("database unavailable");ledger.add(amount); }catch(RuntimeException e){throw e;} }
}
