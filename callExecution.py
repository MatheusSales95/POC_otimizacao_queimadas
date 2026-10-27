from geopandas.io.file import fiona
import geopandas as gpd
import pandas as pd
import gerarEventos
import genetic_algorithm 
import glob
import os

# =====================================================================
# =====================================================================
# CONFIGURAÇÕES
# =====================================================================
MARGIN_BOX = 50 # Margem em metros ao redor do polígono de referência para extração dos focos

# =====================================================================
# 1. CARREGAR A MÁSCARA DE POLÍGONOS UMA ÚNICA VEZ (FORA DO AG)
# =====================================================================
geometrias_path = 'poligonsMask'
arquivos_geojson = glob.glob(os.path.join(geometrias_path, "*.geojson"))

if arquivos_geojson:
    print(f"Carregando {len(arquivos_geojson)} arquivos de máscara...")
    gdfs = [gpd.read_file(arq) for arq in arquivos_geojson]
    # Concatena e projeta para CRS métrico EPSG:5880 (área em m²)
    poligonos_queimadas = pd.concat(gdfs, ignore_index=True).to_crs(epsg=5880)
    geom_mask = poligonos_queimadas.union_all()
    area_mask = geom_mask.area
    print(f"Máscara unificada. Área total de referência: {area_mask / 1e6:.2f} km²")
else:
    geom_mask = None
    area_mask = 0.0
    print("Aviso: Nenhum arquivo encontrado em poligonsMask.")

# Caixa delimitadora do tile com margem
caminho_focos = "focosPantanal040824040924.geojson"
gdf_focos_total = gpd.read_file(caminho_focos).to_crs(epsg=5880)

if geom_mask is not None:
    envelope_tile = geom_mask.envelope.buffer(MARGIN_BOX)
    focos_tile = gdf_focos_total[gdf_focos_total.geometry.within(envelope_tile)].copy()
else:
    focos_tile = gdf_focos_total

COUNT_ESPERADO_EVENTOS = len(focos_tile) # No limite, pior caso, deve-se formar tantos eventos quanso focos houver


print(f"Focos no Pantanal inteiro: {len(gdf_focos_total)} | Focos dentro do Tile: {len(focos_tile)}")

# =====================================================================
# Eventos CONTROLE (Baseline com raio padrão 1300m no tile)
# =====================================================================
os.makedirs("eventsResults", exist_ok=True)
eventos_controle = gerarEventos.executarProcessamento(
    data_inicio="2024-08-04",
    data_fim="2024-09-04",
    raio=1300,
    gdf_focos=focos_tile,
    satelites_alvo=None,
    retornar_crs_4326=False
)
eventos_controle.to_file("eventsResults/events_control.geojson", driver="GeoJSON")
print("Eventos de controle gerados com sucesso.")


# =====================================================================
# 2. FUNÇÃO OBJETIVO (fob): Recebe x (raio) e retorna um float a minimizar
# =====================================================================
fob_cache = {}

def fob(x):
    raio_key = int(round(x))
    if raio_key in fob_cache:
        return fob_cache[raio_key]

    # Processa os eventos para o raio candidato
    eventos = gerarEventos.executarProcessamento(
        data_inicio="2024-08-04",
        data_fim="2024-09-04",
        raio=raio_key,
        gdf_focos=focos_tile,
        satelites_alvo=None,
        retornar_crs_4326=False  # Mantém EPSG:5880 para cálculo de área
    )
    count_eventos = len(eventos)
    print(f"  -> [Simulação] Avaliando raio = {raio_key} m | {len(fob_cache)}/ {n_generations * pop_size} simulações já realizadas | número de eventos {count_eventos}...", flush=True)
    if count_eventos == 0:
        fob_cache[raio_key] = 999.0
        return 999.0  # Penalidade se o raio não formar nenhum evento
    
    # União da área acumulada de todos os eventos gerados
    geom_eventos = eventos.union_all()
    area_eventos = geom_eventos.area
    
    # Se temos polígonos de referência da máscara:
    if geom_mask is not None and area_mask > 0:
        

        intersecao = geom_eventos.intersection(geom_mask).area
        # Coeficiente de Dice (mede sobreposição: 1 = perfeito, 0 = sem interseção)
        denom_dice = area_eventos + area_mask

        dice = (2.0 * intersecao / denom_dice) if denom_dice > 0 else 0.0
        
        ### MELHORAR A ESCALA DA FOB (LOG OU EXP) ####
        #### F1 SCORE #### JUSTIFICAR O PRECISION E RECALL #####


        # Dissimilaridade (quanto menor, mais próxima a área acumulada está da máscara)
        dissimilaridade = 1.0 - dice
        # Penalidade pelo número de eventos (normalizado para 0 a 1)
        penalidade_eventos = min(count_eventos / COUNT_ESPERADO_EVENTOS, 1.0)
        
        # Combinação multiobjetivo:
        w_area = 0.8
        w_eventos = 0.2
        f_val = (w_area * dissimilaridade) + (w_eventos * penalidade_eventos)
        
        fob_cache[raio_key] = float(f_val)
        return float(f_val)
    else:
        # Caso não haja máscara válida com interseção, minimiza o número de eventos
        fob_cache[raio_key] = float(count_eventos)
        return float(count_eventos)


# =====================================================================
# 3. EXECUTAR O ALGORITMO GENÉTICO
# =====================================================================
minRatio = 1000
maxRatio = 1500
pop_size = 50      
crom_size = 12      # 16 bits -> intervalo [1000, 1500]
n_generations = 25
pm = 0.01

print("\n--- Inicializando População Inicial do AG ---", flush=True)
population = genetic_algorithm.Population(
    pop_size, crom_size, minRatio, maxRatio, fob, genetic_algorithm.fitness
)
print("--- População Inicial Concluída! Iniciando Gerações ---\n", flush=True)

best_x_history = []
best_f_history = []

for generation in range(n_generations):

    # Best individual
    best = min(population.individuals, key=lambda ind: ind.fob)
    print(f"Geração {generation + 1}/{n_generations} - Melhor Raio: {best.x_r:.1f} m | fob: {best.fob:.4f}", flush=True)

    best_x_history.append(best.x_r)
    best_f_history.append(best.fob)

    # Selection and crossover
    roulette = genetic_algorithm.Roulette(population)
    new_individuals = []

    while len(new_individuals) < pop_size:

        idx1 = roulette.spin()
        idx2 = roulette.spin()

        parent_1 = population.individuals[idx1]
        parent_2 = population.individuals[idx2]

        child_1, child_2 = genetic_algorithm.cross(parent_1, parent_2)

        child_1 = genetic_algorithm.mutation(child_1, pm)
        child_2 = genetic_algorithm.mutation(child_2, pm)

        new_individuals.append(child_1)

        if len(new_individuals) < pop_size:
            new_individuals.append(child_2)

    # Full population replacement
    population.individuals = new_individuals

# Best final individual
best = min(population.individuals, key=lambda ind: ind.fob)

print("\n" + "=" * 50)
print("Melhor solução encontrada:")
print(f"Raio ótimo = {best.x_r:.2f} m")
print(f"Valor da função objetivo = {best.fob:.4f}")
print("=" * 50)

# Salvar eventos otimizados
eventos_otimizados = gerarEventos.executarProcessamento(
    data_inicio="2024-08-04",
    data_fim="2024-09-04",
    raio=best.x_r,
    gdf_focos=focos_tile,
    satelites_alvo=None,
    retornar_crs_4326=False
)
eventos_otimizados.to_file("eventsResults/events_optimized.geojson", driver="GeoJSON")
print("Eventos otimizados salvos em 'eventsResults/events_optimized.geojson'.")
