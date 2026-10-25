import java.util.*;
public class Service {
int stock=5; synchronized boolean reserve(int quantity){if(quantity>stock)return false;stock-=quantity;return true;}
}
