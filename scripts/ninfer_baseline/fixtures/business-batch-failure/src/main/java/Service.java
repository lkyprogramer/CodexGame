import java.util.*;
public class Service {
record Result(java.util.List<String> accepted,java.util.List<String> rejected){}static Result ingest(java.util.List<String> rows){var ok=new java.util.ArrayList<String>();var bad=new java.util.ArrayList<String>();for(String id:rows){try{if(id.startsWith("bad"))throw new IllegalArgumentException();ok.add(id);}catch(IllegalArgumentException e){bad.add(id);break;}}return new Result(ok,bad);}
}
