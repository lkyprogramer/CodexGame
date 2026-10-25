// Arithmetic smoke corpus only; excluded from business baseline.
// New fixtures, not invented historical benchmark tasks. Values include boundaries.
export const SMOKE_CASES=[
 ['increment','Return n + 1.',[-2,0,8],[-1,1,9]],['double','Return n * 2.',[-3,0,7],[-6,0,14]],
 ['square','Return n squared.',[-4,0,7],[16,0,49]],['absolute','Return absolute n (input excludes Integer.MIN_VALUE).',[-9,0,7],[9,0,7]],
 ['sign','Return -1, 0 or 1 according to the sign of n.',[-9,0,7],[-1,0,1]],
 ['clamp','Clamp n to inclusive range 0..10.',[-3,5,30],[0,5,10]],
 ['even','Return 1 for even n and 0 for odd n.',[-3,0,8],[0,1,1]],
 ['positive','Return 1 if n is strictly positive, otherwise 0.',[-2,0,9],[0,0,1]],
 ['sum','Return sum of all integers from 1 through n; n is 0..100.',[0,1,10],[0,1,55]],
 ['factorial','Return n factorial for n in 0..10.',[0,1,5],[1,1,120]],
 ['digit-sum','Return sum of decimal digits for nonnegative n.',[0,19,123],[0,10,6]],
 ['digits','Return decimal digit count for nonnegative n; zero has one digit.',[0,9,100],[1,1,3]],
 ['last-digit','Return last decimal digit of absolute n (excludes MIN_VALUE).',[-27,0,34],[7,0,4]],
 ['popcount','Return number of set bits in the 32-bit representation of n.',[0,7,-1],[0,3,32]],
 ['ceil-ten','Return ceiling of n/10 for nonnegative n.',[0,10,11],[0,1,2]],
 ['floor-ten','Return mathematical floor of n/10 including negatives.',[-11,0,19],[-2,0,1]],
 ['leap','Return 1 if positive year n is a Gregorian leap year else 0.',[1900,2000,2024],[0,1,1]],
 ['century','Return 1-based century of positive year n.',[1,100,101],[1,1,2]],
 ['reverse','Reverse decimal digits of nonnegative n as an integer.',[0,120,123],[0,21,321]],
 ['fibonacci','Return Fibonacci F(n), F(0)=0 and F(1)=1, for n in 0..20.',[0,1,10],[0,1,55]],
];
const VERIFY='#!/bin/sh\nset -eu\nmkdir -p classes\njavac -d classes Main.java MainTest.java\njava -cp classes MainTest\n';
export function smokeFixtureFiles(c) {
 const [id,task,ins,outs]=c;
 return {'Main.java':'public class Main { public static int calc(int n) { return 0; } }\n',
 'MainTest.java':`public class MainTest { public static void main(String[] args) { int[] in={${ins}}, expected={${outs}}; for(int i=0;i<in.length;i++) if(Main.calc(in[i])!=expected[i]) throw new AssertionError("input="+in[i]+" expected="+expected[i]+" actual="+Main.calc(in[i])); System.out.println("PASS ${id}"); } }\n`,
 'verify.sh':VERIFY,'TASK.md':`${task}\nRead Main.java and MainTest.java, fix only Main.java, then run ./verify.sh. Do not edit tests, task or verify.sh. Tools allowed: read, edit, write, bash. Bash command must be exactly ./verify.sh or bash verify.sh. No network, packages, other commands or external paths.\n`};
}
