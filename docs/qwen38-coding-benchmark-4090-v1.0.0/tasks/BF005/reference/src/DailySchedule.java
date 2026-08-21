import java.time.*;
import java.time.zone.ZoneOffsetTransition;
import java.time.zone.ZoneRules;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
public final class DailySchedule {
    public static ZonedDateTime nextAfter(ZonedDateTime after, LocalTime time, ZoneId zone){
        if(after==null||time==null||zone==null)throw new IllegalArgumentException("null argument");
        ZonedDateTime localAfter=after.withZoneSameInstant(zone);
        LocalDate date=localAfter.toLocalDate();
        for(int day=0;day<370;day++,date=date.plusDays(1)){
            LocalDateTime ldt=LocalDateTime.of(date,time);
            ZoneRules rules=zone.getRules();
            List<ZoneOffset> offsets=rules.getValidOffsets(ldt);
            List<ZonedDateTime> candidates=new ArrayList<>();
            if(offsets.isEmpty()){
                ZoneOffsetTransition transition=rules.getTransition(ldt);
                candidates.add(transition.getDateTimeAfter().atZone(zone));
            }else{
                for(ZoneOffset offset:offsets)candidates.add(ZonedDateTime.ofLocal(ldt,zone,offset));
            }
            candidates.sort(Comparator.comparing(ZonedDateTime::toInstant));
            for(ZonedDateTime candidate:candidates)if(candidate.toInstant().isAfter(after.toInstant()))return candidate;
        }
        throw new IllegalStateException("no occurrence found");
    }
}
