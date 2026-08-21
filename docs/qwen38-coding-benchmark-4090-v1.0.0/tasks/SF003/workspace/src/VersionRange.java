public final class VersionRange {
    private final String expression;
    public VersionRange(String expression) { this.expression = expression; }
    public boolean contains(String version) {
        if ("*".equals(expression)) return true;
        return version.compareTo(expression.replace("=", "")) >= 0;
    }
}
