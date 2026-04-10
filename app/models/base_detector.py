from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List

@dataclass
class RawDetection:
    confidence: float
    frame_scores: List[float]
    artifact_scores: dict
    metadata: dict

class BaseDetector(ABC):
    def __init__(self):
        self.model = None
        self.loaded = False
        self.device = self._get_device()

    def _get_device(self):
        import torch
        if torch.cuda.is_available():
            return torch.device("cuda")
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return torch.device("mps")
        return torch.device("cpu")

    @abstractmethod
    def load(self): ...

    @abstractmethod
    def predict(self, file_path: str) -> RawDetection: ...

    def ensure_loaded(self):
        if not self.loaded:
            self.load()
            self.loaded = True
