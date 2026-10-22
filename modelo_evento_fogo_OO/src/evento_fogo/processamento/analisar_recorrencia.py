
import geopandas as gpd
import pandas as pd

from shared.models.evento import Eventos


def eventos_para_gdf(
    eventos: list[Eventos],
    crs: str = "EPSG:4326",
) -> gpd.GeoDataFrame:

    if not eventos:
        return gpd.GeoDataFrame(
            {
                "_evento": [],
                "id_evento": [],
                "data_inicio": [],
                "data_fim": [],
                "data_ultima_observacao": [],
                "recorrencia": [],
                "_ids_predecessores": [],
                "geometry": [],
            },
            geometry="geometry",
            crs=crs,
        )

    registros = [
        {
            "_evento": evento,
            "id_evento": evento.id_evento,
            "data_inicio": evento.data_inicio,
            "data_fim": evento.data_fim,
            "data_ultima_observacao": evento.data_ultima_observacao,
            "recorrencia": (
                evento.recorrencia
                if evento.recorrencia is not None
                else 0
            ),
            "_ids_predecessores": [
                predecessor.id_evento
                for predecessor in evento.predecessores
            ],
            "geometry": evento.geom,
        }
        for evento in eventos
    ]

    return gpd.GeoDataFrame(
        registros,
        geometry="geometry",
        crs=crs,
    )

def selecionar_eventos_alvo(
    gdf: gpd.GeoDataFrame,
    data_analise,
) -> gpd.GeoDataFrame:

    data_analise = pd.Timestamp(
        data_analise
    )

    inicio_periodo = (
        data_analise
        - pd.DateOffset(months=1)
    )

    mascara = (
        gdf["data_inicio"].ge(inicio_periodo)
        & gdf["data_inicio"].lt(data_analise)
    )

    return gdf.loc[mascara].copy()


def obter_fim_referencia(
    evento: pd.Series,
) -> pd.Timestamp:

    if pd.notna(evento["data_fim"]):
        return pd.Timestamp(
            evento["data_fim"]
        )

    return pd.Timestamp(
        evento["data_ultima_observacao"]
    )

def eh_predecessor_recorrente(
    alvo: pd.Series,
    candidato: pd.Series,
    janela_operacional_dias: int = 7,
    horizonte_anos: int = 2,
) -> bool:

    if candidato["id_evento"] == alvo["id_evento"]:
        return False

    data_inicio_alvo = pd.Timestamp(
        alvo["data_inicio"]
    )

    data_inicio_candidato = pd.Timestamp(
        candidato["data_inicio"]
    )

    # Precisa ser anterior ao alvo
    if data_inicio_candidato >= data_inicio_alvo:
        return False

    # Precisa estar dentro do horizonte histórico
    limite_historico = (
        data_inicio_alvo
        - pd.DateOffset(years=horizonte_anos)
    )

    if data_inicio_candidato < limite_historico:
        return False

    # Precisa estar fora da janela operacional
    fim_candidato = obter_fim_referencia(
        candidato
    )

    limite_operacional = (
        data_inicio_alvo
        - pd.Timedelta(
            days=janela_operacional_dias
        )
    )

    if fim_candidato >= limite_operacional:
        return False

    # Confirmação espacial
    return alvo.geometry.intersects(
        candidato.geometry
    )


def identificar_predecessores(
    gdf: gpd.GeoDataFrame,
    alvo: pd.Series,
    indice_espacial,
    janela_operacional_dias: int = 7,
    horizonte_anos: int = 2,
) -> list[int]:

    ids_predecessores = []

    indices_candidatos = indice_espacial.query(
        alvo.geometry
    )

    for indice_candidato in indices_candidatos:

        candidato = gdf.iloc[
            indice_candidato
        ]

        if not eh_predecessor_recorrente(
            alvo=alvo,
            candidato=candidato,
            janela_operacional_dias=janela_operacional_dias,
            horizonte_anos=horizonte_anos,
        ):
            continue

        ids_predecessores.append(
            int(candidato["id_evento"])
        )

    return sorted(ids_predecessores)



def atualizar_recorrencia_no_gdf(
    gdf: gpd.GeoDataFrame,
    indice_alvo: int,
    ids_predecessores_detectados: list[int],
) -> bool:

    ids_existentes = set(
        gdf.at[
            indice_alvo,
            "_ids_predecessores",
        ]
    )

    quantidade_inicial = len(
        ids_existentes
    )

    ids_existentes.update(
        ids_predecessores_detectados
    )

    if len(ids_existentes) == quantidade_inicial:
        return False

    ids_atualizados = sorted(
        ids_existentes
    )

    gdf.at[
        indice_alvo,
        "_ids_predecessores",
    ] = ids_atualizados

    gdf.at[
        indice_alvo,
        "recorrencia",
    ] = len(ids_atualizados)

    return True


def processar_recorrencias_no_gdf(
    gdf: gpd.GeoDataFrame,
    gdf_alvos: gpd.GeoDataFrame,
    janela_operacional_dias: int = 7,
    horizonte_anos: int = 2,
) -> list[int]:

    indice_espacial = gdf.sindex
    indices_atualizados = []

    for indice_alvo, alvo in gdf_alvos.iterrows():

        ids_predecessores_detectados = (
            identificar_predecessores(
                gdf=gdf,
                alvo=alvo,
                indice_espacial=indice_espacial,
                janela_operacional_dias=janela_operacional_dias,
                horizonte_anos=horizonte_anos,
            )
        )

        if not ids_predecessores_detectados:
            continue

        alterou = atualizar_recorrencia_no_gdf(
            gdf=gdf,
            indice_alvo=indice_alvo,
            ids_predecessores_detectados=ids_predecessores_detectados,
        )

        if alterou:
            indices_atualizados.append(
                indice_alvo
            )

    return indices_atualizados


def aplicar_recorrencias_nos_eventos(
    gdf: gpd.GeoDataFrame,
    indices_atualizados: list[int],
) -> None:

    eventos_por_id = {
        int(linha["id_evento"]): linha["_evento"]
        for _, linha in gdf.iterrows()
    }

    for indice in indices_atualizados:
        linha = gdf.loc[indice]

        evento = linha["_evento"]

        ids_predecessores = linha[
            "_ids_predecessores"
        ]

        evento.predecessores = [
            eventos_por_id[id_predecessor]
            for id_predecessor in ids_predecessores
            if id_predecessor in eventos_por_id
        ]

        evento.recorrencia = len(
            evento.predecessores
        )

#----------------------------------------------------------------
# Função pública de orquestração
#---------------------------------------------------------------

def analisar_recorrencia(
    eventos: list[Eventos],
    data_analise,
    janela_operacional_dias: int = 7,
    horizonte_anos: int = 2,
) -> None:

    if not eventos:
        return

    data_analise = pd.Timestamp(
        data_analise
    )

    gdf_eventos = eventos_para_gdf(
        eventos
    )

    if gdf_eventos.empty:
        return

    gdf_alvos = selecionar_eventos_alvo(
        gdf_eventos,
        data_analise=data_analise,
    )

    if gdf_alvos.empty:
        return

    indices_atualizados = (
        processar_recorrencias_no_gdf(
            gdf=gdf_eventos,
            gdf_alvos=gdf_alvos,
            janela_operacional_dias=janela_operacional_dias,
            horizonte_anos=horizonte_anos,
        )
    )

    if not indices_atualizados:
        return

    aplicar_recorrencias_nos_eventos(
        gdf=gdf_eventos,
        indices_atualizados=indices_atualizados,
    )