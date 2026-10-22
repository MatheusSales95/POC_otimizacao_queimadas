from evento_fogo.infraestrutura.config.configuracao import Configuracao
from evento_fogo.processamento.preparador_focos import PreparadorFocos
from evento_fogo.mapeadores.mapeador_focos import MapeadorFocos
from evento_fogo.processamento.bufferizador_focos import Bufferizador
from evento_fogo.processamento.identificacao_grupos_espaciais import IdentificadorGruposEspaciais
from evento_fogo.processamento.criador_eventos_diarios import CriadorEventosDiarios
from evento_fogo.mapeadores.mapeador_eventos import MapeadorEventos
from evento_fogo.processamento.identificacao_grupos_espaciais import IdentificadorGruposEspaciais
from evento_fogo.processamento.identificacao_grupos_espaco_temporais import IdentificadorGruposEspacoTemporais
from evento_fogo.processamento.resolucao_fusionamentos import ResolvedorFusionamentos
import geopandas as gpd
from io import StringIO
from typing import TypeAlias
GeoJSON: TypeAlias = str

from shared.config import config_keys

def integrar_eventos(
    focos_dia_geojson: GeoJSON,
    gdf_banco: gpd.GeoDataFrame | None = None,
) -> GeoJSON:
    
    #-------------------------------------------------------------------------------------
    # Configuração - Arquivo: src/infraestrutura/config/config.yaml
    #-------------------------------------------------------------------------------------
    config = Configuracao()
    buffer_por_satelite = config.obter_buffer_por_satelite()
    tipo_buffer = config.obter_tipo_buffer()
    crs_metrico = config.obter_crs_metrico()
    crs_lat_lon = config.obter_crs_lat_lon()
    agrupar_por_dia = config.obter_agregar_por_dia()
    intervalo_dias = config.obter_intervalo_dias_espaco_temporal()

    #-------------------------------------------------------------------------------------
    # Checar e preparar focos para processamento
    #-------------------------------------------------------------------------------------

    preparador = PreparadorFocos(
        focos_geojson=focos_dia_geojson,
        agrupar_apenas_por_dia=agrupar_por_dia,
    )

    focos_dia, data_processamento = preparador.preparar_focos()

    #-------------------------------------------------------------------------------------
    # Tratamento dos Focos
    #-------------------------------------------------------------------------------------
    mapeador_focos = MapeadorFocos()

    # Mapeia gdf diário de focos para lista e instancia objetos Foco
    focos = mapeador_focos.mapear_gdf_para_lista(focos_dia)

    # Mapeia lista diária de objetos objetos focos para gdf. 
    # (processamento ainda realizado com geopandas) 
    gdf_focos = mapeador_focos.mapear_lista_para_gdf(focos=focos)

    #-------------------------------------------------------------------------------------
    # Bufferização - Usa lista de satélites para associar com raio do buffer
    #-------------------------------------------------------------------------------------
    buferizador = Bufferizador(gdf=gdf_focos,buffer_por_satelite=buffer_por_satelite,
                              tipo_buffer=tipo_buffer)
    gdf_focos_bufferizado = buferizador.bufferizar_focos()

    #-------------------------------------------------------------------------------------
    # Identificação dos grupos de buffers que se tocam
    #-------------------------------------------------------------------------------------
    identificador_espacial = IdentificadorGruposEspaciais()

    grupos_espaciais = identificador_espacial.identificar_grupos(
        gdf_focos_bufferizado
    )

    #-------------------------------------------------------------------------------------
    # Criador de eventos diários
    #-------------------------------------------------------------------------------------
    criador_eventos_diarios = CriadorEventosDiarios()

    lista_eventos_diarios = (
        criador_eventos_diarios.criar_eventos(
            grupos_espaciais
        )
    )


    #-------------------------------------------------------------------------------------
    # Pré-processamento dos eventos retornados do banco para processamento
    #-------------------------------------------------------------------------------------
    mapeador_eventos = MapeadorEventos()
    lista_eventos_existentes = []
    lista_eventos_processaveis = []

    if gdf_banco is not None and not gdf_banco.empty:

        if gdf_banco.crs != crs_metrico:
            raise ValueError(
                "Os eventos existentes devem estar no CRS operacional "
                f"{crs_metrico}. CRS recebido: {gdf_banco.crs}"
            )

        lista_eventos_existentes = (
            mapeador_eventos.mapear_geojson_banco_para_lista_eventos(
                gdf_banco.copy()
            )
        )

        
        status_data = config_keys.get("status_data", [])
        status_map = {item["nome"].lower(): item["id_status"] for item in status_data}
        STATUS_EXTINTO = status_map.get("extinto", 3)

        lista_eventos_processaveis = [
            evento
            for evento in lista_eventos_existentes
            if evento.status != STATUS_EXTINTO
        ]

    lista_eventos_para_processamento_temporal = (
        lista_eventos_processaveis
        + lista_eventos_diarios
    )


    # Mapeamento da listade eventos processáveis para ggf.
    gdf_eventos_para_processamento_temporal = (
        mapeador_eventos.mapear_lista_eventos_para_gdf_processamento_temporal(
            lista_eventos_para_processamento_temporal
        )
    )

    #-------------------------------------------------------------------------------------
    # Identificação dos grupos espaço-temporais
    #-------------------------------------------------------------------------------------

    identificador = IdentificadorGruposEspacoTemporais(
        intervalo_dias=intervalo_dias,
    )

    grupos_eventos = identificador.identificar_grupos(
        gdf_eventos_para_processamento_temporal
    )


    #-------------------------------------------------------------------------------------
    # Resolução e absorção de eventos que se tocam
    #-------------------------------------------------------------------------------------

    resolvedor = ResolvedorFusionamentos()

    decisoes = resolvedor.resolver_grupos(
        grupos_eventos
    )

    #-------------------------------------------------------------------------------------
    # Aplicação das absorções
    #-------------------------------------------------------------------------------------
    eventos_continuados = []
    eventos_extintos_fusao = []

    for evento_absorvedor, eventos_absorvidos in decisoes:

        evento_absorvedor.absorver_eventos(
            eventos_absorvidos
        )

        eventos_continuados.append(
            evento_absorvedor
        )

        for evento_absorvido in eventos_absorvidos:
            # Evento diário: nunca foi persistido.
            if evento_absorvido.id_evento is None:
                continue

            # Um evento persistido não pode ser absorvido por um evento
            # que ainda não possui identidade persistida.
            if evento_absorvedor.id_evento is None:
                raise ValueError(
                    "Um evento persistido não pode ser extinto por um "
                    "evento absorvedor ainda não persistido."
                )

            evento_absorvido.extinguir_por_fusionamento(
                evento_absorvedor.id_evento,
                evento_absorvedor.data_ultima_observacao
            )

            eventos_extintos_fusao.append(
                evento_absorvido
            )



# -------------------------------------------------------------------------
# Atualização dos eventos
# -------------------------------------------------------------------------

    eventos_processados = (
        eventos_continuados
        + eventos_extintos_fusao
    )

    for evento in eventos_processados:
        evento.atualizar_status(
            data_ultima_base=data_processamento
        )
        evento.persistencia = evento.calcular_persistencia()

    gdf_eventos_final = mapeador_eventos.mapear_lista_eventos_finais_para_gdf(
        eventos_processados
    )

    return gdf_eventos_final
