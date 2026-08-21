public class TestMain {
    static void check(boolean v, String m) { if (!v) throw new AssertionError(m); }
    static void bad(Runnable r) { try { r.run(); throw new AssertionError("expected IAE"); } catch (IllegalArgumentException e) { } }
    public static void main(String[] args) {
        check(new VersionRange("*").contains("0.0.1-alpha"), "wildcard");
        VersionRange stable = new VersionRange(">=1.2.3 <2.0.0");
        check(stable.contains("1.2.3"), "lower inclusive");
        check(stable.contains("1.9.9"), "middle");
        check(!stable.contains("2.0.0"), "upper exclusive");
        check(!stable.contains("1.2.3-alpha"), "prerelease below release");
        check(new VersionRange(">=1.2.3-alpha.2 <1.2.3").contains("1.2.3-alpha.10"), "numeric prerelease");
        check(new VersionRange("1.0.0-beta").contains("1.0.0-beta"), "bare exact");
        check(!new VersionRange("=1.0.0-beta").contains("1.0.0"), "release differs");
        bad(() -> new VersionRange(""));
        bad(() -> new VersionRange(">="));
        bad(() -> new VersionRange("1.2"));
        bad(() -> new VersionRange("01.2.3"));
        bad(() -> new VersionRange("1.2.3-01"));
        bad(() -> stable.contains("v1.2.3"));
        System.out.println("OK");
    }
}
