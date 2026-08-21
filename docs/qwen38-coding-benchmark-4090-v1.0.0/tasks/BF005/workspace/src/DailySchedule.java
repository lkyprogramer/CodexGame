import java.time.*;
public final class DailySchedule {
    public static ZonedDateTime nextAfter(ZonedDateTime after, LocalTime time, ZoneId zone){
        ZonedDateTime candidate=after.withZoneSameInstant(zone).with(time);
        if(!candidate.isAfter(after))candidate=candidate.plusDays(1);
        return candidate;
    }
}
