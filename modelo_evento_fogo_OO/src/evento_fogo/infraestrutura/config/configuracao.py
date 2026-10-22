# evento_fogo/infraestrutura/config/configuracao.py
from pathlib import Path
import yaml
import sys
import os



PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from shared.config import config_keys

CAMINHO_PADRAO = Path(__file__).parent / "parametros_processamento.yaml"

class Configuracao:
    
    def __init__(self):
        caminho_yaml = CAMINHO_PADRAO

        with open(caminho_yaml, "r", encoding="utf-8") as arquivo:
            self._dados = yaml.safe_load(arquivo)

    def obter_buffer_por_satelite(self) -> dict:
        dados_buffer_por_satelite = {}
        # =================== satélites com seus id e buffer config_keys        
        for sat_data in config_keys.get("satelite_data", []):
            id_sat = sat_data["id_satelite"]
            nome_sat = sat_data["satelite"]
            
            # Prioriza o raio definido no config_keys.yaml
            if "raio" in sat_data:
                raio = sat_data["raio"]
                dados_buffer_por_satelite[id_sat] = raio
                dados_buffer_por_satelite[nome_sat] = raio
            # Fallback para o parametros_processamento.yaml se não estiver no config_keys
            elif nome_sat in self._dados["buffer"]["por_satelite"]:
                raio = self._dados["buffer"]["por_satelite"][nome_sat]["raio"]
                dados_buffer_por_satelite[id_sat] = raio
                dados_buffer_por_satelite[nome_sat] = raio
                
        return dados_buffer_por_satelite

    def obter_tipo_buffer(self) -> str:
        return self._dados["buffer"]["tipo"]

    def obter_crs_metrico(self) -> str:
        return self._dados["crs"]["metrico"]
    
    def obter_crs_lat_lon(self) -> str:
        return self._dados["crs"]["lat_lon"]
    
    def obter_agregar_por_dia(self) -> bool:
        return self._dados["agregacao"]["agregar_por_dia"]

    def obter_intervalo_dias_espaco_temporal(self) -> int:
        return self._dados["agregacao"]["intervalo_dias_espaco_temporal"]