from evento_fogo.infraestrutura.config.configuracao import Configuracao


def test_obter_tipo_buffer():
    config = Configuracao()

    tipo_buffer = config.obter_tipo_buffer()

    assert isinstance(tipo_buffer, str)
    assert tipo_buffer in {"quadrado", "circular"}


def test_obter_crs_metrico():
    config = Configuracao()

    crs_metrico = config.obter_crs_metrico()

    assert crs_metrico == "EPSG:5880"


def test_obter_crs_lat_lon():
    config = Configuracao()

    crs_lat_lon = config.obter_crs_lat_lon()

    assert crs_lat_lon == "EPSG:4326"


def test_obter_agregar_por_dia():
    config = Configuracao()

    agregar_por_dia = config.obter_agregar_por_dia()

    assert isinstance(agregar_por_dia, bool)


def test_obter_intervalo_dias_espaco_temporal():
    config = Configuracao()

    intervalo_dias = (
        config.obter_intervalo_dias_espaco_temporal()
    )

    assert isinstance(intervalo_dias,int)
    assert intervalo_dias > 0
    


def test_obter_buffer_por_satelite_retorna_raios_configurados():
    config = Configuracao()

    buffers = config.obter_buffer_por_satelite()

    assert buffers["AQUA_M-T"] == 500

    assert buffers["GOES-16"] == 1300
    assert buffers["GOES-19"] == 1300


def test_obter_buffer_por_satelite_mapeia_raio_por_id_e_nome():
    config = Configuracao()

    buffers = config.obter_buffer_por_satelite()

    assert isinstance(buffers, dict)
    assert len(buffers) > 0
    assert "GOES-16" in buffers
    assert isinstance(buffers["GOES-16"], (int, float))
    assert buffers["GOES-16"] > 0