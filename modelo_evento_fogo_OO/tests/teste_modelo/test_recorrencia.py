from pathlib import Path
import sys
import geopandas as gpd
import pandas as pd
import pytest


path_share = Path(__file__).parent.parent.parent.parent
sys.path.append(str(path_share))

from shared.models.evento import Eventos




from evento_fogo.processamento.analisar_recorrencia import (
    analisar_recorrencia,
    eventos_para_gdf,
    selecionar_eventos_alvo,
)


CAMINHO_GEOJSON = (
    Path(__file__).parent.parent
    / "dados"
    / "eventos_teste_recorrencia.geojson"
)


# ==========================================================
# Auxiliares para criar a massa de Eventos
# ==========================================================

def valor_ou_none(valor):
    if valor is None:
        return None

    try:
        if pd.isna(valor):
            return None
    except (TypeError, ValueError):
        pass

    return valor


def converter_data(valor):
    valor = valor_ou_none(valor)

    if valor is None:
        return None

    return pd.Timestamp(
        valor
    ).to_pydatetime()


def converter_duracao(valor):
    valor = valor_ou_none(valor)

    if valor is None:
        return None

    return pd.to_timedelta(
        valor
    ).to_pytimedelta()


def normalizar_predecessores(valor):
    if isinstance(
        valor,
        (list, tuple, set),
    ):
        return [
            int(id_evento)
            for id_evento in valor
        ]

    return []


def criar_lista_eventos(
    caminho_geojson=CAMINHO_GEOJSON,
):
    gdf = gpd.read_file(
        caminho_geojson
    )

    eventos_por_id = {}

    # Primeira passagem:
    # instancia todos os Eventos.
    for _, linha in gdf.iterrows():

        recorrencia = valor_ou_none(
            linha["recorrencia"]
        )

        quantidade_focos = valor_ou_none(
            linha["quantidade_focos"]
        )

        evento = Eventos(
            id_evento=int(
                linha["id_evento"]
            ),

            # Não é necessário reconstruir os focos para
            # o processamento de recorrência.
            focos=[],

            geometria=linha.geometry,

            data_inicio=converter_data(
                linha["data_inicio"]
            ),

            data_ultima_observacao=converter_data(
                linha["data_ultima_observacao"]
            ),

            data_fim=converter_data(
                linha["data_fim"]
            ),

            area_inicio=valor_ou_none(
                linha["area_inicio"]
            ),

            area_fim=valor_ou_none(
                linha["area_fim"]
            ),

            status=valor_ou_none(
                linha["status"]
            ),

            id_evento_absorvedor=valor_ou_none(
                linha["id_evento_absorvedor"]
            ),

            persistencia=valor_ou_none(
                linha["persistencia"]
            ),

            recorrencia=(
                int(recorrencia)
                if recorrencia is not None
                else 0
            ),

            duracao=converter_duracao(
                linha["duracao"]
            ),

            qnt_focos=(
                int(quantidade_focos)
                if quantidade_focos is not None
                else 0
            ),
        )

        evento.descricao = valor_ou_none(
            linha["descricao"]
        )

        eventos_por_id[
            evento.id_evento
        ] = evento

    # Segunda passagem:
    # reconstrói a relationship de predecessores.
    for _, linha in gdf.iterrows():

        evento = eventos_por_id[
            int(linha["id_evento"])
        ]

        ids_predecessores = (
            normalizar_predecessores(
                linha["predecessores"]
            )
        )

        evento.predecessores = [
            eventos_por_id[id_predecessor]
            for id_predecessor in ids_predecessores
            if id_predecessor in eventos_por_id
        ]

    return list(
        eventos_por_id.values()
    )


def obter_evento(
    eventos,
    id_evento,
):
    return next(
        evento
        for evento in eventos
        if evento.id_evento == id_evento
    )


def obter_ids_predecessores(
    evento,
):
    return {
        predecessor.id_evento
        for predecessor in evento.predecessores
    }


# ==========================================================
# Fixture
# ==========================================================

@pytest.fixture
def eventos():
    # Cada teste recebe novos objetos porque o analisador
    # altera os Eventos em memória.
    return criar_lista_eventos()


# ==========================================================
# Conversão para GeoDataFrame
# ==========================================================

def test_eventos_para_gdf_preserva_referencia_dos_objetos(
    eventos,
):
    gdf = eventos_para_gdf(
        eventos
    )

    assert len(gdf) == len(eventos)

    assert (
        gdf.iloc[0]["_evento"]
        is eventos[0]
    )

    assert gdf.crs.to_string() == "EPSG:4326"


def test_selecionar_eventos_alvo_considera_mes_anterior(
    eventos,
):
    gdf = eventos_para_gdf(
        eventos
    )

    alvos = selecionar_eventos_alvo(
        gdf,
        data_analise="2024-02-01",
    )

    assert set(
        alvos["id_evento"]
    ) == {
        43,
        62,
    }

    assert (
        alvos["data_inicio"]
        >= pd.Timestamp("2024-01-01")
    ).all()

    assert (
        alvos["data_inicio"]
        < pd.Timestamp("2024-02-01")
    ).all()


# ==========================================================
# Recorrência simples
# ==========================================================

def test_analisar_recorrencia_identifica_um_predecessor(
    eventos,
):
    evento_62 = obter_evento(
        eventos,
        62,
    )

    resultado = analisar_recorrencia(
        eventos=eventos,
        data_analise="2024-02-01",
        janela_operacional_dias=7,
        horizonte_anos=2,
    )

    # A função modifica os objetos em memória.
    assert resultado is None

    assert evento_62.recorrencia == 1

    assert obter_ids_predecessores(
        evento_62
    ) == {
        43,
    }


# ==========================================================
# Múltiplos predecessores
# ==========================================================

def test_analisar_recorrencia_identifica_multiplos_predecessores(
    eventos,
):
    evento_86 = obter_evento(
        eventos,
        86,
    )

    analisar_recorrencia(
        eventos=eventos,
        data_analise="2024-03-01",
    )

    assert evento_86.recorrencia == 2

    assert obter_ids_predecessores(
        evento_86
    ) == {
        43,
        62,
    }


# ==========================================================
# Idempotência
# ==========================================================

def test_analisar_recorrencia_nao_duplica_predecessores(
    eventos,
):
    evento_62 = obter_evento(
        eventos,
        62,
    )

    analisar_recorrencia(
        eventos=eventos,
        data_analise="2024-02-01",
    )

    analisar_recorrencia(
        eventos=eventos,
        data_analise="2024-02-01",
    )

    assert evento_62.recorrencia == 1

    assert obter_ids_predecessores(
        evento_62
    ) == {
        43,
    }

    assert len(
        evento_62.predecessores
    ) == 1


# ==========================================================
# Preservação de predecessores já existentes
# ==========================================================

def test_analisar_recorrencia_preserva_predecessor_existente_e_adiciona_novo(
    eventos,
):
    evento_43 = obter_evento(
        eventos,
        43,
    )

    evento_86 = obter_evento(
        eventos,
        86,
    )

    # Simula estado previamente persistido.
    evento_86.predecessores = [
        evento_43
    ]
    evento_86.recorrencia = 1

    analisar_recorrencia(
        eventos=eventos,
        data_analise="2024-03-01",
    )

    assert evento_86.recorrencia == 2

    assert obter_ids_predecessores(
        evento_86
    ) == {
        43,
        62,
    }


# ==========================================================
# Janela operacional de sete dias
# ==========================================================

def test_analisar_recorrencia_nao_considera_evento_no_limite_de_sete_dias(
    eventos,
):
    evento_992 = obter_evento(
        eventos,
        992,
    )

    # 753 termina em 25/08.
    # 992 inicia em 01/09.
    # Diferença exata de 7 dias:
    # ainda pertence à janela operacional.
    analisar_recorrencia(
        eventos=eventos,
        data_analise="2024-10-01",
        janela_operacional_dias=7,
    )

    assert 753 not in obter_ids_predecessores(
        evento_992
    )


# ==========================================================
# Evento sem recorrência
# ==========================================================

def test_analisar_recorrencia_mantem_evento_sem_predecessores(
    eventos,
):
    evento_974 = obter_evento(
        eventos,
        974,
    )

    analisar_recorrencia(
        eventos=eventos,
        data_analise="2024-09-01",
    )

    assert evento_974.recorrencia == 0

    assert obter_ids_predecessores(
        evento_974
    ) == set()


# ==========================================================
# Horizonte histórico de dois anos
# ==========================================================

def test_analisar_recorrencia_ignora_predecessor_fora_do_horizonte_de_dois_anos(
    eventos,
):
    evento_43 = obter_evento(
        eventos,
        43,
    )

    evento_62 = obter_evento(
        eventos,
        62,
    )

    # Mantemos a geometria real do evento 43,
    # alterando somente seu período para colocá-lo
    # fora do horizonte histórico do evento 62.
    evento_43.data_inicio = (
        pd.Timestamp("2021-01-09")
        .to_pydatetime()
    )

    evento_43.data_ultima_observacao = (
        pd.Timestamp("2021-01-09")
        .to_pydatetime()
    )

    evento_43.data_fim = (
        pd.Timestamp("2021-01-09")
        .to_pydatetime()
    )

    analisar_recorrencia(
        eventos=eventos,
        data_analise="2024-02-01",
        horizonte_anos=2,
    )

    assert evento_62.recorrencia == 0

    assert 43 not in obter_ids_predecessores(
        evento_62
    )


# ==========================================================
# Entrada vazia
# ==========================================================

def test_analisar_recorrencia_aceita_lista_vazia():
    resultado = analisar_recorrencia(
        eventos=[],
        data_analise="2024-02-01",
    )

    assert resultado is None