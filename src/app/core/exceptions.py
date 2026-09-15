# src/app/core/exceptions.py
class DomainException(Exception):
    """Exceção base de domínio"""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class ProductNotFoundError(DomainException):
    def __init__(self, message: str = "Produto não encontrado"):
        super().__init__(message)

class ProductAccessDeniedError(DomainException):
    def __init__(self, message: str = "Acesso ao produto negado"):
        super().__init__(message)