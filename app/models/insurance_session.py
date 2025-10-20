from sqlalchemy import ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.mysql import VARCHAR, TINYINT, CHAR
from typing import Optional, TYPE_CHECKING, Set, Dict
import enum
import uuid

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.client import Client
    from app.models.vehicle import Vehicle
    from app.models.vehicle_homologation import VehicleHomologation
    from app.models.quote_product import QuoteProduct


class SessionStatus(str, enum.Enum):
    """
    Insurance session status enum.
    
    Flujo normal:
    CREATED → VALIDATING → VALIDATED → QUOTING → QUOTED → 
    SELECTING → SELECTED → ISSUING → ISSUED → COMPLETED
    
    Estados de error:
    VALIDATION_FAILED, QUOTE_FAILED, SELECTION_FAILED, 
    ISSUE_FAILED, CANCELLED, EXPIRED
    """
    
    # Estados iniciales
    CREATED = "created"  # Sesión creada, datos mínimos
    
    # Flujo de validación de propietario
    VALIDATING = "validating"  # Consultando RUNT, validando propietario
    VALIDATED = "validated"  # Propietario validado exitosamente
    VALIDATION_FAILED = "validation_failed"  # Fallo en validación de propietario
    
    # Flujo de cotización
    QUOTING = "quoting"  # Consultando APIs de seguros
    QUOTED = "quoted"  # Cotización exitosa, planes disponibles
    QUOTE_FAILED = "quote_failed"  # Fallo al obtener cotización
    
    # Flujo de selección de planes
    SELECTING = "selecting"  # Usuario seleccionando planes
    SELECTED = "selected"  # Planes seleccionados por usuario
    SELECTION_FAILED = "selection_failed"  # Fallo en selección (plan inválido, etc.)
    
    # Flujo de emisión/expedición
    ISSUING = "issuing"  # Pre-expedición y validación de emisión
    ISSUED = "issued"  # Pre-expedición exitosa, listo para pago
    ISSUE_FAILED = "issue_failed"  # Fallo en pre-expedición
    
    # Estados finales
    PAYMENT_PENDING = "payment_pending"  # Esperando confirmación de pago
    PAYMENT_CONFIRMED = "payment_confirmed"  # Pago confirmado
    PAYMENT_FAILED = "payment_failed"  # Pago fallido
    
    COMPLETED = "completed"  # Pólizas emitidas y entregadas
    CANCELLED = "cancelled"  # Sesión cancelada por usuario/sistema
    EXPIRED = "expired"  # Sesión expirada por timeout
    
    # Estado legacy para compatibilidad
    STARTED = "started"  # Deprecated: usar CREATED


class SessionStatusTransitions:
    """Gestiona las transiciones válidas entre estados de sesión."""
    
    # Mapa de transiciones válidas: estado_actual → [estados_permitidos]
    VALID_TRANSITIONS: Dict[SessionStatus, Set[SessionStatus]] = {
        # Desde CREATED
        SessionStatus.CREATED: {
            SessionStatus.VALIDATING,
            SessionStatus.CANCELLED,
            SessionStatus.EXPIRED
        },
        
        # Desde VALIDATING
        SessionStatus.VALIDATING: {
            SessionStatus.VALIDATED,
            SessionStatus.VALIDATION_FAILED,
            SessionStatus.CANCELLED
        },
        
        # Desde VALIDATED
        SessionStatus.VALIDATED: {
            SessionStatus.QUOTING,
            SessionStatus.CANCELLED
        },
        
        # Desde VALIDATION_FAILED
        SessionStatus.VALIDATION_FAILED: {
            SessionStatus.VALIDATING,  # Reintentar
            SessionStatus.CANCELLED
        },
        
        # Desde QUOTING
        SessionStatus.QUOTING: {
            SessionStatus.QUOTED,
            SessionStatus.QUOTE_FAILED,
            SessionStatus.CANCELLED
        },
        
        # Desde QUOTED
        SessionStatus.QUOTED: {
            SessionStatus.QUOTING,  # Re-cotizar
            SessionStatus.SELECTING,
            SessionStatus.SELECTED,  # Selección directa
            SessionStatus.CANCELLED
        },
        
        # Desde QUOTE_FAILED
        SessionStatus.QUOTE_FAILED: {
            SessionStatus.QUOTING,  # Reintentar
            SessionStatus.CANCELLED
        },
        
        # Desde SELECTING
        SessionStatus.SELECTING: {
            SessionStatus.SELECTED,
            SessionStatus.SELECTION_FAILED,
            SessionStatus.CANCELLED
        },
        
        # Desde SELECTED
        SessionStatus.SELECTED: {
            SessionStatus.QUOTING,  # Re-cotizar
            SessionStatus.SELECTING,  # Cambiar selección
            SessionStatus.ISSUING,
            SessionStatus.CANCELLED
        },
        
        # Desde SELECTION_FAILED
        SessionStatus.SELECTION_FAILED: {
            SessionStatus.SELECTING,  # Reintentar
            SessionStatus.CANCELLED
        },
        
        # Desde ISSUING
        SessionStatus.ISSUING: {
            SessionStatus.ISSUED,
            SessionStatus.ISSUE_FAILED,
            SessionStatus.CANCELLED
        },
        
        # Desde ISSUED
        SessionStatus.ISSUED: {
            SessionStatus.PAYMENT_PENDING,
            SessionStatus.CANCELLED
        },
        
        # Desde ISSUE_FAILED
        SessionStatus.ISSUE_FAILED: {
            SessionStatus.ISSUING,  # Reintentar
            SessionStatus.CANCELLED
        },
        
        # Desde PAYMENT_PENDING
        SessionStatus.PAYMENT_PENDING: {
            SessionStatus.PAYMENT_CONFIRMED,
            SessionStatus.PAYMENT_FAILED,
            SessionStatus.CANCELLED,
            SessionStatus.EXPIRED
        },
        
        # Desde PAYMENT_CONFIRMED
        SessionStatus.PAYMENT_CONFIRMED: {
            SessionStatus.COMPLETED
        },
        
        # Desde PAYMENT_FAILED
        SessionStatus.PAYMENT_FAILED: {
            SessionStatus.PAYMENT_PENDING,  # Reintentar pago
            SessionStatus.CANCELLED
        },
        
        # Desde COMPLETED
        SessionStatus.COMPLETED: set(),  # Estado final, no transiciones
        
        # Desde CANCELLED
        SessionStatus.CANCELLED: set(),  # Estado final
        
        # Desde EXPIRED
        SessionStatus.EXPIRED: set(),  # Estado final
        
        # STARTED (legacy) - compatibilidad
        SessionStatus.STARTED: {
            SessionStatus.CREATED,
            SessionStatus.VALIDATING,
            SessionStatus.VALIDATED,
            SessionStatus.QUOTING,
            SessionStatus.CANCELLED
        }
    }
    
    # Estados que indican error
    ERROR_STATES: Set[SessionStatus] = {
        SessionStatus.VALIDATION_FAILED,
        SessionStatus.QUOTE_FAILED,
        SessionStatus.SELECTION_FAILED,
        SessionStatus.ISSUE_FAILED,
        SessionStatus.PAYMENT_FAILED
    }
    
    # Estados finales (no hay vuelta atrás)
    FINAL_STATES: Set[SessionStatus] = {
        SessionStatus.COMPLETED,
        SessionStatus.CANCELLED,
        SessionStatus.EXPIRED
    }
    
    # Estados en progreso (operación en curso)
    IN_PROGRESS_STATES: Set[SessionStatus] = {
        SessionStatus.VALIDATING,
        SessionStatus.QUOTING,
        SessionStatus.SELECTING,
        SessionStatus.ISSUING
    }
    
    @classmethod
    def can_transition(cls, from_status: SessionStatus, to_status: SessionStatus) -> bool:
        """
        Verifica si una transición de estado es válida.
        
        Args:
            from_status: Estado actual
            to_status: Estado destino
            
        Returns:
            True si la transición es válida
        """
        allowed_transitions = cls.VALID_TRANSITIONS.get(from_status, set())
        return to_status in allowed_transitions
    
    @classmethod
    def is_error_state(cls, status: SessionStatus) -> bool:
        """Verifica si un estado es de error."""
        return status in cls.ERROR_STATES
    
    @classmethod
    def is_final_state(cls, status: SessionStatus) -> bool:
        """Verifica si un estado es final."""
        return status in cls.FINAL_STATES
    
    @classmethod
    def is_in_progress(cls, status: SessionStatus) -> bool:
        """Verifica si una operación está en progreso."""
        return status in cls.IN_PROGRESS_STATES
    
    @classmethod
    def get_next_states(cls, current_status: SessionStatus) -> Set[SessionStatus]:
        """Obtiene los estados válidos siguientes desde el estado actual."""
        return cls.VALID_TRANSITIONS.get(current_status, set())


class InsuranceSession(Base, TimestampMixin):
    """Insurance session table - tracks the insurance purchase flow."""
    
    __tablename__ = "insurance_sessions"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(VARCHAR(50), nullable=False, unique=True, index=True)
    client_id: Mapped[int] = mapped_column(
        ForeignKey("clients.id", name="insurance_sessions_ibfk_2"), 
        nullable=False,
        index=True
    )
    vehicle_id: Mapped[int] = mapped_column(
        ForeignKey("vehicles.id", name="insurance_sessions_ibfk_3"),
        nullable=False,
        index=True
    )
    is_owner: Mapped[bool] = mapped_column(TINYINT(1), nullable=False, default=False)
    status: Mapped[SessionStatus] = mapped_column(
        SQLEnum(SessionStatus, name="session_status_enum", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=SessionStatus.STARTED
    )
    
    # Relationships
    client: Mapped["Client"] = relationship("Client", foreign_keys=[client_id])
    vehicle: Mapped["Vehicle"] = relationship("Vehicle", foreign_keys=[vehicle_id])
    homologations: Mapped[list["VehicleHomologation"]] = relationship(
        "VehicleHomologation", 
        back_populates="session",
        # cascade="all, delete-orphan"
    )
    quote_products: Mapped[list["QuoteProduct"]] = relationship(
        "QuoteProduct",
        back_populates="session",
        # cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<InsuranceSession(slug={self.slug}, status={self.status}, is_owner={self.is_owner})>"
    
    def can_transition_to(self, new_status: SessionStatus) -> bool:
        """
        Verifica si se puede transicionar al nuevo estado.
        
        Args:
            new_status: Estado destino
            
        Returns:
            True si la transición es válida
        """
        return SessionStatusTransitions.can_transition(self.status, new_status)
    
    def transition_to(self, new_status: SessionStatus, force: bool = False) -> bool:
        """
        Transiciona a un nuevo estado si es válido.
        
        Args:
            new_status: Estado destino
            force: Si True, ignora validación de transición
            
        Returns:
            True si la transición fue exitosa
            
        Raises:
            ValueError: Si la transición no es válida y force=False
        """
        if force or self.can_transition_to(new_status):
            self.status = new_status
            return True
        
        allowed = SessionStatusTransitions.get_next_states(self.status)
        raise ValueError(
            f"Transición inválida de {self.status.value} a {new_status.value}. "
            f"Estados permitidos: {[s.value for s in allowed]}"
        )
    
    @property
    def is_error_state(self) -> bool:
        """Verifica si la sesión está en estado de error."""
        return SessionStatusTransitions.is_error_state(self.status)
    
    @property
    def is_final_state(self) -> bool:
        """Verifica si la sesión está en estado final."""
        return SessionStatusTransitions.is_final_state(self.status)
    
    @property
    def is_in_progress(self) -> bool:
        """Verifica si hay una operación en progreso."""
        return SessionStatusTransitions.is_in_progress(self.status)
    
    @property
    def can_quote(self) -> bool:
        """Verifica si se puede cotizar en el estado actual."""
        return self.status in {
            SessionStatus.VALIDATED,
            SessionStatus.QUOTED,
            SessionStatus.SELECTED
        }
    
    @property
    def can_select(self) -> bool:
        """Verifica si se puede seleccionar planes."""
        return self.status in {
            SessionStatus.QUOTED,
            SessionStatus.SELECTED
        }
    
    @property
    def can_issue(self) -> bool:
        """Verifica si se puede emitir/pre-expedir."""
        return self.status == SessionStatus.SELECTED
    
    @classmethod
    def create_session(
        cls,
        client_id: int,
        vehicle_id: int,
        is_owner: bool = False,
        status: SessionStatus = SessionStatus.CREATED
    ) -> "InsuranceSession":
        """Factory method to create a new insurance session with a unique UUID slug.
        
        Args:
            client_id: Client database ID
            vehicle_id: Vehicle database ID
            is_owner: Whether the client is the vehicle owner
            status: Initial session status (default: CREATED)
            
        Returns:
            New InsuranceSession instance with generated UUID slug
        """
        slug = str(uuid.uuid4())
        return cls(
            slug=slug,
            client_id=client_id,
            vehicle_id=vehicle_id,
            is_owner=is_owner,
            status=status
        )
