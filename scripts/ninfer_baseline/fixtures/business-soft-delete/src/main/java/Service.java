import java.util.*;
public class Service {
record User(long tenant,String name,boolean deleted){}final java.util.List<User> users=new java.util.ArrayList<>();void create(long tenant,String name){if(users.stream().anyMatch(u->u.name().equals(name)))throw new IllegalStateException("duplicate");users.add(new User(tenant,name,false));}
}
