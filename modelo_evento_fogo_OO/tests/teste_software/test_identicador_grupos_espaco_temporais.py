import geopandas as gpd
import pytest
from shapely.geometry import box

from evento_fogo.processamento.identificacao_grupos_espaco_temporais import (
    IdentificadorGruposEspacoTemporais,
)


def criar_gdf(registros, crs="EPSG:5880"):
    return gpd.GeoDataFrame(
        registros,
        geometry="geometry",
        crs=crs,
    )


def test_identificar_grupos_retorna_lista_vazia_quando_entrada_esta_vazia():
    gdf = gpd.GeoDataFrame(
        {
            "_evento": [],
            "data_ultima_observacao": [],
            "geometry": [],
        },
        geometry="geometry",
        crs="EPSG:5880",
    )

    identificador = IdentificadorGruposEspacoTemporais()

    grupos = identificador.identificar_grupos(gdf)

    assert grupos == []


def test_identificar_grupos_rejeita_entrada_sem_colunas_obrigatorias():
    gdf = criar_gdf(
        [
            {
                "_evento": object(),
                "geometry": box(0, 0, 10, 10),
            }
        ]
    )

    identificador = IdentificadorGruposEspacoTemporais()

    with pytest.raises(
        ValueError,
        match="Faltam as colunas necessárias",
    ):
        identificador.identificar_grupos(gdf)


def test_identificar_grupos_remove_registros_invalidos():
    evento_valido = object()

    gdf = criar_gdf(
        [
            {
                "_evento": evento_valido,
                "data_ultima_observacao": "2024-08-01",
                "geometry": box(0, 0, 10, 10),
            },
            {
                "_evento": None,
                "data_ultima_observacao": "2024-08-01",
                "geometry": box(0, 0, 10, 10),
            },
            {
                "_evento": object(),
                "data_ultima_observacao": "data-invalida",
                "geometry": box(0, 0, 10, 10),
            },
            {
                "_evento": object(),
                "data_ultima_observacao": "2024-08-01",
                "geometry": None,
            },
        ]
    )

    identificador = IdentificadorGruposEspacoTemporais()

    grupos = identificador.identificar_grupos(gdf)

    assert grupos == [[evento_valido]]


def test_identificar_grupos_agrupa_eventos_conectados_no_espaco_e_no_tempo():
    evento_1 = object()
    evento_2 = object()

    gdf = criar_gdf(
        [
            {
                "_evento": evento_1,
                "data_ultima_observacao": "2024-08-08",
                "geometry": box(0, 0, 10, 10),
            },
            {
                "_evento": evento_2,
                "data_ultima_observacao": "2024-08-03",
                "geometry": box(5, 0, 15, 10),
            },
        ]
    )

    grupos = IdentificadorGruposEspacoTemporais(
        intervalo_dias=7
    ).identificar_grupos(gdf)

    assert len(grupos) == 1
    assert len(grupos[0]) == 2
    assert set(grupos[0]) == {
        evento_1,
        evento_2,
    }


def test_identificar_grupos_separa_eventos_fora_do_intervalo_temporal():
    evento_1 = object()
    evento_2 = object()

    geometria = box(0, 0, 10, 10)

    gdf = criar_gdf(
        [
            {
                "_evento": evento_1,
                "data_ultima_observacao": "2024-08-10",
                "geometry": geometria,
            },
            {
                "_evento": evento_2,
                "data_ultima_observacao": "2024-08-02",
                "geometry": geometria,
            },
        ]
    )

    grupos = IdentificadorGruposEspacoTemporais(
        intervalo_dias=7
    ).identificar_grupos(gdf)

    assert len(grupos) == 2

    eventos_retornados = {
        grupo[0]
        for grupo in grupos
    }

    assert eventos_retornados == {
        evento_1,
        evento_2,
    }


def test_identificar_grupos_separa_eventos_sem_intersecao_espacial():
    evento_1 = object()
    evento_2 = object()

    gdf = criar_gdf(
        [
            {
                "_evento": evento_1,
                "data_ultima_observacao": "2024-08-08",
                "geometry": box(0, 0, 10, 10),
            },
            {
                "_evento": evento_2,
                "data_ultima_observacao": "2024-08-03",
                "geometry": box(20, 0, 30, 10),
            },
        ]
    )

    grupos = IdentificadorGruposEspacoTemporais(
        intervalo_dias=7
    ).identificar_grupos(gdf)

    assert len(grupos) == 2

    eventos_retornados = {
        grupo[0]
        for grupo in grupos
    }

    assert eventos_retornados == {
        evento_1,
        evento_2,
    }


def test_identificar_grupos_inclui_eventos_no_limite_do_intervalo_temporal():
    evento_1 = object()
    evento_2 = object()

    geo = box(0, 0, 10, 10)

    gdf = criar_gdf(
        [
            {
                "_evento": evento_1,
                "data_ultima_observacao": "2024-08-08",
                "geometry": geo,
            },
            {
                "_evento": evento_2,
                "data_ultima_observacao": "2024-08-01",
                "geometry": geo,
            },
        ]
    )

    grupos = IdentificadorGruposEspacoTemporais(
        intervalo_dias=7
    ).identificar_grupos(gdf)

    assert len(grupos) == 1
    assert set(grupos[0]) == {
        evento_1,
        evento_2,
    }


def test_identificar_grupos_considera_conectividade_espaco_temporal_transitiva():
    evento_a = object()
    evento_b = object()
    evento_c = object()

    gdf = criar_gdf(
        [
            {
                "_evento": evento_a,
                "data_ultima_observacao": "2024-08-11",
                "geometry": box(0, 0, 10, 10),
            },
            {
                "_evento": evento_b,
                "data_ultima_observacao": "2024-08-06",
                "geometry": box(8, 0, 18, 10),
            },
            {
                "_evento": evento_c,
                "data_ultima_observacao": "2024-08-01",
                "geometry": box(16, 0, 26, 10),
            },
        ]
    )

    grupos = IdentificadorGruposEspacoTemporais(
        intervalo_dias=7
    ).identificar_grupos(gdf)

    assert len(grupos) == 1
    assert len(grupos[0]) == 3
    assert set(grupos[0]) == {
        evento_a,
        evento_b,
        evento_c,
    }

