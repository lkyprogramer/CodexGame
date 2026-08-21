import java.time.*;
public class TestMain{
    static void check(boolean v,String m){if(!v)throw new AssertionError(m);}
    public static void main(String[]a){
        ZoneId ny=ZoneId.of("America/New_York");
        ZonedDateTime normal=DailySchedule.nextAfter(ZonedDateTime.of(2026,2,1,8,0,0,0,ny),LocalTime.of(9,30),ny);
        check(normal.toLocalDateTime().equals(LocalDateTime.of(2026,2,1,9,30)),"normal same day");
        ZonedDateTime next=DailySchedule.nextAfter(ZonedDateTime.of(2026,2,1,10,0,0,0,ny),LocalTime.of(9,30),ny);
        check(next.toLocalDateTime().equals(LocalDateTime.of(2026,2,2,9,30)),"next day");
        ZonedDateTime spring=DailySchedule.nextAfter(ZonedDateTime.of(2026,3,8,1,0,0,0,ny),LocalTime.of(2,30),ny);
        check(spring.toLocalDateTime().equals(LocalDateTime.of(2026,3,8,3,0)),"gap end: "+spring);
        ZonedDateTime beforeOverlap=ZonedDateTime.ofLocal(LocalDateTime.of(2026,11,1,0,30),ny,ZoneOffset.ofHours(-4));
        ZonedDateTime first=DailySchedule.nextAfter(beforeOverlap,LocalTime.of(1,30),ny);
        check(first.getOffset().equals(ZoneOffset.ofHours(-4)),"first overlap");
        ZonedDateTime between=ZonedDateTime.ofLocal(LocalDateTime.of(2026,11,1,1,45),ny,ZoneOffset.ofHours(-4));
        ZonedDateTime second=DailySchedule.nextAfter(between,LocalTime.of(1,30),ny);
        check(second.toLocalDate().equals(LocalDate.of(2026,11,1))&&second.getOffset().equals(ZoneOffset.ofHours(-5)),"second overlap: "+second);
        try{DailySchedule.nextAfter(null,LocalTime.NOON,ny);throw new AssertionError();}catch(IllegalArgumentException e){}
        System.out.println("OK");
    }
}
