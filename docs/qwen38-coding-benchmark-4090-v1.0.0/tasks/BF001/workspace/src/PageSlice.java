import java.util.List;
public final class PageSlice {
    public static <T> List<T> page(List<T> items, int pageNumber, int pageSize) {
        int from = pageNumber * pageSize;
        int to = Math.min(items.size(), from + pageSize);
        return items.subList(from, to);
    }
}
