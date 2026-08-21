import java.util.List;
public final class PageSlice {
    public static <T> List<T> page(List<T> items, int pageNumber, int pageSize) {
        if (items == null || pageNumber < 1 || pageSize < 1) throw new IllegalArgumentException("invalid pagination");
        long fromLong = (long) (pageNumber - 1) * pageSize;
        if (fromLong >= items.size()) return List.of();
        int from = (int) fromLong;
        int to = (int) Math.min(items.size(), fromLong + pageSize);
        return List.copyOf(items.subList(from, to));
    }
}
