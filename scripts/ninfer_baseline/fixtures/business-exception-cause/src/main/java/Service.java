import java.util.*;
public class Service {
interface Repository { String load(String id); } static String load(Repository repo,String id){try{return repo.load(id);}catch(RuntimeException e){throw new IllegalStateException("order "+id+" failed");}}
}
