from dataclasses import dataclass
@dataclass(frozen=True)
class Spec:
 name:str;factory:object;dependencies:tuple[str,...]
