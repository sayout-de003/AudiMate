from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from dataclasses import dataclass

@dataclass
class RuleResult:
    status: bool
    details: str
    compliance_mapping: str

class BaseRule(ABC):
    """
    Abstract base class for all compliance rules.
    """
    compliance_standard: str = "General"

    @abstractmethod
    def evaluate(self, data: Any) -> RuleResult:
        """
        Input: Raw data from the provider (GitHub JSON).
        Output: RuleResult object
        """
        pass

# maintain backward compatibility alias if needed, but we will update the usage
AuditRule = BaseRule