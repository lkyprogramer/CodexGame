import java.util.*;
public final class SqlSplitter{
 public List<String>split(String sql){if(sql==null)throw new IllegalArgumentException("null sql");List<String>out=new ArrayList<>();StringBuilder current=new StringBuilder();String state="code";
  for(int i=0;i<sql.length();i++){char c=sql.charAt(i),n=i+1<sql.length()?sql.charAt(i+1):'\0';
   if(state.equals("single")){current.append(c);if(c=='\''&&n=='\''){current.append(n);i++;}else if(c=='\'')state="code";continue;}
   if(state.equals("double")){current.append(c);if(c=='"'&&n=='"'){current.append(n);i++;}else if(c=='"')state="code";continue;}
   if(state.equals("line")){current.append(c);if(c=='\n')state="code";continue;}
   if(state.equals("block")){current.append(c);if(c=='*'&&n=='/'){current.append(n);i++;state="code";}continue;}
   if(c=='\''){state="single";current.append(c);}else if(c=='"'){state="double";current.append(c);}else if(c=='-'&&n=='-'){state="line";current.append(c).append(n);i++;}else if(c=='/'&&n=='*'){state="block";current.append(c).append(n);i++;}else if(c==';'){String s=current.toString().trim();if(!s.isEmpty())out.add(s);current.setLength(0);}else current.append(c);
  }
  if(state.equals("single")||state.equals("double")||state.equals("block"))throw new IllegalArgumentException("unterminated construct");String tail=current.toString().trim();if(!tail.isEmpty())out.add(tail);return List.copyOf(out);
 }
}
