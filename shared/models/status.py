from .base import Base
from sqlalchemy import Integer, String, UniqueConstraint, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from shared.config import config_keys


tb = config_keys["tables"]
col_st = config_keys["columns"]["status"]


class Status(Base):
    __tablename__ = tb["status"]
    __table_args__ = (UniqueConstraint(col_st["id_status"], col_st["nome"]),)
    
    id_status: Mapped[int] = mapped_column(col_st["id_status"], Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(col_st["nome"], String(50), nullable=False)


