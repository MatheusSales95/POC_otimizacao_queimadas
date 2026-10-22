import geopandas as gpd
import pandas as pd
from unittest.mock import Mock
from shapely.geometry import Point

from evento_fogo.mapeadores.mapeador_eventos import MapeadorEventos
from shared.models.evento import (
    Eventos as EventoFogo,
    STATUS_ATIVO,
    STATUS_OBSERVACAO,
    STATUS_EXTINTO,
)

from shared.models.focos import Focos as Foco

foco_1 = Foco(
    id_foco="foco_1",
    data=pd.Timestamp("2024-08-01"),
    geometria=Point(1, 1),
)

foco_2 = Foco(
    id_foco="foco_2",
    data=pd.Timestamp("2024-08-02"),
    geometria=Point(2, 2),
)

focos = [foco_1, foco_2]

def criar_evento_mock():
    evento = Mock(spec=EventoFogo)

    evento.id_evento = "evento_1"
    evento.focos = focos

    evento.data_inicio = pd.Timestamp(
        "2024-08-01"
    )
    evento.data_ultima_observacao = pd.Timestamp(
        "2024-08-03"
    )
    evento.data_fim = None

    evento.area_inicio = 100.0
    evento.area_fim = 250.0

    evento.status = STATUS_ATIVO

    evento.id_evento_absorvedor = None

    evento.geom = Point(100, 200)

    evento.persistencia = 3
    evento.recorrencia = 0
    evento.predecessores = []

    evento.obter_ids_focos.return_value = [
        "foco_1",
        "foco_2",
    ]

    evento.quantidade_focos.return_value = 2

    return evento


def test_mapear_para_processamento_temporal_mapeia_evento_corretamente():
    evento = criar_evento_mock()

    gdf = (
        MapeadorEventos()
        .mapear_lista_eventos_para_gdf_processamento_temporal(
            [evento]
        )
    )

    assert isinstance(gdf, gpd.GeoDataFrame)
    assert len(gdf) == 1

    linha = gdf.iloc[0]

    assert linha["id_evento"] == evento.id_evento
    assert linha["focos"] == evento.focos
    assert linha["data_inicio"] == evento.data_inicio
    assert (
        linha["data_ultima_observacao"]
        == evento.data_ultima_observacao
    )
    assert linha["data_fim"] is None
    assert linha["area_inicio"] == evento.area_inicio
    assert linha["area_fim"] == evento.area_fim
    assert linha["status"] == evento.status
    assert (
        linha["id_evento_absorvedor"]
        == evento.id_evento_absorvedor
    )
    assert linha["ids_focos"] == evento.obter_ids_focos()
    assert linha["persistencia"] == evento.persistencia
    assert linha.geometry.equals(evento.geom)


def test_mapear_para_processamento_temporal_inclui_referencia_ao_evento():
    evento = criar_evento_mock()

    gdf = (
        MapeadorEventos()
        .mapear_lista_eventos_para_gdf_processamento_temporal(
            [evento]
        )
    )

    assert "_evento" in gdf.columns
    assert gdf.iloc[0]["_evento"] is evento
    assert "quantidade_focos" not in gdf.columns


def test_mapear_eventos_finais_mapeia_evento_corretamente():
    evento = criar_evento_mock()

    gdf = (
        MapeadorEventos()
        .mapear_lista_eventos_finais_para_gdf(
            [evento]
        )
    )

    assert isinstance(gdf, gpd.GeoDataFrame)
    assert len(gdf) == 1

    linha = gdf.iloc[0]

    assert linha["id_evento"] == evento.id_evento
    assert linha["focos"] == evento.focos
    assert linha["data_inicio"] == evento.data_inicio
    assert (
        linha["data_ultima_observacao"]
        == evento.data_ultima_observacao
    )
    assert linha["data_fim"] is None
    assert linha["area_inicio"] == evento.area_inicio
    assert linha["area_fim"] == evento.area_fim
    assert linha["status"] == evento.status
    assert (
        linha["id_evento_absorvedor"]
        == evento.id_evento_absorvedor
    )
    assert linha["ids_focos"] == evento.obter_ids_focos()
    assert linha["persistencia"] == evento.persistencia
    assert linha.geometry.equals(evento.geom)


def test_mapear_eventos_finais_inclui_quantidade_focos_e_nao_referencia_evento():
    evento = criar_evento_mock()

    gdf = (
        MapeadorEventos()
        .mapear_lista_eventos_finais_para_gdf(
            [evento]
        )
    )

    assert "quantidade_focos" in gdf.columns
    assert gdf.iloc[0]["quantidade_focos"] == 2

    assert "_evento" not in gdf.columns


def test_mapeamentos_para_gdf_utilizam_crs_configurado():
    evento = criar_evento_mock()

    mapeador = MapeadorEventos(
        crs_saida="EPSG:4326",
    )

    gdf_temporal = (
        mapeador
        .mapear_lista_eventos_para_gdf_processamento_temporal(
            [evento]
        )
    )

    gdf_final = (
        mapeador
        .mapear_lista_eventos_finais_para_gdf(
            [evento]
        )
    )

    assert gdf_temporal.crs.to_string() == "EPSG:4326"
    assert gdf_final.crs.to_string() == "EPSG:4326"


def test_mapear_geojson_banco_mapeia_registro_para_evento_corretamente():
    focos = [foco_1, foco_2]

    geo = Point(100, 200)

    gdf = gpd.GeoDataFrame(
        [
            {
                "id_evento": "evento_1",
                "focos": focos,
                "ids_focos": [1, 2],
                "data_inicio": pd.Timestamp("2024-08-01"),
                "data_ultima_observacao": pd.Timestamp(
                    "2024-08-03"
                ),
                "data_fim": pd.Timestamp("2024-08-04"),
                "area_inicio": 100.0,
                "area_fim": 250.0,
                "status": "extinto",
                "id_evento_absorvedor": None,
                "persistencia": 3,
                "geometry": geo,
            }
        ],
        geometry="geometry",
        crs="EPSG:5880",
    )

    eventos = (
        MapeadorEventos()
        .mapear_geojson_banco_para_lista_eventos(gdf)
    )

    assert len(eventos) == 1

    evento = eventos[0]

    assert isinstance(evento, EventoFogo)
    assert evento.id_evento == "evento_1"
    assert evento.focos == focos
    assert evento.data_inicio == pd.Timestamp("2024-08-01")
    assert (
        evento.data_ultima_observacao
        == pd.Timestamp("2024-08-03")
    )
    assert evento.data_fim == pd.Timestamp("2024-08-04")
    assert evento.area_inicio == 100.0
    assert evento.area_fim == 250.0
    assert evento.status == "extinto"
    assert evento.id_evento_absorvedor is None
    assert evento.persistencia == 3
    assert evento.geom.equals(geo)


def test_mapear_geojson_banco_preserva_focos_e_permite_obter_ids():
    foco_1 = Foco(
        id_foco=1,
        data=pd.Timestamp("2024-08-01"),
        geometria=Point(1, 1),
    )

    foco_2 = Foco(
        id_foco=2,
        data=pd.Timestamp("2024-08-01"),
        geometria=Point(2, 2),
    )

    gdf = gpd.GeoDataFrame(
        [
            {
                "id_evento": 1,
                "focos": [foco_1, foco_2],
                "data_inicio": pd.Timestamp("2024-08-01"),
                "data_ultima_observacao": pd.Timestamp("2024-08-03"),
                "data_fim": None,
                "area_inicio": 100.0,
                "area_fim": 250.0,
                "status": STATUS_ATIVO,
                "id_evento_absorvedor": None,
                "persistencia": 3,
                "geometry": Point(100, 200),
            }
        ],
        geometry="geometry",
        crs="EPSG:5880",
    )

    evento = (
        MapeadorEventos()
        .mapear_geojson_banco_para_lista_eventos(gdf)[0]
    )

    assert evento.focos == [
        foco_1,
        foco_2,
    ]

    assert evento.obter_ids_focos() == [
        "1",
        "2",
    ]

def test_mapear_geojson_banco_converte_data_fim_nula_para_none():
    gdf = gpd.GeoDataFrame(
        [
            {
                "id_evento": "evento_1",
                "focos": [],
                "ids_focos": [],
                "data_inicio": pd.Timestamp("2024-08-01"),
                "data_ultima_observacao": pd.Timestamp(
                    "2024-08-03"
                ),
                "data_fim": pd.NaT,
                "area_inicio": 100.0,
                "area_fim": 250.0,
                "status": STATUS_ATIVO,
                "id_evento_absorvedor": None,
                "persistencia": 3,
                "geometry": Point(100, 200),
            }
        ],
        geometry="geometry",
        crs="EPSG:5880",
    )

    evento = (
        MapeadorEventos()
        .mapear_geojson_banco_para_lista_eventos(gdf)[0]
    )

    assert evento.data_fim is None