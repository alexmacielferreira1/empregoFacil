"""Localização aproximada por bairro/cidade (Grande Porto Alegre).

Coordenadas são o centro APROXIMADO de cada bairro/cidade, suficientes para
ordenar vagas e cursos por distância no MVP. Numa fase posterior, trocar por
geocodificação de CEP (ViaCEP + Nominatim ou Google) e PostGIS.
"""
from math import asin, cos, radians, sin, sqrt

LOCAIS: dict[str, tuple[float, float]] = {
    # Porto Alegre — bairros
    "Centro Histórico": (-30.0331, -51.2300),
    "Cidade Baixa": (-30.0420, -51.2210),
    "Menino Deus": (-30.0530, -51.2240),
    "Azenha": (-30.0530, -51.2120),
    "Bom Fim": (-30.0330, -51.2110),
    "Navegantes": (-30.0000, -51.2000),
    "Sarandi": (-29.9890, -51.1290),
    "Rubem Berta": (-29.9960, -51.1060),
    "Partenon": (-30.0600, -51.1800),
    "Bom Jesus": (-30.0420, -51.1590),
    "Agronomia": (-30.0700, -51.1400),
    "Lomba do Pinheiro": (-30.1150, -51.1150),
    "Glória": (-30.0800, -51.1980),
    "Cavalhada": (-30.1000, -51.2230),
    "Restinga": (-30.1530, -51.1630),
    "Belém Novo": (-30.2050, -51.1780),
    "Humaitá": (-29.9850, -51.1900),
    "Passo d'Areia": (-30.0150, -51.1600),
    # Região metropolitana — cidades
    "Alvorada": (-29.9900, -51.0800),
    "Viamão": (-30.0810, -51.0230),
    "Cachoeirinha": (-29.9510, -51.0940),
    "Gravataí": (-29.9440, -50.9920),
    "Canoas": (-29.9180, -51.1830),
    "Esteio": (-29.8610, -51.1790),
    "Sapucaia do Sul": (-29.8280, -51.1450),
    "São Leopoldo": (-29.7600, -51.1470),
    "Novo Hamburgo": (-29.6780, -51.1300),
    "Guaíba": (-30.1130, -51.3250),
    "Eldorado do Sul": (-30.0840, -51.6170),
}


def coords(bairro: str | None) -> tuple[float | None, float | None]:
    if not bairro:
        return None, None
    found = LOCAIS.get(bairro)
    if found:
        return found
    low = bairro.strip().lower()
    for nome, c in LOCAIS.items():
        if nome.lower() == low:
            return c
    return None, None


def distancia_km(lat1, lng1, lat2, lng2) -> float | None:
    if None in (lat1, lng1, lat2, lng2):
        return None
    r = 6371.0
    dlat, dlng = radians(lat2 - lat1), radians(lng2 - lng1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    return round(2 * r * asin(sqrt(a)), 1)
