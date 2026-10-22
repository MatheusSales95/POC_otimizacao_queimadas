import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import box

from evento_fogo.processamento.identificacao_grupos_espaciais import (
    IdentificadorGruposEspaciais,
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
            "_foco": [],
            "data": [],
            "geometry": [],
        },
        geometry="geometry",
        crs="EPSG:5880",
    )

    identificador = IdentificadorGruposEspaciais()

    grupos = identificador.identificar_grupos(gdf)

    assert grupos == []


def test_identificar_grupos_rejeita_entrada_sem_colunas_obrigatorias():
    gdf = criar_gdf(
        [
            {
                "_foco": object(),
                "geometry": box(0, 0, 10, 10),
            }
        ]
    )

    identificador = IdentificadorGruposEspaciais()

    with pytest.raises(
        ValueError,
        match="Faltam colunas necessárias",
    ):
        identificador.identificar_grupos(gdf)


def test_identificar_grupos_agrupa_geometrias_que_se_intersectam():
    data = pd.Timestamp("2024-08-01")

    foco_1 = object()
    foco_2 = object()

    gdf = criar_gdf(
        [
            {
                "_foco": foco_1,
                "data": data,
                "geometry": box(0, 0, 10, 10),
            },
            {
                "_foco": foco_2,
                "data": data,
                "geometry": box(5, 0, 15, 10),
            },
        ]
    )

    identificador = IdentificadorGruposEspaciais()

    grupos = identificador.identificar_grupos(gdf)

    assert len(grupos) == 1
    assert len(grupos[0]) == 2
    assert set(grupos[0]["_foco"]) == {
        foco_1,
        foco_2,
    }


def test_identificar_grupos_separa_geometrias_sem_conexao():
    data = pd.Timestamp("2024-08-01")

    foco_1 = object()
    foco_2 = object()

    gdf = criar_gdf(
        [
            {
                "_foco": foco_1,
                "data": data,
                "geometry": box(0, 0, 10, 10),
            },
            {
                "_foco": foco_2,
                "data": data,
                "geometry": box(20, 0, 30, 10),
            },
        ]
    )

    identificador = IdentificadorGruposEspaciais()

    grupos = identificador.identificar_grupos(gdf)

    assert len(grupos) == 2
    assert sorted(len(grupo) for grupo in grupos) == [1, 1]

    focos_retornados = {
        grupo.iloc[0]["_foco"]
        for grupo in grupos
    }

    assert focos_retornados == {
        foco_1,
        foco_2,
    }


def test_identificar_grupos_considera_conectividade_transitiva():
    data = pd.Timestamp("2024-08-01")

    foco_1 = object()
    foco_2 = object()
    foco_3 = object()

    gdf = criar_gdf(
        [
            {
                "_foco": foco_1,
                "data": data,
                "geometry": box(0, 0, 10, 10),
            },
            {
                "_foco": foco_2,
                "data": data,
                "geometry": box(8, 0, 18, 10),
            },
            {
                "_foco": foco_3,
                "data": data,
                "geometry": box(16, 0, 26, 10),
            },
        ]
    )

    identificador = IdentificadorGruposEspaciais()

    grupos = identificador.identificar_grupos(gdf)

    assert len(grupos) == 1
    assert len(grupos[0]) == 3
    assert set(grupos[0]["_foco"]) == {
        foco_1,
        foco_2,
        foco_3,
    }


def test_identificar_grupos_nao_conecta_geometrias_de_datas_diferentes():
    foco_1 = object()
    foco_2 = object()

    geometria = box(0, 0, 10, 10)

    gdf = criar_gdf(
        [
            {
                "_foco": foco_1,
                "data": pd.Timestamp("2024-08-01"),
                "geometry": geometria,
            },
            {
                "_foco": foco_2,
                "data": pd.Timestamp("2024-08-02"),
                "geometry": geometria,
            },
        ]
    )

    identificador = IdentificadorGruposEspaciais()

    grupos = identificador.identificar_grupos(gdf)

    assert len(grupos) == 2
    assert all(len(grupo) == 1 for grupo in grupos)

    datas = {
        grupo.iloc[0]["data"]
        for grupo in grupos
    }

    assert datas == {
        pd.Timestamp("2024-08-01"),
        pd.Timestamp("2024-08-02"),
    }


def test_identificar_grupos_preserva_dados_dos_focos():
    data = pd.Timestamp("2024-08-01")

    foco_1 = object()
    foco_2 = object()

    gdf = criar_gdf(
        [
            {
                "_foco": foco_1,
                "data": data,
                "satelite": 4,
                "valor_teste": 10,
                "geometry": box(0, 0, 10, 10),
            },
            {
                "_foco": foco_2,
                "data": data,
                "satelite": 17,
                "valor_teste": 20,
                "geometry": box(5, 0, 15, 10),
            },
        ]
    )

    identificador = IdentificadorGruposEspaciais()

    grupos = identificador.identificar_grupos(gdf)

    assert len(grupos) == 1

    grupo = grupos[0]

    assert list(grupo["_foco"]) == [
        foco_1,
        foco_2,
    ]

    assert list(grupo["satelite"]) == [
        4,
        17,
    ]

    assert list(grupo["valor_teste"]) == [
        10,
        20,
    ]

    assert "_componente_espacial" not in grupo.columns