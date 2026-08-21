from dataclasses import dataclass
@dataclass(frozen=True)
class FlagConfig:
 name:str;salt:str;basis_points:int
