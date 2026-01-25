from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, Optional
from dataclasses import dataclass

class RiskLevel(Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

@dataclass
class RuleResult:
    passed: bool  # Renamed from 'status' to be more explicit
    details: str
    compliance_mapping: str
    raw_data: Optional[Dict[str, Any]] = None
    remediation: Optional[str] = None
    severity: Optional[str] = None

    @property
    def status(self):
        return self.passed

class BaseRule(ABC):
    """
    Abstract base class for all compliance rules.
    Now supports Risk Levels and direct Object interrogation.
    """
    id: str = "GENERIC"
    title: str = "Generic Rule"
    risk_level: RiskLevel = RiskLevel.LOW
    compliance_standard: str = "General"

    @property
    def status(self):
        return self.passed

    @abstractmethod
    def evaluate(self, context: Any) -> RuleResult:
        """
        Alias for check() to maintain compatibility with logic.py
        """
        pass
        
    def check(self, context: Any) -> RuleResult:
         return self.evaluate(context)


# from abc import ABC, abstractmethod
# from typing import Any, Dict, Optional
# from dataclasses import dataclass

# @dataclass
# class RuleResult:
#     status: bool
#     details: str
#     compliance_mapping: str

# class BaseRule(ABC):
#     """
#     Abstract base class for all compliance rules.
#     """
#     compliance_standard: str = "General"

#     @abstractmethod
#     def evaluate(self, data: Any) -> RuleResult:
#         """
#         Input: Raw data from the provider (GitHub JSON).
#         Output: RuleResult object
#         """
#         pass

# # maintain backward compatibility alias if needed, but we will update the usage
# AuditRule = BaseRule