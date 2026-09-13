from abc import ABC, abstractmethod
from typing import Dict, Any, List

class BaseExtractor(ABC):
    """
    Abstract Base Class for Document Feature Extractors.
    Allows adding new document types without modifying existing extractors.
    """

    @abstractmethod
    def extract(self, raw_text: str, text_blocks: List[Dict[str, Any]], qr_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Extracts structured fields from OCR text, bounding blocks, or QR payload.
        """
        pass
