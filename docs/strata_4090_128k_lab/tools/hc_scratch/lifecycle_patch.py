"""Enable existing successful-MTP/state traces without the one-request raw oracle."""
import hashlib

ORACLE = 'std::getenv("STRATA_LAB_ORACLE_DIR")'
LIFE = '(std::getenv("STRATA_LAB_ORACLE_DIR") || std::getenv("STRATA_LAB_HC_LIFECYCLE_TRACE"))'
PROGRAM_SHA256 = '22446e2b4eacbb7465f232f375631120439525328368389a5ac64c94ac02cf9a'


def program(source):
    if hashlib.sha256(source.encode()).hexdigest() != PROGRAM_SHA256 or source.count(ORACLE) != 5:
        raise ValueError('LIFECYCLE_PROGRAM_SOURCE_DRIFT')
    source = source.replace(ORACLE, LIFE)
    # GEN1 is a constraint of the raw oracle only. Lifecycle cancellation uses bounded longer output.
    guard = 'if (' + LIFE + ') {\n                if (max_new != 1)'
    if source.count(guard) != 1:
        raise ValueError('LIFECYCLE_GEN1_GUARD_ANCHOR')
    source = source.replace(guard, 'if (' + ORACLE + ') {\n                if (max_new != 1)', 1)
    anchor = '            cur = ids;'
    if source.count(anchor) != 1: raise ValueError('LIFECYCLE_REQUEST_ANCHOR')
    return source.replace(anchor, anchor + r'''
            if (std::getenv("STRATA_LAB_HC_LIFECYCLE_TRACE"))
                std::fprintf(stderr, "P21_REQUEST {\"input_tokens\":%lld,\"max_new\":%lld}\n",
                             (long long) n, (long long) max_new);
''', 1)


def prefill(source):
    anchor = 'if (' + ORACLE + ')\n            std::fprintf(stderr, "P14_FULL_MTP_BATCH '
    if source.count(anchor) != 1: raise ValueError('LIFECYCLE_MTP_BATCH_ANCHOR')
    return source.replace(anchor, 'if (' + LIFE + ')\n            std::fprintf(stderr, "P14_FULL_MTP_BATCH ', 1)
