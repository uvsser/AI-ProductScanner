class DomainException(Exception):
    """Base domain exception."""
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

class EntityNotFoundException(DomainException):
    def __init__(self, entity_name: str, identifier: any):
        super().__init__(f"{entity_name} '{identifier}' not found.", status_code=404)

class ValidationException(DomainException):
    def __init__(self, message: str):
        super().__init__(message, status_code=400)

class UnauthorizedException(DomainException):
    def __init__(self, message: str = "Invalid or expired token. Please log in again."):
        super().__init__(message, status_code=401)
