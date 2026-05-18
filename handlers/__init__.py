from .domain import router as domain_router
from .email_h import router as email_router
from .phone_h import router as phone_router
from .username_h import router as username_router
from .social_h import router as social_router
from .image_h import router as image_router
from .breach_h import router as breach_router
from .fio_h import router as fio_router
from .company_h import router as company_router
from .car_h import router as car_router
from .doc_h import router as doc_router

__all__ = [
    "domain_router", "email_router", "phone_router",
    "username_router", "social_router", "image_router",
    "breach_router", "fio_router",
    "company_router", "car_router", "doc_router",
]
