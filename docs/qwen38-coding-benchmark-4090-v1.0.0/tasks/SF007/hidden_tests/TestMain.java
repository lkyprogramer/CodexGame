import java.util.List;
import java.util.Objects;

public class TestMain {
    static void eq(Object actual, Object expected) {
        if (!Objects.equals(actual, expected)) {
            throw new AssertionError(actual + " != " + expected);
        }
    }
    static void bad(String input) {
        try {
            CsvParser.parse(input);
            throw new AssertionError("expected bad input: " + input);
        } catch (IllegalArgumentException expected) {
        }
    }
    public static void main(String[] args) {
        eq(CsvParser.parse(""), List.of());
        eq(CsvParser.parse("a,b\n1,2\n"), List.of(List.of("a", "b"), List.of("1", "2")));
        eq(CsvParser.parse("a,,c"), List.of(List.of("a", "", "c")));
        eq(CsvParser.parse("\"a,b\",\"x\"\"y\""), List.of(List.of("a,b", "x\"y")));
        eq(CsvParser.parse("\"a\nb\",c\r\nd,e"), List.of(List.of("a\nb", "c"), List.of("d", "e")));
        eq(CsvParser.parse(",\n"), List.of(List.of("", "")));
        bad("\"abc");
        bad("ab\"c,d");
        bad("\"a\"x,b");
        bad("a\rb");
        System.out.println("OK");
    }
}
