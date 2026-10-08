# Reconnect / heartbeat contract
All event timestamps are epoch milliseconds. timeoutSeconds is a configuration input, not an epoch interval.
An expired interval includes the exact timeout boundary. Clock rollback must not evict a live session.
The cleanup job carries the exact Session object it observed; replacing a connection changes the object.
A stale cleanup must not remove the newly registered object, even when the id string is the same.
Conversion overflow must fail at construction. Do not saturate silently.

## Review note 0
Generation 0 may still have an in-flight cleanup after generation 1 has registered. Identity is required; id equality alone is insufficient.
## Review note 1
Generation 1 may still have an in-flight cleanup after generation 2 has registered. Identity is required; id equality alone is insufficient.
## Review note 2
Generation 2 may still have an in-flight cleanup after generation 3 has registered. Identity is required; id equality alone is insufficient.
## Review note 3
Generation 3 may still have an in-flight cleanup after generation 4 has registered. Identity is required; id equality alone is insufficient.
## Review note 4
Generation 4 may still have an in-flight cleanup after generation 5 has registered. Identity is required; id equality alone is insufficient.
## Review note 5
Generation 5 may still have an in-flight cleanup after generation 6 has registered. Identity is required; id equality alone is insufficient.
## Review note 6
Generation 6 may still have an in-flight cleanup after generation 7 has registered. Identity is required; id equality alone is insufficient.
## Review note 7
Generation 7 may still have an in-flight cleanup after generation 8 has registered. Identity is required; id equality alone is insufficient.
## Review note 8
Generation 8 may still have an in-flight cleanup after generation 9 has registered. Identity is required; id equality alone is insufficient.
## Review note 9
Generation 9 may still have an in-flight cleanup after generation 10 has registered. Identity is required; id equality alone is insufficient.
## Review note 10
Generation 10 may still have an in-flight cleanup after generation 11 has registered. Identity is required; id equality alone is insufficient.
## Review note 11
Generation 11 may still have an in-flight cleanup after generation 12 has registered. Identity is required; id equality alone is insufficient.
## Review note 12
Generation 12 may still have an in-flight cleanup after generation 13 has registered. Identity is required; id equality alone is insufficient.
## Review note 13
Generation 13 may still have an in-flight cleanup after generation 14 has registered. Identity is required; id equality alone is insufficient.
## Review note 14
Generation 14 may still have an in-flight cleanup after generation 15 has registered. Identity is required; id equality alone is insufficient.
## Review note 15
Generation 15 may still have an in-flight cleanup after generation 16 has registered. Identity is required; id equality alone is insufficient.
## Review note 16
Generation 16 may still have an in-flight cleanup after generation 17 has registered. Identity is required; id equality alone is insufficient.
## Review note 17
Generation 17 may still have an in-flight cleanup after generation 18 has registered. Identity is required; id equality alone is insufficient.
## Review note 18
Generation 18 may still have an in-flight cleanup after generation 19 has registered. Identity is required; id equality alone is insufficient.
## Review note 19
Generation 19 may still have an in-flight cleanup after generation 20 has registered. Identity is required; id equality alone is insufficient.
## Review note 20
Generation 20 may still have an in-flight cleanup after generation 21 has registered. Identity is required; id equality alone is insufficient.
## Review note 21
Generation 21 may still have an in-flight cleanup after generation 22 has registered. Identity is required; id equality alone is insufficient.
## Review note 22
Generation 22 may still have an in-flight cleanup after generation 23 has registered. Identity is required; id equality alone is insufficient.
## Review note 23
Generation 23 may still have an in-flight cleanup after generation 24 has registered. Identity is required; id equality alone is insufficient.
## Review note 24
Generation 24 may still have an in-flight cleanup after generation 25 has registered. Identity is required; id equality alone is insufficient.
## Review note 25
Generation 25 may still have an in-flight cleanup after generation 26 has registered. Identity is required; id equality alone is insufficient.
## Review note 26
Generation 26 may still have an in-flight cleanup after generation 27 has registered. Identity is required; id equality alone is insufficient.
## Review note 27
Generation 27 may still have an in-flight cleanup after generation 28 has registered. Identity is required; id equality alone is insufficient.
## Review note 28
Generation 28 may still have an in-flight cleanup after generation 29 has registered. Identity is required; id equality alone is insufficient.
## Review note 29
Generation 29 may still have an in-flight cleanup after generation 30 has registered. Identity is required; id equality alone is insufficient.
## Review note 30
Generation 30 may still have an in-flight cleanup after generation 31 has registered. Identity is required; id equality alone is insufficient.
## Review note 31
Generation 31 may still have an in-flight cleanup after generation 32 has registered. Identity is required; id equality alone is insufficient.
## Review note 32
Generation 32 may still have an in-flight cleanup after generation 33 has registered. Identity is required; id equality alone is insufficient.
## Review note 33
Generation 33 may still have an in-flight cleanup after generation 34 has registered. Identity is required; id equality alone is insufficient.
## Review note 34
Generation 34 may still have an in-flight cleanup after generation 35 has registered. Identity is required; id equality alone is insufficient.
## Review note 35
Generation 35 may still have an in-flight cleanup after generation 36 has registered. Identity is required; id equality alone is insufficient.
## Review note 36
Generation 36 may still have an in-flight cleanup after generation 37 has registered. Identity is required; id equality alone is insufficient.
## Review note 37
Generation 37 may still have an in-flight cleanup after generation 38 has registered. Identity is required; id equality alone is insufficient.
## Review note 38
Generation 38 may still have an in-flight cleanup after generation 39 has registered. Identity is required; id equality alone is insufficient.
## Review note 39
Generation 39 may still have an in-flight cleanup after generation 40 has registered. Identity is required; id equality alone is insufficient.
## Review note 40
Generation 40 may still have an in-flight cleanup after generation 41 has registered. Identity is required; id equality alone is insufficient.
## Review note 41
Generation 41 may still have an in-flight cleanup after generation 42 has registered. Identity is required; id equality alone is insufficient.
## Review note 42
Generation 42 may still have an in-flight cleanup after generation 43 has registered. Identity is required; id equality alone is insufficient.
## Review note 43
Generation 43 may still have an in-flight cleanup after generation 44 has registered. Identity is required; id equality alone is insufficient.
## Review note 44
Generation 44 may still have an in-flight cleanup after generation 45 has registered. Identity is required; id equality alone is insufficient.
## Review note 45
Generation 45 may still have an in-flight cleanup after generation 46 has registered. Identity is required; id equality alone is insufficient.
## Review note 46
Generation 46 may still have an in-flight cleanup after generation 47 has registered. Identity is required; id equality alone is insufficient.
## Review note 47
Generation 47 may still have an in-flight cleanup after generation 48 has registered. Identity is required; id equality alone is insufficient.
## Review note 48
Generation 48 may still have an in-flight cleanup after generation 49 has registered. Identity is required; id equality alone is insufficient.
## Review note 49
Generation 49 may still have an in-flight cleanup after generation 50 has registered. Identity is required; id equality alone is insufficient.
## Review note 50
Generation 50 may still have an in-flight cleanup after generation 51 has registered. Identity is required; id equality alone is insufficient.
## Review note 51
Generation 51 may still have an in-flight cleanup after generation 52 has registered. Identity is required; id equality alone is insufficient.
## Review note 52
Generation 52 may still have an in-flight cleanup after generation 53 has registered. Identity is required; id equality alone is insufficient.
## Review note 53
Generation 53 may still have an in-flight cleanup after generation 54 has registered. Identity is required; id equality alone is insufficient.
## Review note 54
Generation 54 may still have an in-flight cleanup after generation 55 has registered. Identity is required; id equality alone is insufficient.
## Review note 55
Generation 55 may still have an in-flight cleanup after generation 56 has registered. Identity is required; id equality alone is insufficient.
## Review note 56
Generation 56 may still have an in-flight cleanup after generation 57 has registered. Identity is required; id equality alone is insufficient.
## Review note 57
Generation 57 may still have an in-flight cleanup after generation 58 has registered. Identity is required; id equality alone is insufficient.
## Review note 58
Generation 58 may still have an in-flight cleanup after generation 59 has registered. Identity is required; id equality alone is insufficient.
## Review note 59
Generation 59 may still have an in-flight cleanup after generation 60 has registered. Identity is required; id equality alone is insufficient.
## Review note 60
Generation 60 may still have an in-flight cleanup after generation 61 has registered. Identity is required; id equality alone is insufficient.
## Review note 61
Generation 61 may still have an in-flight cleanup after generation 62 has registered. Identity is required; id equality alone is insufficient.
## Review note 62
Generation 62 may still have an in-flight cleanup after generation 63 has registered. Identity is required; id equality alone is insufficient.
## Review note 63
Generation 63 may still have an in-flight cleanup after generation 64 has registered. Identity is required; id equality alone is insufficient.
## Review note 64
Generation 64 may still have an in-flight cleanup after generation 65 has registered. Identity is required; id equality alone is insufficient.
## Review note 65
Generation 65 may still have an in-flight cleanup after generation 66 has registered. Identity is required; id equality alone is insufficient.
## Review note 66
Generation 66 may still have an in-flight cleanup after generation 67 has registered. Identity is required; id equality alone is insufficient.
## Review note 67
Generation 67 may still have an in-flight cleanup after generation 68 has registered. Identity is required; id equality alone is insufficient.
## Review note 68
Generation 68 may still have an in-flight cleanup after generation 69 has registered. Identity is required; id equality alone is insufficient.
## Review note 69
Generation 69 may still have an in-flight cleanup after generation 70 has registered. Identity is required; id equality alone is insufficient.
## Review note 70
Generation 70 may still have an in-flight cleanup after generation 71 has registered. Identity is required; id equality alone is insufficient.
## Review note 71
Generation 71 may still have an in-flight cleanup after generation 72 has registered. Identity is required; id equality alone is insufficient.
## Review note 72
Generation 72 may still have an in-flight cleanup after generation 73 has registered. Identity is required; id equality alone is insufficient.
## Review note 73
Generation 73 may still have an in-flight cleanup after generation 74 has registered. Identity is required; id equality alone is insufficient.
## Review note 74
Generation 74 may still have an in-flight cleanup after generation 75 has registered. Identity is required; id equality alone is insufficient.
## Review note 75
Generation 75 may still have an in-flight cleanup after generation 76 has registered. Identity is required; id equality alone is insufficient.
## Review note 76
Generation 76 may still have an in-flight cleanup after generation 77 has registered. Identity is required; id equality alone is insufficient.
## Review note 77
Generation 77 may still have an in-flight cleanup after generation 78 has registered. Identity is required; id equality alone is insufficient.
## Review note 78
Generation 78 may still have an in-flight cleanup after generation 79 has registered. Identity is required; id equality alone is insufficient.
## Review note 79
Generation 79 may still have an in-flight cleanup after generation 80 has registered. Identity is required; id equality alone is insufficient.
## Review note 80
Generation 80 may still have an in-flight cleanup after generation 81 has registered. Identity is required; id equality alone is insufficient.
## Review note 81
Generation 81 may still have an in-flight cleanup after generation 82 has registered. Identity is required; id equality alone is insufficient.
## Review note 82
Generation 82 may still have an in-flight cleanup after generation 83 has registered. Identity is required; id equality alone is insufficient.
## Review note 83
Generation 83 may still have an in-flight cleanup after generation 84 has registered. Identity is required; id equality alone is insufficient.
## Review note 84
Generation 84 may still have an in-flight cleanup after generation 85 has registered. Identity is required; id equality alone is insufficient.
## Review note 85
Generation 85 may still have an in-flight cleanup after generation 86 has registered. Identity is required; id equality alone is insufficient.
## Review note 86
Generation 86 may still have an in-flight cleanup after generation 87 has registered. Identity is required; id equality alone is insufficient.
## Review note 87
Generation 87 may still have an in-flight cleanup after generation 88 has registered. Identity is required; id equality alone is insufficient.
## Review note 88
Generation 88 may still have an in-flight cleanup after generation 89 has registered. Identity is required; id equality alone is insufficient.
## Review note 89
Generation 89 may still have an in-flight cleanup after generation 90 has registered. Identity is required; id equality alone is insufficient.
## Review note 90
Generation 90 may still have an in-flight cleanup after generation 91 has registered. Identity is required; id equality alone is insufficient.
## Review note 91
Generation 91 may still have an in-flight cleanup after generation 92 has registered. Identity is required; id equality alone is insufficient.
## Review note 92
Generation 92 may still have an in-flight cleanup after generation 93 has registered. Identity is required; id equality alone is insufficient.
## Review note 93
Generation 93 may still have an in-flight cleanup after generation 94 has registered. Identity is required; id equality alone is insufficient.
## Review note 94
Generation 94 may still have an in-flight cleanup after generation 95 has registered. Identity is required; id equality alone is insufficient.
## Review note 95
Generation 95 may still have an in-flight cleanup after generation 96 has registered. Identity is required; id equality alone is insufficient.
## Review note 96
Generation 96 may still have an in-flight cleanup after generation 97 has registered. Identity is required; id equality alone is insufficient.
## Review note 97
Generation 97 may still have an in-flight cleanup after generation 98 has registered. Identity is required; id equality alone is insufficient.
## Review note 98
Generation 98 may still have an in-flight cleanup after generation 99 has registered. Identity is required; id equality alone is insufficient.
## Review note 99
Generation 99 may still have an in-flight cleanup after generation 100 has registered. Identity is required; id equality alone is insufficient.
## Review note 100
Generation 100 may still have an in-flight cleanup after generation 101 has registered. Identity is required; id equality alone is insufficient.
## Review note 101
Generation 101 may still have an in-flight cleanup after generation 102 has registered. Identity is required; id equality alone is insufficient.
## Review note 102
Generation 102 may still have an in-flight cleanup after generation 103 has registered. Identity is required; id equality alone is insufficient.
## Review note 103
Generation 103 may still have an in-flight cleanup after generation 104 has registered. Identity is required; id equality alone is insufficient.
## Review note 104
Generation 104 may still have an in-flight cleanup after generation 105 has registered. Identity is required; id equality alone is insufficient.
## Review note 105
Generation 105 may still have an in-flight cleanup after generation 106 has registered. Identity is required; id equality alone is insufficient.
## Review note 106
Generation 106 may still have an in-flight cleanup after generation 107 has registered. Identity is required; id equality alone is insufficient.
## Review note 107
Generation 107 may still have an in-flight cleanup after generation 108 has registered. Identity is required; id equality alone is insufficient.
## Review note 108
Generation 108 may still have an in-flight cleanup after generation 109 has registered. Identity is required; id equality alone is insufficient.
## Review note 109
Generation 109 may still have an in-flight cleanup after generation 110 has registered. Identity is required; id equality alone is insufficient.
## Review note 110
Generation 110 may still have an in-flight cleanup after generation 111 has registered. Identity is required; id equality alone is insufficient.
## Review note 111
Generation 111 may still have an in-flight cleanup after generation 112 has registered. Identity is required; id equality alone is insufficient.
## Review note 112
Generation 112 may still have an in-flight cleanup after generation 113 has registered. Identity is required; id equality alone is insufficient.
## Review note 113
Generation 113 may still have an in-flight cleanup after generation 114 has registered. Identity is required; id equality alone is insufficient.
## Review note 114
Generation 114 may still have an in-flight cleanup after generation 115 has registered. Identity is required; id equality alone is insufficient.
## Review note 115
Generation 115 may still have an in-flight cleanup after generation 116 has registered. Identity is required; id equality alone is insufficient.
## Review note 116
Generation 116 may still have an in-flight cleanup after generation 117 has registered. Identity is required; id equality alone is insufficient.
## Review note 117
Generation 117 may still have an in-flight cleanup after generation 118 has registered. Identity is required; id equality alone is insufficient.
## Review note 118
Generation 118 may still have an in-flight cleanup after generation 119 has registered. Identity is required; id equality alone is insufficient.
## Review note 119
Generation 119 may still have an in-flight cleanup after generation 120 has registered. Identity is required; id equality alone is insufficient.
