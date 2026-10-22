from .base import Base
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer, UniqueConstraint, String
from shared.config import config_keys

tb = config_keys["tables"]
col_ev = config_keys["columns"]["evento"]
col_desc = config_keys["columns"]["descricao"]

class Descricao(Base):
    __tablename__ = tb["descricao"]
    __table_args__ = (UniqueConstraint(col_desc["id_evento"], col_desc["descricao"]),)
    
    id_descricao: Mapped[int] = mapped_column(col_desc["id_descricao"], Integer, primary_key=True, autoincrement=True)
    descricao: Mapped[str] = mapped_column(col_desc["descricao"], String(1000), nullable=False)
    id_evento: Mapped[int] = mapped_column(col_desc["id_evento"], Integer, ForeignKey(f"{tb['evento']}.{col_ev['id_evento']}", ondelete="CASCADE"), nullable=False)
