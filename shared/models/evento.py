from .base import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import timedelta, datetime
from sqlalchemy import Table, Column, ForeignKey
from geoalchemy2.elements import WKBElement, WKTElement
from geoalchemy2 import Geometry
from geoalchemy2.shape import to_shape
from sqlalchemy import  UUID,DateTime, Integer, Float, Index, text, Interval, func, select, insert, delete
from .regiao import Regiao
from sqlalchemy.sql.elements import ClauseElement
        
import json
import shapely
import shapely.wkt
import numpy as np
from shapely.geometry import shape, GeometryCollection
from shapely.ops import transform
import pyproj
from shapely.ops import unary_union

from shared.config import config_keys
tb = config_keys["tables"]
col_ev = config_keys["columns"]["evento"]
col_fc = config_keys["columns"]["foco"]
col_sat = config_keys["columns"]["satelite"]
col_reg = config_keys["columns"]["regiao"]
schema_db = config_keys["schema"]
geojson_ev = config_keys.get("geojson", {}).get("evento", {})
geojson_foco = config_keys.get("geojson", {}).get("foco", {})

status_data = config_keys.get("status_data", [])
satelite_raios_cache = {s["id_satelite"]: float(s.get("raio")) for s in config_keys.get("satelite_data")}
status_map = {item["nome"].lower(): item["id_status"] for item in status_data}

STATUS_ATIVO = status_map.get("ativo", 1)
STATUS_OBSERVACAO = status_map.get("observacao", 2)
STATUS_EXTINTO = status_map.get("extinto", 3)

# Inicializa as transformações de projeção globalmente para máxima performance
project_to_5880_transform = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:5880", always_xy=True).transform
project_to_4326_transform = pyproj.Transformer.from_crs("EPSG:5880", "EPSG:4326", always_xy=True).transform

eventos_focos_table = Table(
    tb["eventos_focos"],
    Base.metadata,
    Column(col_ev["id_evento"], 
            Integer, 
            ForeignKey(f"{tb['evento']}.{col_ev['id_evento']}", ondelete="CASCADE"), 
            primary_key=True),
    Column(col_fc["id_foco"], 
            UUID, 
            ForeignKey(f"{tb['foco']}.{col_fc['id_foco']}", ondelete="CASCADE"), 
            primary_key=True)
)

eventos_predecessores_table = Table(
    tb["eventos_predecessores"],
    Base.metadata,
    Column(col_ev["id_evento"], 
            Integer, 
            ForeignKey(f"{tb['evento']}.{col_ev['id_evento']}", ondelete="CASCADE"), 
            primary_key=True),
    Column(col_ev["predecessores"], 
        Integer, 
        ForeignKey(f"{tb['evento']}.{col_ev['id_evento']}", ondelete="CASCADE"), 
        primary_key=True)
)

class EventoRegiao(Base):
    __tablename__ = tb["eventos_regioes"]
    
    id_evento: Mapped[int] = mapped_column(col_ev["id_evento"], Integer, ForeignKey(f"{tb['evento']}.{col_ev['id_evento']}", ondelete="CASCADE"), primary_key=True)
    id_regiao: Mapped[int] = mapped_column(col_reg["id_regiao"], Integer, primary_key=True)
    
    # Relações de volta
    evento: Mapped["Eventos"] = relationship("Eventos", back_populates="eventos_regioes")
    regiao: Mapped["Regiao"] = relationship(
        "Regiao", 
        back_populates="eventos_regioes",
        primaryjoin="EventoRegiao.id_regiao == Regiao.id_regiao",
        foreign_keys="[EventoRegiao.id_regiao]"
    )

class Eventos(Base):
    
    __tablename__ = tb["evento"]
    __table_args__ = (Index('ix_evento_data_geom_unique', col_ev["data_inicio"], text(f"md5(ST_AsBinary({col_ev['geometria']}))"), unique=True),)

    id_evento: Mapped[int] = mapped_column(col_ev["id_evento"], Integer, primary_key=True, autoincrement=True)
    data_inicio: Mapped[datetime] = mapped_column(col_ev["data_inicio"], DateTime, nullable=False)
    data_fim: Mapped[datetime | None] = mapped_column(col_ev["data_fim"], DateTime, nullable=True)
    data_ultima_observacao: Mapped[datetime | None] = mapped_column(col_ev["data_ultima_observacao"], DateTime, nullable=True)
    status: Mapped[int] = mapped_column(col_ev["status"], Integer, ForeignKey(f"{tb['status']}.{config_keys['columns']['status']['id_status']}"), nullable=False)
    area_inicio: Mapped[float] = mapped_column(col_ev["area_inicio"], Float, nullable=True)
    area_fim: Mapped[float] = mapped_column(col_ev["area_fim"], Float, nullable=True)
    recorrencia: Mapped[int] = mapped_column(col_ev["recorrencia"], Integer, nullable=True, default=0)
    persistencia: Mapped[float] = mapped_column(col_ev["persistencia"], Float, nullable=True, default=0)
    duracao: Mapped[timedelta | None] = mapped_column(col_ev["duracao"], Interval, nullable=True)
    qnt_focos: Mapped[int] = mapped_column(col_ev["qnt_focos"], Integer, nullable=True, default=0)
    geometria: Mapped[WKBElement | WKTElement | str] = mapped_column(col_ev["geometria"], Geometry('GEOMETRY', srid=4326), nullable=True)
    focos: Mapped[list["Focos"]] = relationship("Focos", secondary=eventos_focos_table, back_populates="eventos")

    predecessores: Mapped[list["Eventos"]] = relationship(
        "Eventos",
        secondary=eventos_predecessores_table,
        primaryjoin=id_evento == eventos_predecessores_table.c[col_ev["id_evento"]],
        secondaryjoin=id_evento == eventos_predecessores_table.c[col_ev["predecessores"]],
        backref="sucessores"
    )

    id_evento_absorvedor: Mapped[int | None] = mapped_column(col_ev["id_evento_absorvedor"], Integer, ForeignKey(f"{tb['evento']}.{col_ev['id_evento']}", ondelete="SET NULL"), nullable=True)
    
    #AUXILIARES
    eventos_regioes: Mapped[list["EventoRegiao"]] = relationship("EventoRegiao", back_populates="evento", cascade="all, delete-orphan")

    # Está iniciando com valores nulos até que o orm carregue ou pydantic faça testes
    def __init__(
        self,
        focos=None,
        geometria=None,
        data_inicio=None,
        data_ultima_observacao=None,
        data_fim=None,
        id_evento=None,
        area_inicio=None,
        area_fim=None,
        status=None,
        id_evento_absorvedor=None,
        persistencia=None,
        recorrencia=None,
        duracao=None,
        qnt_focos=None,
        **kwargs
    ):
        self.id_evento = id_evento if id_evento is not None else None
        self.focos = focos if focos is not None else []
        self.data_inicio = data_inicio if data_inicio is not None else None
        self.data_ultima_observacao = data_ultima_observacao if data_ultima_observacao is not None else None
        self.calcular_duracao()
        self.data_fim = data_fim if data_fim is not None else None
        self.area_inicio = area_inicio if area_inicio is not None else None
        self.area_fim = area_fim if area_fim is not None else None
        self.status = status
        self.id_evento_absorvedor = id_evento_absorvedor
        self.persistencia = persistencia
        self.recorrencia = (
            recorrencia
            if recorrencia is not None
            else 0
        )
        #REPENSAR
        self.qnt_focos = qnt_focos if qnt_focos is not None else 0
        if not self.qnt_focos and self.focos:
            self.qnt_focos = len(self.focos)

        # Garantir a tipagem a depender se será orm ou motor que irá instanciar
        if geometria is not None:
            if isinstance(geometria, (str, bytes, ClauseElement)): # Se for WKT/WKB ou func. do banco
                self.geometria = geometria
            else:
                self.geom = geometria # Se for objeto Shapely vindo do Motor OO

        # Para garantir compatibilidade total com instâncias dinâmicas do SQLAlchemy
        for key, value in kwargs.items():
            setattr(self, key, value)

    # -- Propriedades e Atributos dinâmicos para uso do Motor OO --
    @property
    def geom(self):
        if self.geometria:
            if isinstance(self.geometria, str):
                return shapely.wkt.loads(self.geometria)
            else:
                
                return to_shape(self.geometria)
        return None
    
    @geom.setter
    def geom(self, value):
        if hasattr(value, 'wkt'):
            self.geometria = WKTElement(value.wkt, srid=4326)
        else:
            self.geometria = value
    
    @staticmethod
    def row_to_geojson(evento, geojson_geom=None, include_regiao=False, include_satelites=False, descricao_text=None):
        from .focos import Focos 
        
        focos_list = []
        if evento.focos:
            for foco in evento.focos:
                focos_list.append(Focos.row_to_geojson(foco))
                
        regioes_dict = {}
        if include_regiao and evento.eventos_regioes:
            chave_historico = config_keys.get("geojson", {}).get("evento", {}).get("historico_regioes", "historico_regioes")
            regioes_dict[chave_historico] = []
            
            for ev_reg in evento.eventos_regioes:

                tipo = ev_reg.regiao.tipo_regiao
                nome = ev_reg.regiao.nome_regiao
                
                if tipo not in regioes_dict:
                    regioes_dict[tipo] = []
                regioes_dict[tipo].append(nome)
                
                regioes_dict[chave_historico].append({
                    col_reg["id_regiao"]: ev_reg.id_regiao
                })
                
        satelites_list = []
        if include_satelites and evento.focos:
            satelite_map = {s["id_satelite"]: s["satelite"] for s in config_keys.get("satelite_data", [])}
            unique_sat_ids = {foco.id_satelite for foco in evento.focos if foco.id_satelite is not None}
            for sat_id in unique_sat_ids:
                satelites_list.append({
                    "id_satelite": sat_id,
                    "nome_satelite": satelite_map.get(sat_id, "Desconhecido")
                })

                
        properties = {
            geojson_ev.get("id_evento", "id_evento"): evento.id_evento,
            geojson_ev.get("data_inicio", "data_inicio"): str(evento.data_inicio) if evento.data_inicio else None,
            geojson_ev.get("data_fim", "data_fim"): str(evento.data_fim) if getattr(evento, 'data_fim', None) else None,
            geojson_ev.get("data_ultima_observacao", "data_ultima_observacao"): str(evento.data_ultima_observacao) if getattr(evento, 'data_ultima_observacao', None) else None,
            geojson_ev.get("area_inicio", "area_inicio"): getattr(evento, 'area_inicio'),
            geojson_ev.get("area_fim", "area_fim"): getattr(evento, 'area_fim', None),
            geojson_ev.get("status", "status"): getattr(evento, 'status'),
            geojson_ev.get("recorrencia", "recorrencia"): getattr(evento, 'recorrencia', None),
            geojson_ev.get("persistencia", "persistencia"): getattr(evento, 'persistencia', None),
            geojson_ev.get("duracao", "duracao"): str(evento.duracao) if getattr(evento, 'duracao', None) else None,
            geojson_ev.get("qnt_focos", "qnt_focos"): getattr(evento, 'qnt_focos', None),
            geojson_ev.get("descricao", "descricao"): descricao_text if descricao_text is not None else getattr(evento, 'descricao', "Sem descrição"),
            geojson_ev.get("id_evento_absorvedor", "id_evento_absorvedor"): getattr(evento, 'id_evento_absorvedor', None),
            geojson_ev.get("predecessores", "predecessores"): [p.id_evento for p in evento.predecessores] if getattr(evento, 'predecessores', None) else [],
            geojson_ev.get("ids_focos", "ids_focos"): [str(f.id_foco) for f in evento.focos] if getattr(evento, 'focos', None) else [],
            "focos": focos_list,
            "regiao": regioes_dict
        }

        if include_satelites:
            properties["satelites"] = satelites_list

        geom_json = None
        if geojson_geom:
            import json
            geom_json = json.loads(geojson_geom)
        elif getattr(evento, 'poligono', None) and isinstance(evento.poligono, str):
            geom_json = json.loads(evento.poligono)

        return {
            "type": "Feature",
            "properties": properties,
            "geometry": geom_json
        }
    


    def atualizar_regioes(self, gdf_regioes):
        """
        Recebe o GeoDataFrame global de regiões em memória e descobre
        quais regiões intersectam com o polígono do evento usando o método vetorizado do geopandas.
        Retorna uma lista de IDs das regiões atingidas.
        """

        if not self.poligono:
            return []
            
        # Garantindo a tipagem da geometria 
        if isinstance(self.poligono, str):
            geom_shapely = shapely.wkt.loads(self.poligono)
        else:
            geom_shapely = shape(self.poligono)
            
        #testa todas as regiões contra essa única geometria
        regioes_atingidas_gdf = gdf_regioes[gdf_regioes.intersects(geom_shapely)]
        
        ids_regioes = regioes_atingidas_gdf['id_regiao'].tolist()
        data_atual = self.data_ultima_observacao
        
        # 1. Mapeia as regiões que o evento JÁ POSSUI
        ids_existentes = {er.id_regiao for er in self.eventos_regioes}
        
        # 2. Usa diferença de conjuntos para encontrar as INÉDITAS
        novos_ids = set(ids_regioes) - ids_existentes
        for id_r in novos_ids:
            nova_assoc = EventoRegiao(id_regiao=id_r)
            self.eventos_regioes.append(nova_assoc)
        
        return ids_regioes
        
    def adicionar_regioes(self, ids_regioes: list[int]) -> None:
        """ Adiciona as regiões ao evento caso não existam. """
        ids_existentes = {er.id_regiao for er in self.eventos_regioes}
        novos_ids = set(ids_regioes) - ids_existentes
        for id_r in novos_ids:
            nova_assoc = EventoRegiao(id_regiao=id_r)
            self.eventos_regioes.append(nova_assoc)

# =========================================== Métodos do Motor OO ================================ 
    def obter_ids_focos(self) -> list[str]:
        if not self.focos:
            return []
        # Usa set para evitar IDs duplicados (caso aconteça por algum motivo)
        ids = {str(foco.id_foco) for foco in self.focos}
        return sorted(list(ids))

    def obter_data_ultima_observacao(self):
        datas = []
        if self.data_ultima_observacao is not None:
            datas.append(self.data_ultima_observacao)
        if self.focos:
            datas.extend(foco.data for foco in self.focos)
        return max(datas) if datas else None

    def calcular_area(self) -> float:
        if self.geom:
            return round((self.geom.area / 1_000_000), 2)
        return 00.000

    def adicionar_foco(self, foco):
        self.focos.append(foco)
        self.qnt_focos += 1

    def quantidade_focos(self) -> int:
        return self.qnt_focos
        
    def extinguir_por_fusionamento(
        self, 
        id_evento_absorvedor: int, 
        data_ultimo_registro
        ) -> None:
        
        self.status = STATUS_EXTINTO
        self.id_evento_absorvedor = id_evento_absorvedor
        self.data_ultima_observacao = data_ultimo_registro
        self.calcular_duracao()
        self.data_fim = data_ultimo_registro
        self.area_fim = self.calcular_area()

    def atualizar_status(self, data_ultima_base):

        if isinstance(self.id_evento_absorvedor,int):      # proteção para não modificar status de eventos extintos 
            self.status = STATUS_EXTINTO    # na ataulização.
            
            if self.data_fim is None:
                self.data_fim = self.data_ultima_observacao

            return self.status

        dias_sem_focos = (
            data_ultima_base
            - self.data_ultima_observacao.normalize()
        ).days

        if dias_sem_focos < 0:
            raise ValueError(
                "A data da última base não pode ser anterior "
                "à data do último foco do evento."
            )

        if dias_sem_focos <= 1:
            self.status = STATUS_ATIVO
        elif dias_sem_focos <= 6:
            self.status = STATUS_OBSERVACAO
        else:
            self.status = STATUS_EXTINTO
            if self.data_fim is None:
                self.data_fim = self.data_ultima_observacao
            self.area_fim = self.calcular_area()       

    def incorporar_predecessores_recorrencia(
        self,
        predecessores: list["Eventos"],
    ) -> None:

        ids_existentes = {
            evento.id_evento
            for evento in self.predecessores
        }

        for predecessor in predecessores:

            if predecessor.id_evento in ids_existentes:
                continue

            self.predecessores.append(
                predecessor
            )

            ids_existentes.add(
                predecessor.id_evento
            )

        self.recorrencia = len(
            self.predecessores
        )

    def absorver_evento(
        self, 
        evento_absorvido: "Eventos"
        ) -> None:
        
        if not self.focos:
            self.focos = []
        if evento_absorvido.focos:
            self.focos.extend(evento_absorvido.focos)

        focos_a_adicionar = getattr(evento_absorvido, 'qnt_focos', 0)
        if not focos_a_adicionar:
            focos_a_adicionar = len(evento_absorvido.obter_ids_focos())
            
        self.qnt_focos += focos_a_adicionar

        
        geoms = []
        if self.geom: geoms.append(self.geom)
        if evento_absorvido.geom: geoms.append(evento_absorvido.geom)
        if geoms:
            self.geom = unary_union(geoms)

        datas = [self.data_ultima_observacao, evento_absorvido.data_ultima_observacao]

        self.data_ultima_observacao = max(datas)
        self.calcular_duracao()
        
    def absorver_eventos(
        self,
        eventos_absorvidos: list["Eventos"],
    ) -> None:

        for evento_absorvido in eventos_absorvidos:

            self.absorver_evento(
                evento_absorvido
            )

            self.incorporar_predecessores_recorrencia(
                evento_absorvido.predecessores
            )

            evento_absorvido.predecessores = []
            evento_absorvido.recorrencia = 0

    def quantidade_sitios(self) -> int:
        if not self.focos:
            return 0

        sitios = set()
        for foco in self.focos:
            p = foco.geometria
            if p is not None:
                sitios.add((p.x, p.y))
        return len(sitios)

    # Pensar que isso do deve ser feito com GOES se assim for manter apenas o persitencia _state
    def calcular_persistencia(self) -> float:
        qs = self.quantidade_sitios()
        if qs == 0: return 0.0
        return round(self.quantidade_focos() / qs, 2)

    def calcular_duracao(self):
        if self.data_inicio and getattr(self, 'data_ultima_observacao'):
            self.duracao = (self.data_ultima_observacao - self.data_inicio) + timedelta(days=1) #assim o evento que começou e terminou no mesmo dia dura um dia sempre
        return self.duracao

# =========================================== Métodos utilizei no state  ================================ 
    def atualizar_duracao_state(self, data_obs):
        """
        Calcula a duração do evento baseado na data de início.
        Regra A: A duração corre até a data de observação, a menos que o evento tenha sido extinto (data_fim).
        """
        if self.data_inicio:
            referencia_final = self.data_fim if self.data_fim else self.data_ultima_observacao
            self.duracao = (referencia_final - self.data_inicio) + timedelta(days=1)
                
        return self.duracao

    def atualizar_ultima_observacao_state(self):
        """
        Atualiza a data de última observação do evento baseado nos focos atuais.
        """
        if self.focos:
            self.data_ultima_observacao = max(fc.data for fc in self.focos)
            #self.calcular_duracao()
        return self.data_ultima_observacao

    def calcular_persistencia_state(self):
        """
        Calcula a persistência do evento (média de focos por pixel GOES na área).
        Baseia-se nos focos já associados (self.focos).
        """
        lista_satelites_goes = config_keys['satelites_goes']
        lista_focos_goes = [fc for fc in self.focos if getattr(fc, 'id_satelite', 0) in lista_satelites_goes]
        
        if not lista_focos_goes:
            self.persistencia = 0.0
            return 0.0
            
        pixels_distintos = set([fc.ponto for fc in lista_focos_goes])
        
        self.persistencia = round(len(lista_focos_goes) / len(pixels_distintos), 2)
        return self.persistencia
    
    def atualizar_status_state(self, data_obs):
        """
        Define o status do evento (Ativo, Observação, Extinto) 
        comparando com a data_obs (data da iteração).
        """
            
        # Extinção dinâmica (se passou da janela de inatividade sem receber focos, declara extinção para o state atual)
        if self.data_ultima_observacao and (data_obs.date() - self.data_ultima_observacao.date()).days >= 7:
            self.status = STATUS_EXTINTO
            self.data_fim = self.data_ultima_observacao
            # Calcula e trava a área fim baseada no último dia ativo
            self.area_fim = self.calcular_area_do_dia_state(self.data_ultima_observacao)
            return self.status

        # Verifica se houve algum foco neste evento no dia de hoje
        focos_dia = [fc for fc in self.focos if fc.data.date() == data_obs.date()]
        delta_time_inicio = data_obs.date() - self.data_inicio.date()
        
        if len(focos_dia) == 0:
            if delta_time_inicio >= timedelta(days=1):
                self.status = STATUS_OBSERVACAO
        else:
            self.status = STATUS_ATIVO
        return self.status

    def atualizar_satelites_por_focos_state(self):
        """
        Gera uma lista de IDs únicos de satélites baseado nos focos atuais do evento.
        """
        # Extrai os IDs únicos dos focos associados
        self.id_satelites = list(set([fc.id_satelite for fc in self.focos]))
        return self.id_satelites

    def qnt_focos_state(self, data_obs):
        """
        Conta a quantidade de focos que ocorreram até a data_obs.
        """
        focos_ate_data = [fc for fc in self.focos if fc.data.date() <= data_obs.date()]
        self.qnt_focos = len(focos_ate_data)
        return self.qnt_focos

    def calcular_area_do_dia_state(self, data_obs):
        """
        Calcula a área dinâmica (diária) criando um buffer apenas sobre os focos que ocorreram na data alvo.
        ATENÇÃO: Deve ser chamado DEPOIS de atualizar_status().
        """

        # Decide qual data usar (se não teve foco no dia e tá ativo, recua pra última observação)
        focos_dia = [fc for fc in self.focos if fc.data.date() == data_obs.date()]
        data_alvo = data_obs
        
        if len(focos_dia) == 0 and getattr(self, 'status', None) in ["Ativo", "Observação", 1, 2]:
            if self.data_ultima_observacao:
                data_alvo = self.data_ultima_observacao                
        # Pega os focos apenas da data_alvo
        focos_alvo = [fc for fc in self.focos if fc.data.date() == data_alvo.date()]
        
        if not focos_alvo:
            self.geometria = GeometryCollection().wkt
            return 0.0
            
        wkts = [fc.ponto for fc in focos_alvo]
        raios = [satelite_raios_cache.get(fc.id_satelite, float(config_keys.get("raio_buffer"))) for fc in focos_alvo]
        
        # Carrega todas as geometrias do WKT nativamente em C (Shapely 2.0)
        geoms = shapely.from_wkt(wkts)
        # Extrai todas as coordenadas (array Nx2) e transforma via PyProj em lote
        coords = shapely.get_coordinates(geoms)
        x_novo, y_novo = project_to_5880_transform(coords[:, 0], coords[:, 1])
        # Recria as geometrias com as coordenadas reprojetadas
        geoms_5880 = shapely.set_coordinates(geoms, np.column_stack((x_novo, y_novo)))
        # Cria os buffers de forma vetorizada
        buffers = shapely.buffer(geoms_5880, raios, cap_style=3)
        
        # Faz a união espacial de todas as frentes (Dissolve)
        geometria_disolve_5880 = shapely.union_all(buffers)
        area_today = round(geometria_disolve_5880.area / 1_000_000, 2)
        
        # Pega as coordenadas do polígono final resultante (pode ser MultiPolygon)
        coords_dissolve = shapely.get_coordinates(geometria_disolve_5880)
        x_orig, y_orig = project_to_4326_transform(coords_dissolve[:, 0], coords_dissolve[:, 1])
        
        # Atualiza a geometria devolvendo para o EPSG:4326 nativamente
        geometria_disolve_4326 = shapely.set_coordinates(geometria_disolve_5880, np.column_stack((x_orig, y_orig)))
        self.geometria = geometria_disolve_4326.wkt
        
        return area_today

    def injetar_focos_ate_data(self, list_focos, data_obs):
        """ Filtra a lista de focos até a data_obs e os injeta no evento """
        self.focos = [fc for fc in list_focos if fc.data.date() <= data_obs.date()]

    def injetar_historico_regioes(self, historico_regiao: list[dict]):
        """ Popula as instâncias de EventoRegiao a partir do dicionário retornado pela API """
        
        self.eventos_regioes = []
        if not historico_regiao:
            return
            
        for regiao in historico_regiao:
            nova_regiao = EventoRegiao(
                id_evento=self.id_evento,
                id_regiao=regiao[col_reg["id_regiao"]]
            )
            self.eventos_regioes.append(nova_regiao)
    
    def reverter_extincao_se_necessario(self, data_obs):
        """ Zera a data_fim e area_fim se a data de observação for anterior à declaração de extinção. """
        #Rever se vamos deixar o estado do evento como Extinto mesmo se data_obs for anterior à data_fim 
        #if data_obs.date() <= self.data_fim.date():
        if self.data_fim:
            if (data_obs.date() - self.data_fim.date()).days < 7:
                self.data_fim = None
                self.area_fim = None

    def reverter_fusionamento_se_necessario(self, data_obs):
        """ Limpa o id_evento_absorvedor se o evento foi fusionado após a observação atual """
        if self.data_fim and self.data_fim > data_obs and self.id_evento_absorvedor is not None:
            self.id_evento_absorvedor = None

    def filtrar_regioes_ate_data(self, data_obs, gdf_regioes=None):
        """ Retorna os IDs das regiões associadas ao evento. Sem filtro temporal, faz o intersect com a geometria do dia. """
        if gdf_regioes is not None and not gdf_regioes.empty and getattr(self, 'geometria', None):
            import shapely.wkt
            geom_evento = shapely.wkt.loads(self.geometria)
            intersected = gdf_regioes[gdf_regioes.intersects(geom_evento)]
            return intersected['nome_regiao'].tolist()
            
        if hasattr(self, 'eventos_regioes') and self.eventos_regioes:
            return [er.id_regiao for er in self.eventos_regioes]
        return []

    def obter_ids_focos_do_dia(self, data_obs):
        """ 
        Retorna os IDs dos focos que ocorreram no dia analisado.
        """
        lista_today = [f for f in self.focos if f.data.date() == data_obs.date()]
        return [fc.id_foco for fc in lista_today]
        
# ====================================================================================================================
