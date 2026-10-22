from .base import Base
from sqlalchemy import Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from shared.config import config_keys

tb = config_keys["tables"]
col_sat = config_keys["columns"]["satelite"]

class Satelite(Base):
    __tablename__ = tb["satelite"]
    __table_args__ = (UniqueConstraint(col_sat["id_satelite"], col_sat["satelite"]),)
    
    id_satelite: Mapped[int] = mapped_column(col_sat["id_satelite"], Integer, primary_key=True, autoincrement=True)
    satelite: Mapped[str] = mapped_column(col_sat["satelite"], String(50), nullable=False)

