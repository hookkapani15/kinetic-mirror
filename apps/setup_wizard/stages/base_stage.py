#!/usr/bin/env python3
"""
Stage Base Class - Common interface for all diagnostic stages.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class StageStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class CheckResult:
    """Result of a single check within a stage."""
    name: str
    passed: bool
    message: str
    fix_instructions: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StageResult:
    """Result of an entire stage."""
    stage_name: str
    status: StageStatus
    checks: List[CheckResult] = field(default_factory=list)
    
    @property
    def passed(self) -> bool:
        return self.status == StageStatus.PASSED
    
    @property
    def failed_checks(self) -> List[CheckResult]:
        return [c for c in self.checks if not c.passed]


class BaseStage(ABC):
    """Base class for all diagnostic stages."""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.status = StageStatus.PENDING
        self.result: Optional[StageResult] = None
    
    @abstractmethod
    def run(self, callback=None) -> StageResult:
        """
        Run all checks in this stage.
        
        Args:
            callback: Optional function(check_name, passed, message) for live updates
            
        Returns:
            StageResult with all check results
        """
        pass
    
    def _make_result(self, checks: List[CheckResult]) -> StageResult:
        """Create a StageResult from a list of checks."""
        all_passed = all(c.passed for c in checks)
        self.status = StageStatus.PASSED if all_passed else StageStatus.FAILED
        self.result = StageResult(
            stage_name=self.name,
            status=self.status,
            checks=checks
        )
        return self.result
