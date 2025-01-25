# enums.py
from enum import Enum

class PatientPhase(Enum):
    REGISTERED = "registered"
    TRIAGED = "triaged"
    INVESTIGATIONS_PENDING = "investigations_pending"
    TREATMED = "treatment"
    ADMITTED = "admitted"
    DISCHARgED = "discharged"

class InvestigationState(Enum):
    ORDERED = "ordered" # Physician has asked that a test be done
    PENDING = "pending" # The test is in progress
    REPORTED = "reported" # The test result is available

class TriageCategory(Enum):
    RESUSCITATION = 1  # Blue, severely ill
    EMERGENT = 2       # Red, requires rapid intervention
    URGENT = 3         # Yellow, requires urgent care
    LESS_URGENT = 4    # Green, requires less-urgent care
    NON_URGENT = 5     # White, requires non-urgent care

    def __lt__(self, other):
        if not isinstance(other, TriageCategory):
            return NotImplemented
        return self.value < other.value
