import os
import yaml

pasta_atual = os.path.dirname(os.path.abspath(__file__))
pasta_raiz = os.path.dirname(pasta_atual)
caminho_yaml = os.path.join(pasta_atual, 'config_keys.yaml')

with open(caminho_yaml, 'r', encoding='utf-8') as f:
    keys = yaml.safe_load(f)

config_keys = keys if keys else {}

