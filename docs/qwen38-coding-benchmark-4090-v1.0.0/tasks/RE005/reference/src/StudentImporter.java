import java.util.*;
public final class StudentImporter{
 private final StudentRepository repo;public StudentImporter(StudentRepository repo){if(repo==null)throw new IllegalArgumentException("null repo");this.repo=repo;}
 public void importAll(List<Student> students){if(students==null)throw new IllegalArgumentException("null batch");List<String>errors=new ArrayList<>();List<Student>normalized=new ArrayList<>();Set<String>ids=new HashSet<>(),emails=new HashSet<>();
  for(int i=0;i<students.size();i++){Student s=students.get(i);int row=i+1;if(s==null){errors.add("row "+row+": student is null");continue;}String id=s.id()==null?"":s.id().trim();String email=s.email()==null?"":s.email().trim().toLowerCase(Locale.ROOT);
   if(id.isEmpty())errors.add("row "+row+": id is empty");if(email.isEmpty())errors.add("row "+row+": email is empty");
   if(!id.isEmpty()&&!ids.add(id))errors.add("row "+row+": duplicate id "+id);if(!email.isEmpty()&&!emails.add(email))errors.add("row "+row+": duplicate email "+email);
   if(!id.isEmpty()&&repo.existsId(id))errors.add("row "+row+": existing id "+id);if(!email.isEmpty()&&repo.existsEmail(email))errors.add("row "+row+": existing email "+email);
   normalized.add(new Student(id,email));
  }
  if(!errors.isEmpty())throw new BatchValidationException(errors);repo.saveAll(List.copyOf(normalized));
 }
}
