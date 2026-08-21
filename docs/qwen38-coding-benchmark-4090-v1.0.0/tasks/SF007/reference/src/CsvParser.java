import java.util.ArrayList;
import java.util.List;

public final class CsvParser {
    private enum State { START, UNQUOTED, QUOTED, AFTER_QUOTE }

    public static List<List<String>> parse(String input) {
        if (input == null) {
            throw new IllegalArgumentException("input is null");
        }
        List<List<String>> rows = new ArrayList<>();
        if (input.isEmpty()) {
            return rows;
        }
        List<String> row = new ArrayList<>();
        StringBuilder field = new StringBuilder();
        State state = State.START;
        boolean justEndedRecord = false;

        for (int i = 0; i < input.length(); i++) {
            char c = input.charAt(i);
            justEndedRecord = false;

            if (state == State.QUOTED) {
                if (c == '"') {
                    state = State.AFTER_QUOTE;
                } else {
                    field.append(c);
                }
                continue;
            }

            if (state == State.AFTER_QUOTE) {
                if (c == '"') {
                    field.append('"');
                    state = State.QUOTED;
                } else if (c == ',') {
                    row.add(field.toString());
                    field.setLength(0);
                    state = State.START;
                } else if (c == '\n' || c == '\r') {
                    if (c == '\r') {
                        if (i + 1 >= input.length() || input.charAt(i + 1) != '\n') {
                            throw new IllegalArgumentException("bare CR");
                        }
                        i++;
                    }
                    row.add(field.toString());
                    field.setLength(0);
                    rows.add(row);
                    row = new ArrayList<>();
                    state = State.START;
                    justEndedRecord = true;
                } else {
                    throw new IllegalArgumentException("characters after closing quote");
                }
                continue;
            }

            if (c == '"') {
                if (state != State.START) {
                    throw new IllegalArgumentException("quote in unquoted field");
                }
                state = State.QUOTED;
            } else if (c == ',') {
                row.add(field.toString());
                field.setLength(0);
                state = State.START;
            } else if (c == '\n' || c == '\r') {
                if (c == '\r') {
                    if (i + 1 >= input.length() || input.charAt(i + 1) != '\n') {
                        throw new IllegalArgumentException("bare CR");
                    }
                    i++;
                }
                row.add(field.toString());
                field.setLength(0);
                rows.add(row);
                row = new ArrayList<>();
                state = State.START;
                justEndedRecord = true;
            } else {
                field.append(c);
                state = State.UNQUOTED;
            }
        }

        if (state == State.QUOTED) {
            throw new IllegalArgumentException("unterminated quote");
        }
        if (!justEndedRecord || !row.isEmpty() || field.length() > 0 || state != State.START) {
            row.add(field.toString());
            rows.add(row);
        }
        return rows;
    }
}
