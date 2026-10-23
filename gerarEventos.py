import os
import sys
from datetime import datetime, timedelta, date
from typing import Union, Dict, List, Optional
import pandas as pd
import geopandas as gpd

# Configuração de paths para garantir importações do projeto
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELO_SRC = os.path.join(BASE_DIR, "modelo_evento_fogo_OO", "src")
SHARED_DIR = os.path.join(BASE_DIR, "shared")

for path in [BASE_DIR, MODELO_SRC, SHARED_DIR]:
    if path not in sys.path:
        sys.path.insert(0, path)

from shared.config import config_keys
from evento_fogo.integracao.integrador import integrar_eventos as integrador

# Satélites geoestacionários GOES com resolução espacial mais ampla
SATELITES_GOES_PADRAO = ["GOES-13", "GOES-16", "GOES-19", "GOES-12", "GOES-08", "GOES-10"]


def changeRaio(
    raioAG: Union[float, int, Dict[Union[str, int], float]],
    satelites: Optional[List[Union[str, int]]] = None
) -> Dict[Union[str, int], float]:
    """
    Atualiza os raios de buffer dos satélites diretamente em memória.

    Args:
        raioAG: Valor numérico (aplicado aos satélites alvo, por padrão GOES)
                OU dicionário mapeando nome ou ID do satélite para o raio (ex: {"GOES-16": 1200}).
        satelites: Lista de satélites a atualizar quando raioAG for numérico.
                   Se None, usa SATELITES_GOES_PADRAO.

    Returns:
        Dicionário buffer_por_satelite mapeando {id_satelite: raio, nome_satelite: raio}.
    """
    if satelites is None:
        satelites = SATELITES_GOES_PADRAO

    buffer_dict: Dict[Union[str, int], float] = {}

    for sat in config_keys.get("satelite_data", []):
        id_sat = sat.get("id_satelite")
        nome_sat = sat.get("satelite")

        if isinstance(raioAG, dict):
            if nome_sat in raioAG:
                sat["raio"] = float(raioAG[nome_sat])
            elif id_sat in raioAG:
                sat["raio"] = float(raioAG[id_sat])
            elif str(id_sat) in raioAG:
                sat["raio"] = float(raioAG[str(id_sat)])
        else:
            if nome_sat in satelites or id_sat in satelites or str(id_sat) in satelites:
                sat["raio"] = float(raioAG)

        raio_atual = float(sat.get("raio", 1000.0))
        if id_sat is not None:
            buffer_dict[id_sat] = raio_atual
        if nome_sat:
            buffer_dict[nome_sat] = raio_atual

    return buffer_dict


def process(
    focos: Union[gpd.GeoDataFrame],
    eventos: Optional[gpd.GeoDataFrame] = None,
    buffer_por_satelite: Optional[Dict] = None
) -> gpd.GeoDataFrame:
    """
    Invoca o motor OO integrador diretamente em memória sem passar por camada HTTP.
    """
    return integrador(
        focos_dia_geojson=focos,
        gdf_banco=eventos,
        buffer_por_satelite=buffer_por_satelite
    )


def executarProcessamento(
    data_inicio: Union[str, datetime, date],
    data_fim: Union[str, datetime, date],
    raio: Union[float, int, Dict[Union[str, int], float]],
    gdf_focos: Optional[Union[str, gpd.GeoDataFrame]] = None,
    satelites_alvo: Optional[List[Union[str, int]]] = None,
    retornar_crs_4326: bool = True
) -> gpd.GeoDataFrame:
    """
    Executa o processamento do modelo de eventos dia a dia para um determinado período para ser chamado repetidamente a cada iteração de um Algoritmo Genético (AG).

    Args:
        data_inicio: Data inicial ("YYYY-MM-DD" ou date/datetime)
        data_fim: Data final ("YYYY-MM-DD" ou date/datetime)
        raio: Raio ou dicionário de raios gerado pelo AG para esta iteração
        gdf_focos: Caminho para o GeoJSON ou GeoDataFrame de focos já carregado
        satelites_alvo: Lista de satélites cujo raio será alterado (se raio for numérico)
        retornar_crs_4326: Se True, converte o resultado final para EPSG:4326 (padrão GeoJSON)

    Returns:
        GeoDataFrame contendo todos os eventos gerados/fusionados no período.
    """
    # 1. Atualizar o raio em memória para o AG
    buffer_dict = changeRaio(raio, satelites=satelites_alvo)

    # 2. Tratar datas
    if isinstance(data_inicio, str):
        data_ini = datetime.fromisoformat(data_inicio).date()
    elif isinstance(data_inicio, datetime):
        data_ini = data_inicio.date()
    else:
        data_ini = data_inicio

    if isinstance(data_fim, str):
        data_end = datetime.fromisoformat(data_fim).date()
    elif isinstance(data_fim, datetime):
        data_end = data_fim.date()
    else:
        data_end = data_fim

    if data_ini > data_end:
        raise ValueError(f"data_inicio ({data_ini}) não pode ser maior que data_fim ({data_end})")

    # Tratar focos
    if gdf_focos is None:
        caminho_pantanal = os.path.join(BASE_DIR, "focosPantanal040824040924.geojson")
        if os.path.exists(caminho_pantanal):
            gdf_focos = gpd.read_file(caminho_pantanal)
        else:
            raise ValueError("GeoDataFrame ou caminho de focos não fornecido para executarProcessamento.")
    elif isinstance(gdf_focos, str):
        gdf_focos = gpd.read_file(gdf_focos)

    # Loop espaço-temporal diário
    delta = (data_end - data_ini).days
    list_days = [data_ini + timedelta(days=i) for i in range(delta + 1)]

    todos_eventos: Dict[int, dict] = {}
    proximo_id_evento: int = 1

    for data_atual in list_days:
        # Filtro de focos do dia por data
        focos_day = gdf_focos[gdf_focos["data"].dt.date == data_atual].copy()
        
        if focos_day.empty:  # Se não houver focos no dia, avança para o próximo
            continue

        # Preparar banco de eventos candidatos dos últimos 7 dias 
        banco_input: Optional[gpd.GeoDataFrame] = None
        data_limite_7d = data_atual - timedelta(days=7)

        eventos_candidatos = [
            ev for ev in todos_eventos.values()
            if (
                # Não é um evento absorvido/fusionado
                (ev.get("id_evento_absorvedor") is None or pd.isna(ev.get("id_evento_absorvedor")))
                # Evento ainda ativo (sem data_fim) ou encerrado na janela recente
                and (ev.get("data_fim") is None or pd.isna(ev.get("data_fim")) or (ev.get("data_fim").date() if hasattr(ev.get("data_fim"), "date") else pd.to_datetime(ev.get("data_fim")).date()) >= data_limite_7d)
                # Teve última observação nos últimos 7 dias
                and (ev.get("data_ultima_observacao") is not None and (ev.get("data_ultima_observacao").date() if hasattr(ev.get("data_ultima_observacao"), "date") else pd.to_datetime(ev.get("data_ultima_observacao")).date()) >= data_limite_7d)
            )
        ]

        if eventos_candidatos:
            banco_input = gpd.GeoDataFrame(eventos_candidatos, geometry="geometry", crs="EPSG:5880")

        # Execução direta do modelo de eventos em memória
        eventos_processados = process(
            focos=focos_day,
            eventos=banco_input,
            buffer_por_satelite=buffer_dict
        )

        if eventos_processados is None or eventos_processados.empty:
            continue

        # Novos eventos criados no dia vêm com id_evento = NaN/None
        # Atribuir identificadores únicos incrementais em memória
        novos_idx = eventos_processados[eventos_processados["id_evento"].isna()].index
        for idx in novos_idx:
            eventos_processados.at[idx, "id_evento"] = proximo_id_evento
            proximo_id_evento += 1

        # Atualizar nosso repositório de eventos em memória
        for _, row in eventos_processados.iterrows():
            id_ev = int(row["id_evento"])
            todos_eventos[id_ev] = row.to_dict()


    # 5. Consolidar GeoDataFrame final com todos os eventos
    if not todos_eventos:
        return gpd.GeoDataFrame(crs="EPSG:4326" if retornar_crs_4326 else "EPSG:5880")

    gdf_resultado = gpd.GeoDataFrame(list(todos_eventos.values()), geometry="geometry", crs="EPSG:5880")

    if retornar_crs_4326:
        gdf_resultado = gdf_resultado.to_crs(epsg=4326)

    return gdf_resultado


class OtimizadorEventosAG:
    """
    Classe utilitária para acoplamento direto com Algoritmos Genéticos (AG / PyMoo / DEAP / SciPy).
    Carrega o GeoJSON de focos uma única vez e expõe um método de avaliação rápido.
    """
    def __init__(self, caminho_ou_gdf_focos: Union[str, gpd.GeoDataFrame]):
        if isinstance(caminho_ou_gdf_focos, str):
            self.gdf_focos = gpd.read_file(caminho_ou_gdf_focos)
        else:
            self.gdf_focos = caminho_ou_gdf_focos.copy()
        self.data_min = self.gdf_focos["data"].min().date() if not self.gdf_focos.empty else None
        self.data_max = self.gdf_focos["data"].max().date() if not self.gdf_focos.empty else None

    def avaliar(
        self,
        raio: Union[float, int, Dict[Union[str, int], float]],
        data_inicio: Optional[Union[str, date]] = None,
        data_fim: Optional[Union[str, date]] = None,
        retornar_crs_4326: bool = True
    ) -> gpd.GeoDataFrame:
        """
        Executa uma iteração do AG com o candidato a raio fornecido.
        """
        d_ini = data_inicio or self.data_min
        d_fim = data_fim or self.data_max
        return executarProcessamento(
            data_inicio=d_ini,
            data_fim=d_fim,
            raio=raio,
            gdf_focos=self.gdf_focos,
            retornar_crs_4326=retornar_crs_4326
        )

    def calcular_iou(
        self,
        gdf_eventos: gpd.GeoDataFrame,
        gdf_referencia: gpd.GeoDataFrame
    ) -> float:
        """
        Calcula o Intersection-over-Union (IoU) entre a área dos eventos gerados
        e os polígonos de referência (ex: NBR de Sentinel-2).
        Pode ser usada como função de aptidão (fitness function) no AG.
        """
        num_eventos = len(gdf_eventos)
        
        if gdf_eventos.empty or gdf_referencia.empty:
            return 0.0, num_eventos

        # Alinhar CRS para métrico
        ev_5880 = gdf_eventos.to_crs(epsg=5880)
        ref_5880 = gdf_referencia.to_crs(epsg=5880)

        uniao_eventos = ev_5880.unary_union
        uniao_referencia = ref_5880.unary_union

        intersecao = uniao_eventos.intersection(uniao_referencia).area
        uniao_total = uniao_eventos.union(uniao_referencia).area

        return float(intersecao / uniao_total) if uniao_total > 0 else 0.0, num_eventos
