from typing import Any, Dict
from fastapi import HTTPException

class JubError(Exception):
    def __init__(self, status_code: int, detail: Any = None, metadata: Dict[str, str]  = None) -> None:
        self.status_code = status_code
        self.detail = detail
        self.metadata = metadata
        # super().__init__(status_code, detail, headers)
    
    @staticmethod
    def from_exception(exc: Exception) -> 'JubError':
        """Converts any exception into a JubError with a 500 status code."""
        return JubError(status_code=500, detail=str(exc))

    # @staticmethod
    def to_http_exception(self) -> HTTPException:
        """Converts a JubError into a FastAPI HTTPException."""
        return HTTPException(status_code=self.status_code, detail=self.detail, headers=self.metadata)

class UnknownError(JubError):
    def __init__(self,detail: Any = None, headers: Dict[str, str]  = None) -> None:
        super().__init__(500, detail, headers)

class NotFound(JubError):
    def __init__(self,detail: Any = None, headers: Dict[str, str]  = None) -> None:
        super().__init__(404, detail, headers)

class CreationError(JubError):
    def __init__(self,detail: Any = None, headers: Dict[str, str]  = None) -> None:
        super().__init__(400, detail, headers)
        

class AlreadyExists(JubError):
    def __init__(self,detail: Any = None, headers: Dict[str, str] = None) -> None:
        super().__init__(403, detail, headers)