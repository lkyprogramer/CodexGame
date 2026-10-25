import java.util.*;
public class Service {
interface Handle extends AutoCloseable {String read() throws Exception;}static String load(Handle h)throws Exception{try{return h.read();}finally{h.close();}}
}
