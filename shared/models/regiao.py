from .base import Base
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from geoalchemy2.elements import WKBElement, WKTElement
from geoalchemy2 import Geometry
from shared.config import config_keys

tb = config_keys["tables"]
col_reg = config_keys["columns"]["regiao"]
schema_db = config_keys["schema"]
col_ev = config_keys["columns"]["evento"]

class Regiao(Base):
    """
    Representação mínima (Lookup) da tabela Regiao que fica em outro schema. Espelha o a regiaoibge
    """
    __tablename__ = tb["regiao"]

    id_regiao: Mapped[int] = mapped_column(col_reg["id_regiao"], Integer, primary_key=True)
    nome_regiao: Mapped[str] = mapped_column(col_reg["nome_regiao"], String(100))
    tipo_regiao: Mapped[str] = mapped_column(col_reg["tipo_regiao"], String(50))
    geometria: Mapped[WKBElement | WKTElement | str] = mapped_column(col_reg["geometria"], Geometry("GEOMETRY", srid=4326), nullable=True)

    # Relação com a tabela associativa
    eventos_regioes: Mapped[list["EventoRegiao"]] = relationship(
        "EventoRegiao", 
        back_populates="regiao",
        primaryjoin="EventoRegiao.id_regiao == Regiao.id_regiao",
        foreign_keys="[EventoRegiao.id_regiao]"
    )
