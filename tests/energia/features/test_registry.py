import pandas as pd
import pytest

from energia_app.config import FeatureSpec
from energia_app.exceptions import ConfigError, FeatureError
from energia_app.features import FeatureBlock, available_blocks, create_block, register


@register("constante_de_prueba")
class Constante(FeatureBlock):
    """Bloque mínimo, solo para los tests: una columna con un valor fijo."""

    def __init__(self, valor: float = 1.0, timezone: str = "UTC"):
        self.valor, self.timezone = valor, timezone

    @property
    def columns(self):
        return ["constante"]

    def _compute(self, prices, instants):
        return pd.DataFrame({"constante": self.valor}, index=instants)


class MalIndice(Constante):
    def _compute(self, prices, instants):
        return pd.DataFrame({"constante": 1.0}, index=instants[::-1])


def test_un_bloque_nuevo_se_usa_desde_la_configuracion_sin_tocar_nada_mas(serie):
    bloque = create_block(FeatureSpec("constante_de_prueba", {"valor": 7.0}))

    out = bloque.transform(serie, serie.index[:5])

    assert "constante_de_prueba" in available_blocks()
    assert out["constante"].tolist() == [7.0] * 5


def test_el_contexto_solo_llega_a_quien_lo_pide():
    bloque = create_block(FeatureSpec("constante_de_prueba"), context={"timezone": "Europe/Madrid", "otra": 1})

    assert bloque.timezone == "Europe/Madrid"


def test_nombre_desconocido_dice_los_disponibles():
    with pytest.raises(ConfigError, match="Disponibles"):
        create_block(FeatureSpec("no_existe"))


def test_parametro_que_el_bloque_no_acepta():
    with pytest.raises(ConfigError, match="Parámetros no válidos"):
        create_block(FeatureSpec("constante_de_prueba", {"sin_sentido": 3}))


def test_no_se_puede_registrar_dos_veces_el_mismo_nombre():
    with pytest.raises(ConfigError, match="Ya hay un bloque"):
        register("constante_de_prueba")(MalIndice)


def test_la_plantilla_rechaza_un_indice_distinto(serie):
    with pytest.raises(FeatureError, match="índice distinto"):
        MalIndice().transform(serie, serie.index[:5])


def test_la_plantilla_exige_fechas_en_utc(serie):
    local = serie.tz_convert("Europe/Madrid")

    with pytest.raises(FeatureError, match="UTC"):
        Constante().transform(local, local.index)
