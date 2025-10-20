"""SQLAlchemy models for the application."""

from app.models.base import Base, AuditMixin, TimestampMixin
from app.models.client import Client
from app.models.vehicle import Vehicle
from app.models.document_type import DocumentType
from app.models.external_log import ExternalServiceLog
from app.models.insurance_session import InsuranceSession, SessionStatus, SessionStatusTransitions
from app.models.product import Product
from app.models.quote_product import QuoteProduct
from app.models.quote_product_option import QuoteProductOption, OptionAvailabilityStatus
from app.models.quote_product_selection import QuoteProductSelection
from app.models.soat_form import SoatForm, FormStatus
from app.models.sponsor import Sponsor
from app.models.user import User
from app.models.vehicle_homologation import VehicleHomologation
from app.models.vehicle_homologation_selection import VehicleHomologationSelection
from app.models.plan_ap import PlanAP
from app.models.vehicle_class import VehicleClass
from app.models.plan_vehicle_class import PlanVehicleClass

__all__ = [
    "Base",
    "AuditMixin",
    "TimestampMixin",
    "Client",
    "Vehicle",
    "DocumentType",
    "ExternalServiceLog",
    "InsuranceSession",
    "SessionStatus",
    "SessionStatusTransitions",
    "Product",
    "QuoteProduct",
    "QuoteProductOption",
    "OptionAvailabilityStatus",
    "QuoteProductSelection",
    "SoatForm",
    "FormStatus",
    "Sponsor",
    "User",
    "VehicleHomologation",
    "VehicleHomologationSelection",
    "PlanAP",
    "VehicleClass",
    "PlanVehicleClass",
]
