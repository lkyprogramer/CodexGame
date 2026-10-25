import java.util.*;
public class Service {
int version=0; String value="initial"; synchronized boolean update(int expected,String next){value=next;if(version!=expected)return false;version++;return true;}
}
