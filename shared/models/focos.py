from .base import Base
from sqlalchemy import Table, Column, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import UUID,DateTime, Integer, Float
import uuid
import datetime
from geoalchemy2.elements import WKBElement, WKTElement
from geoalchemy2 import Geometry
import json
from sqlalchemy.sql.elements import ClauseElement
from geoalchemy2.shape import to_shape
from .evento import eventos_focos_table
import shapely.geometry


from shared.config import config_keys
# Atalhos para as configs
tb = config_keys["tables"]
col_foco = config_keys["columns"]["foco"]
col_reg = config_keys["columns"]["regiao"]
col_sat = config_keys["columns"]["satelite"]
schema_db = config_keys["schema"]
geojson_foco = config_keys.get("geojson", {}).get("foco", {})



focos_regioes_table = Table(
    tb["focos_regioes"],
    Base.metadata,
    Column(col_foco["id_foco"], 
        UUID, 
        ForeignKey(f"{tb['foco']}.{col_foco['id_foco']}", ondelete="CASCADE"), 
        primary_key=True),
    Column(col_reg["id_regiao"], 
        Integer, 
        primary_key=True)
)

class Focos(Base):
    __tablename__ = tb["foco"]

    id_foco: Mapped[uuid.UUID] = mapped_column(col_foco["id_foco"], UUID, primary_key=True)
    data: Mapped[datetime.datetime] = mapped_column(col_foco["data"], DateTime, nullable=False)
    ponto: Mapped[WKBElement | WKTElement | str] = mapped_column(col_foco["ponto"], Geometry('POINT', srid=4326), nullable=False)
    dias_sem_chuva: Mapped[int] = mapped_column(col_foco["dias_sem_chuva"], Integer, nullable=True, default=0)
    frp: Mapped[float | None] = mapped_column(col_foco["frp"], Float, nullable=True)
    id_satelite: Mapped[int] = mapped_column(col_foco["id_satelite"], Integer, ForeignKey(f"{tb['satelite']}.{col_sat['id_satelite']}"), nullable=True)

    def __init__(
        self,
        id_foco=None,
        data=None,
        ponto=None,
        dias_sem_chuva=None,
        frp=None,
        id_satelite=None,
        geometria=None,
        satelite=None,
        **kwargs
    ):
        self.id_foco = id_foco
        self.data = data
        self.dias_sem_chuva = dias_sem_chuva if dias_sem_chuva is not None else 0
        self.frp = frp
        self.id_satelite = id_satelite if id_satelite is not None else satelite

        # Geometria ou ponto
        geom_entrada = ponto if ponto is not None else geometria

        if geom_entrada is not None:
            if isinstance(geom_entrada, (str, bytes, ClauseElement)):
                self.ponto = geom_entrada
            else:
                self.geometria = geom_entrada # Motor OO Shapely

        # Para garantir compatibilidade total com instâncias dinâmicas do SQLAlchemy
        for key, value in kwargs.items():
            setattr(self, key, value)

    @property
    def geometria(self):
        if self.ponto:
            if isinstance(self.ponto, str):
                return shapely.wkt.loads(self.ponto)
            else:
                return to_shape(self.ponto)
        return None

    @geometria.setter
    def geometria(self, value):
        if hasattr(value, 'wkt'):
            self.ponto = WKTElement(value.wkt, srid=4326)
        else:
            self.ponto = value

    eventos: Mapped[list["Eventos"]] = relationship("Eventos", secondary=eventos_focos_table, back_populates="focos")

    @staticmethod
    def row_to_geojson(row):
        geom_json = None
        if getattr(row, 'ponto', None):
            # Se for uma string (veio do ST_AsGeoJSON), lê normalmente
            # se não for converte
            if isinstance(row.ponto, str):
                geom_json = json.loads(row.ponto)
            else:
                shapely_geom = to_shape(row.ponto)
                geom_json = shapely.geometry.mapping(shapely_geom)
        
        return {
            "type": "Feature",
            "properties": {
                geojson_foco.get("id_foco", "id_foco"): str(row.id_foco),
                geojson_foco.get("data", "data"): str(row.data) if row.data else None,
                geojson_foco.get("dias_sem_chuva", "dias_sem_chuva"): getattr(row, col_foco["dias_sem_chuva"], None),
                geojson_foco.get("frp", "frp"): getattr(row, 'frp', None),
                geojson_foco.get("id_satelite", "id_satelite"): getattr(row, col_foco["id_satelite"], None)
            },
            "geometry": geom_json
        }