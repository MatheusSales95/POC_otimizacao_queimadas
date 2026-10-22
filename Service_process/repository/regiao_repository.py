import geopandas as gpd
from sqlalchemy import create_engine
from sqlalchemy.engine.url import make_url
from shared.config import config_keys
from config import DB_URL
import traceback
import warnings

class RegiaoRepository:
    def __init__(self, nome_db: str):
        self.nome_db = nome_db

    def carregar_regioes_gdf(self) -> gpd.GeoDataFrame:
        
        """Carrega a tabela de regiões para um GeoDataFrame."""

        tb_regiao = config_keys["tables"]["regiao"]
        col_reg = config_keys["columns"]["regiao"]
        geom_col = col_reg["geometria"]
        id_col = col_reg["id_regiao"]
        nome_col = col_reg["nome_regiao"]
        tipo_col = col_reg["tipo_regiao"]
        
        try:
            nome_colecao = f"collection_{self.nome_db}"
            url_dinamica = make_url(DB_URL).set(database=nome_colecao)
            engine = create_engine(url_dinamica)
        except Exception as e:
            traceback.print_exc()
            raise Exception(f"Falha ao conectar ao banco de dados: {e}")
        
        query = f"SELECT {id_col} AS id_regiao, {nome_col} AS nome_regiao, {tipo_col} AS tipo_regiao, encode(ST_AsEWKB({geom_col}), 'hex') AS {geom_col} FROM {tb_regiao}"
        
        try:
            raw_conn = engine.raw_connection()
            try:
                with raw_conn.cursor() as cur:
                    cur.execute(f'SET search_path TO "{self.nome_db}", public;')
                
                with warnings.catch_warnings():
                    warnings.filterwarnings("ignore", message=".*pandas only supports SQLAlchemy connectable.*")
                    gdf_regioes = gpd.read_postgis(query, con=raw_conn, geom_col=geom_col)
                    
                if gdf_regioes.crs is None:
                    gdf_regioes.set_crs(epsg=4326, inplace=True, allow_override=True)
                return gdf_regioes
            finally:
                raw_conn.close()
        except Exception as e:
            traceback.print_exc()
            raise Exception(f"Falha ao carregar regiões para a memória: {e}")
