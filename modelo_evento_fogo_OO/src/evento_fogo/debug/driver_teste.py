#------------------------------------------------------------------------
# Driver de teste do módulo de agregação
#------------------------------------------------------------------------
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

import geopandas as gpd
import pandas as pd
from evento_fogo.integracao.integrador import integrar_eventos
from evento_fogo.mapeadores.mapeador_eventos import MapeadorEventos
from pandas.api.types import is_datetime64_any_dtype


caminho_focos = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'notebooks_dados', 'ETL_focos_goes_SP_2024_08.geojson'))
gdf_focos = gpd.read_file(caminho_focos)


# Leitura do arquivo geojson de focos SP-2024-08
# caminho_focos_01 ="dados/focos_artificiais_dia_01.geojson"
# caminho_focos_02 ="dados/focos_artificiais_dia_02.geojson"
# caminho_focos_03 ="dados/focos_artificiais_dia_03.geojson"
# caminho_focos_04 ="dados/focos_artificiais_dia_04.geojson"
# caminho_focos_05 ="dados/focos_artificiais_dia_05.geojson"
# caminho_focos_09 ="dados/focos_artificiais_dia_09.geojson"
# gdf_focos = (gpd.read_file(caminho_focos_01)).to_crs("EPSG:4326")
# gdf_focos_02 = (gpd.read_file(caminho_focos_02)).to_crs("EPSG:4326")
# gdf_focos_03 = (gpd.read_file(caminho_focos_03)).to_crs("EPSG:4326")
# gdf_focos_04 = (gpd.read_file(caminho_focos_04)).to_crs("EPSG:4326")
# gdf_focos_05 = (gpd.read_file(caminho_focos_05)).to_crs("EPSG:4326")
# gdf_focos_09 = (gpd.read_file(caminho_focos_09)).to_crs("EPSG:4326")

# lista = [gdf_focos_02,gdf_focos_03,gdf_focos_04,gdf_focos_05, gdf_focos_09]

# for gdf in lista:
#     gdf_focos = pd.concat([gdf_focos,gdf],ignore_index=True)
  
#------------------------------------------------------------------------
# Funçao para leitura e geração de lotes de focos diários
#------------------------------------------------------------------------
def gerar_lotes_diarios(gdf_focos):

    gdf = gdf_focos.copy()

    def ajustar_saida_para_geojson(gpd_eventos_int: gpd.GeoDataFrame) -> str:
        """
        Ajusta nomes de colunas, formato de datas e CRS final para EPSG:4326.
        Retorna uma string GeoJSON.
        """

        gdf = gpd_eventos_int.to_crs("EPSG:4326").copy()

        gdf["data"] = gdf["data"].dt.strftime("%Y-%m-%d %H:%M:%S")

        return gdf.to_json()

    def dividir_geodataframe_por_dia(gdf: gpd.GeoDataFrame, coluna_data: str) -> dict[str, gpd.GeoDataFrame]:
        """
        Divide um GeoDataFrame em vários GeoDataFrames separados por dia.

        Args:
            gdf: GeoDataFrame original
            coluna_data: Nome da coluna com datas (datetime64[ms])

        Returns:
            Dicionário com chave = data (string 'YYYY-MM-DD') e valor = GeoDataFrame do dia
        """

        # Garante que a coluna está no formato correto
        gdf[coluna_data] = pd.to_datetime(gdf[coluna_data])

        # Extrai apenas a data (sem hora) para agrupar
        gdf["_dia_temp"] = gdf[coluna_data].dt.normalize()

        gdfs_por_dia = {}

        for dia, grupo in gdf.groupby("_dia_temp"):
            chave = dia.strftime("%Y-%m-%d")
            gdfs_por_dia[chave] = grupo.drop(columns=["_dia_temp"]).reset_index(drop=True)
            
        # Remove a coluna temporária do GeoDataFrame original
        gdf.drop(columns=["_dia_temp"], inplace=True)

        return gdfs_por_dia


    # Dividir por dia
    gdfs_por_dia = dividir_geodataframe_por_dia(gdf, coluna_data="data")
    gdfs_por_dia_geojson=[]
    for data, gdf_dia in gdfs_por_dia.items():

        gdfs_por_dia_geojson.append((data, ajustar_saida_para_geojson(gdf_dia)))
    
    return gdfs_por_dia_geojson

#------------------------------------------------------------------------
# Função para gerar GDF (que simula o banco) vazio
#------------------------------------------------------------------------
def criar_gdf_eventos_vazio(
    crs: str = "EPSG:5880",
) -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        {
            "id_evento": pd.Series(dtype="Int64"),
            "focos": pd.Series(dtype="object"),
            "data_inicio": pd.Series(dtype="datetime64[ns]"),
            "data_ultima_observacao": pd.Series(dtype="datetime64[ns]"),
            "data_fim": pd.Series(dtype="datetime64[ns]"),
            "area_inicio": pd.Series(dtype="float64"),
            "area_fim": pd.Series(dtype="float64"),
            "status": pd.Series(dtype="Int64"),
            "id_evento_absorvedor": pd.Series(dtype="Int64"),
            "ids_focos": pd.Series(dtype="object"),
            "geometry": gpd.GeoSeries([], crs=crs),
            "quantidade_focos": pd.Series(dtype="Int64"),
            "persistencia":pd.Series(dtype="float64"),
        },
        geometry="geometry",
        crs=crs,
    )

#------------------------------------------------------------------------
# Função para atualizar banco e atribuir IDs aos eventos
#------------------------------------------------------------------------
def atribuir_ids_e_atualizar_banco(
    gdf_eventos_banco: gpd.GeoDataFrame,
    gdf_eventos_saida: gpd.GeoDataFrame,
    proximo_id_evento: int,
) -> tuple[gpd.GeoDataFrame, int]:
    """
    Atribui IDs aos eventos novos e atualiza o banco simulado.

    O banco e a saída do processamento devem estar no mesmo CRS operacional.
    """

    banco = gdf_eventos_banco.copy()
    saida = gdf_eventos_saida.copy()

    if saida.empty:
        return banco, proximo_id_evento

    if banco.crs is None:
        raise ValueError("O banco de eventos não possui CRS definido.")

    if saida.crs is None:
        raise ValueError("A saída do processamento não possui CRS definido.")

    if banco.crs != saida.crs:
        raise ValueError(
            "O banco e a saída do processamento devem possuir o mesmo CRS. "
            f"Banco: {banco.crs}; saída: {saida.crs}."
        )

    if "id_evento" not in saida.columns:
        raise ValueError(
            "A saída do processamento não possui a coluna 'id_evento'."
        )

    # Simula a atribuição de IDs pelo banco aos eventos novos.
    mascara_eventos_novos = saida["id_evento"].isna()

    for indice in saida.index[mascara_eventos_novos]:
        saida.at[indice, "id_evento"] = proximo_id_evento
        proximo_id_evento += 1

    saida["id_evento"] = saida["id_evento"].astype("Int64")

    # Impede que duas linhas da saída representem o mesmo evento.
    ids_duplicados = saida["id_evento"].duplicated(keep=False)

    if ids_duplicados.any():
        ids = (
            saida.loc[ids_duplicados, "id_evento"]
            .dropna()
            .unique()
            .tolist()
        )

        raise ValueError(
            f"A saída possui IDs de eventos duplicados: {ids}"
        )

    # IDs dos eventos retornados pelo processamento.
    ids_eventos_saida = saida["id_evento"].dropna().tolist()

    # Remove do banco as versões anteriores dos eventos atualizados.
    if not banco.empty:
        banco = banco[
            ~banco["id_evento"].isin(ids_eventos_saida)
        ].copy()

    # Insere as versões atualizadas e os eventos novos.
    banco = gpd.GeoDataFrame(
        pd.concat(
            [banco, saida],
            ignore_index=True,
        ),
        geometry="geometry",
        crs=banco.crs,
    )

    banco["id_evento"] = banco["id_evento"].astype("Int64")

    if "id_evento_absorvedor" in banco.columns:
        banco["id_evento_absorvedor"] = (
            banco["id_evento_absorvedor"].astype("Int64")
        )

    return banco, proximo_id_evento
#------------------------------------------------------------------------
# Função para exibir resumo dos banco (gdf)
#------------------------------------------------------------------------
def exibir_resumo_banco(gdf_eventos_banco) -> None:
    """Exibe no terminal o estado atual do banco de eventos."""

    print("\n" + "=" * 70)
    print("BANCO DE EVENTOS APÓS A ITERAÇÃO")
    print("=" * 70)

    print(f"CRS: {gdf_eventos_banco.crs}")

    quantidade_total = len(gdf_eventos_banco)
    print(f"Quantidade total de eventos no banco: {quantidade_total}")

    if gdf_eventos_banco.empty:
        print("Banco vazio.")
        print("=" * 70)
        return

    geometrias_nulas = gdf_eventos_banco.geometry.isna()
    geometrias_vazias = gdf_eventos_banco.geometry.is_empty
    geometrias_invalidas = ~gdf_eventos_banco.geometry.is_valid

    print(f"Geometrias nulas: {geometrias_nulas.sum()}")
    print(f"Geometrias vazias: {geometrias_vazias.sum()}")
    print(f"Geometrias inválidas: {geometrias_invalidas.sum()}")

    if "id_evento_absorvedor" not in gdf_eventos_banco.columns:
        raise ValueError(
            "O banco não possui a coluna 'id_evento_absorvedor'."
        )

    colunas_exibidas = [
        coluna
        for coluna in [
            "id_evento",
            "data_inicio",
            "data_ultima_observacao",
            "data_fim",
            "status",
            #"extinto_por_fusionamento",
            "id_evento_absorvedor",
            "area_inicio",
            "area_fim",
            "quantidade_focos",
            "persistencia",
        ]
        if coluna in gdf_eventos_banco.columns
    ]

    eventos_nao_extintos = gdf_eventos_banco[
        gdf_eventos_banco["id_evento_absorvedor"].isna() == True
    ].copy()

    eventos_extintos = gdf_eventos_banco[
        gdf_eventos_banco["id_evento_absorvedor"].isna() == False
    ].copy()

    print("\n" + "-" * 70)
    print("EVENTOS NÃO EXTINTOS POR FUSIONAMENTO")
    print("-" * 70)
    print(f"Quantidade: {len(eventos_nao_extintos)}")

    if eventos_nao_extintos.empty:
        print("Nenhum evento não extinto por fusionamento.")
    else:
        print(
            eventos_nao_extintos[colunas_exibidas]
            .sort_values("id_evento")
            .to_string(index=False)
        )

    print("\n" + "-" * 70)
    print("EVENTOS EXTINTOS POR FUSIONAMENTO")
    print("-" * 70)
    print(f"Quantidade: {len(eventos_extintos)}")

    if eventos_extintos.empty:
        print("Nenhum evento extinto por fusionamento.")
    else:
        print(
            eventos_extintos[colunas_exibidas]
            .sort_values("id_evento")
            .to_string(index=False)
        )

    print("\n" + "-" * 70)
    print("RESUMO FINAL")
    print("-" * 70)
    print(f"Total de eventos no banco: {quantidade_total}")
    print(
        "Eventos não extintos por fusionamento: "
        f"{len(eventos_nao_extintos)}"
    )
    print(
        "Eventos extintos por fusionamento: "
        f"{len(eventos_extintos)}"
    )

    print("=" * 70)


#------------------------------------------------------------------------
#------------------------------------------------------------------------
# Início do processamento2
#------------------------------------------------------------------------


# Criando objeto MapeadorEventos
mapeador_eventos = MapeadorEventos()

# Geração dos lotes diários em memória
lotes_diarios = gerar_lotes_diarios(gdf_focos=gdf_focos)

# Criar gdf (banco) vazio 
gdf_eventos_banco = criar_gdf_eventos_vazio(crs="EPSG:5880")

# define id evento inicial = 1
proximo_id = 1

# Looping de processamento diário
for data_processamento, focos_dia_geojson in lotes_diarios:

    gdf_eventos_processados = integrar_eventos(
        focos_dia_geojson,
        gdf_eventos_banco,
    )

    # gdf_eventos_processados = (
    #     mapeador_eventos.mapear_lista_eventos_finais_para_gdf(
    #         eventos_processados
    #     )
    # )

    gdf_eventos_banco, proximo_id = (
        atribuir_ids_e_atualizar_banco(
            gdf_eventos_banco,
            gdf_eventos_processados,
            proximo_id,
        )
    )

print(f"\nProcessamento concluído: {data_processamento}")
# evento_1 = gdf_eventos_banco.loc[
#     gdf_eventos_banco["id_evento"] == 1
# ].iloc[0]

# evento_2 = gdf_eventos_banco.loc[
#     gdf_eventos_banco["id_evento"] == 2
# ].iloc[0]

# evento_9 = gdf_eventos_banco.loc[
#     gdf_eventos_banco["id_evento"] == 9
# ].iloc[0]

# assert evento_1["data_inicio"] == pd.Timestamp("2025-01-01")
# assert evento_1["data_ultima_observacao"] == pd.Timestamp("2025-01-05")

# assert evento_2["extinto_por_fusionamento"]
# assert evento_2["id_evento_absorvedor"] == 1
# assert evento_2["status"] == StatusEvento.EXTINTO

# assert evento_9["data_inicio"] == pd.Timestamp("2025-01-05")
# assert evento_9["data_ultima_observacao"] == pd.Timestamp("2025-01-05")
# assert evento_2["data_fim"] == pd.Timestamp("2025-01-02")

exibir_resumo_banco(gdf_eventos_banco)

# ------------------------------------------------------------------------
# Exportar gdf final (banco) para arquivo
# ------------------------------------------------------------------------

from pathlib import Path

gdf_exportacao = gdf_eventos_banco.copy()

for coluna in gdf_exportacao.columns:
    if coluna == gdf_exportacao.geometry.name:
        continue

    serie = gdf_exportacao[coluna]

    # Colunas já reconhecidas como datetime
    if is_datetime64_any_dtype(serie):
        if getattr(serie.dt, "tz", None) is not None:
            gdf_exportacao[coluna] = (
                serie
                .dt.tz_convert("UTC")
                .dt.tz_localize(None)
            )

        continue

    # Colunas object que contêm Timestamp
    valores = serie.dropna()

    if not valores.empty and isinstance(
        valores.iloc[0],
        (pd.Timestamp,),
    ):
        convertida = pd.to_datetime(serie, utc=True, errors="coerce")

        gdf_exportacao[coluna] = (
            convertida
            .dt.tz_convert("UTC")
            .dt.tz_localize(None)
        )

pasta_comparacao = Path("comparacao")
pasta_comparacao.mkdir(parents=True, exist_ok=True)

# caminho_saida = pasta_comparacao / "eventos_refatoracao3.gpkg"

# gdf_exportacao.to_file(
#     caminho_saida,
#     layer="eventos",
#     driver="GPKG",
#     index=False,
# )
# print(f"Arquivo salvo em: {caminho_saida.resolve()}")

