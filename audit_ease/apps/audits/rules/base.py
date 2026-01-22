from abc import ABC, abstractmethod
from typing import Any, Dict, Tuple

class AuditRule(ABC):
    """
    Abstract base class for all compliance rules.
    """

    @abstractmethod
    def evaluate(self, data: Any) -> Tuple[bool, Dict]:
        """
        Input: Raw data from the provider (GitHub JSON).
        Output: Tuple (passed: bool, details: dict)
        """
        pass