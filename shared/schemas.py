from pydantic import BaseModel
from typing import List, Optional, Literal, Any
from datetime import datetime

class FocoProperties(BaseModel):
    id: str
    data: datetime
    satelite: int
    dias_sem_chuva: Optional[int]
    frp: Optional[float]

class GeoJsonGeometry(BaseModel):
    type: Literal["Point"]
    coordinates: Any

class Foco(BaseModel):
    type: Literal["Feature"]
    geometry: GeoJsonGeometry
    properties: FocoProperties

class FocosAdapter(BaseModel):
    type: Literal["FeatureCollection"]
    features: List[Foco]

class EventoProperties(BaseModel):
    id_evento: Optional[int] = None
    data_inicio: datetime
    data_fim: Optional[datetime] = None
    data_ultima_observacao: datetime
    status: int
    area_inicio: float
    area_fim: Optional[float] = None
    recorrencia: Optional[int] = None
    persistencia: Optional[float] = None
    duracao: Optional[str] = None
    quantidade_focos: Optional[int] = None
    descricao: Optional[str] = None
    ids_focos: List[str]
    id_evento_absorvedor: Optional[int] = None
    predecessores: Optional[List[int]] = None
    focos: Optional[List[dict]] = None
    regiao: Optional[dict] = None
    ids_regioes: Optional[List[int]] = None


class EventoGeometry(BaseModel):
    type: Literal["Polygon", "MultiPolygon"]
    coordinates: Any

class Evento(BaseModel):
    type: Literal["Feature"]
    geometry: EventoGeometry
    properties: EventoProperties

class EventosAdapter(BaseModel):
    type: Literal["FeatureCollection"]
    features: List[Evento]

class RecorrenciaUpdate(BaseModel):
    id_evento: int
    predecessores: List[int]


