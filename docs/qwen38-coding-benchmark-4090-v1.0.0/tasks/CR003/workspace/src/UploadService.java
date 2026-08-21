import java.io.*;import java.nio.file.*;
public final class UploadService{
 private final Path root=Path.of("/srv/uploads");
 public Path save(String filename,InputStream input)throws IOException{
  if(filename.contains(".."))throw new IllegalArgumentException();
  String ext=filename.substring(filename.lastIndexOf('.')+1);
  if(!ext.equals("jpg")&&!ext.equals("png"))throw new IllegalArgumentException();
  Path target=root.resolve(filename);
  Files.createDirectories(target.getParent());
  Files.copy(input,target,StandardCopyOption.REPLACE_EXISTING);
  return target;
 }
}
