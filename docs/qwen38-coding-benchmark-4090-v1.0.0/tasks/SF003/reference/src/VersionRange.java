import java.util.ArrayList;
import java.util.List;

public final class VersionRange {
    private record Constraint(String op, SemVer version) { }
    private final List<Constraint> constraints;

    public VersionRange(String expression) {
        if (expression == null || expression.isBlank()) throw new IllegalArgumentException("empty range");
        constraints = new ArrayList<>();
        if (expression.trim().equals("*")) return;
        for (String token : expression.trim().split("\\s+")) {
            String op;
            String raw;
            if (token.startsWith(">=") || token.startsWith("<=") ) { op = token.substring(0, 2); raw = token.substring(2); }
            else if (token.startsWith(">") || token.startsWith("<") || token.startsWith("=")) { op = token.substring(0, 1); raw = token.substring(1); }
            else { op = "="; raw = token; }
            if (raw.isEmpty()) throw new IllegalArgumentException("missing version");
            constraints.add(new Constraint(op, SemVer.parse(raw)));
        }
    }

    public boolean contains(String version) {
        SemVer actual = SemVer.parse(version);
        for (Constraint c : constraints) {
            int cmp = actual.compareTo(c.version());
            boolean ok = switch (c.op()) {
                case ">=" -> cmp >= 0;
                case ">" -> cmp > 0;
                case "<=" -> cmp <= 0;
                case "<" -> cmp < 0;
                case "=" -> cmp == 0;
                default -> false;
            };
            if (!ok) return false;
        }
        return true;
    }

    private record SemVer(int major, int minor, int patch, List<String> pre) implements Comparable<SemVer> {
        static SemVer parse(String raw) {
            if (raw == null || raw.isBlank() || raw.contains("+")) throw new IllegalArgumentException("invalid version");
            String[] split = raw.split("-", -1);
            if (split.length > 2 || (split.length == 2 && split[1].isEmpty())) throw new IllegalArgumentException("invalid prerelease");
            String[] core = split[0].split("\\.", -1);
            if (core.length != 3) throw new IllegalArgumentException("version must have three parts");
            int[] values = new int[3];
            for (int i = 0; i < 3; i++) {
                if (!core[i].matches("0|[1-9]\\d*")) throw new IllegalArgumentException("invalid number");
                try { values[i] = Integer.parseInt(core[i]); }
                catch (NumberFormatException e) { throw new IllegalArgumentException("number overflow", e); }
            }
            List<String> pre = List.of();
            if (split.length == 2) {
                String[] ids = split[1].split("\\.", -1);
                for (String id : ids) {
                    if (!id.matches("[0-9A-Za-z-]+") || (id.matches("\\d+") && id.length() > 1 && id.startsWith("0"))) {
                        throw new IllegalArgumentException("invalid prerelease identifier");
                    }
                }
                pre = List.of(ids);
            }
            return new SemVer(values[0], values[1], values[2], pre);
        }

        @Override public int compareTo(SemVer other) {
            int cmp = Integer.compare(major, other.major);
            if (cmp == 0) cmp = Integer.compare(minor, other.minor);
            if (cmp == 0) cmp = Integer.compare(patch, other.patch);
            if (cmp != 0) return cmp;
            if (pre.isEmpty() && other.pre.isEmpty()) return 0;
            if (pre.isEmpty()) return 1;
            if (other.pre.isEmpty()) return -1;
            for (int i = 0; i < Math.min(pre.size(), other.pre.size()); i++) {
                String a = pre.get(i), b = other.pre.get(i);
                boolean an = a.matches("\\d+"), bn = b.matches("\\d+");
                if (an && bn) cmp = Integer.compare(Integer.parseInt(a), Integer.parseInt(b));
                else if (an != bn) cmp = an ? -1 : 1;
                else cmp = a.compareTo(b);
                if (cmp != 0) return cmp;
            }
            return Integer.compare(pre.size(), other.pre.size());
        }
    }
}
