import java.util.*;
public final class CsvParser {
    public static List<List<String>> parse(String input) {
        List<List<String>> rows = new ArrayList<>();
        for (String line : input.split("\n")) rows.add(Arrays.asList(line.split(",")));
        return rows;
    }
}
