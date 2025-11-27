from dataclasses import dataclass

@dataclass
class FederalResult:
    totalFederalTax: float
    marginalBracket: float
    longTermCapitalGainsTax: float = 0.0
