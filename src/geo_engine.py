import math
import re
from typing import Dict, Optional, Tuple

# Base de coordenadas de Capitais e Polos Regionais do Brasil (Lat, Lon)
BRAZILIAN_CITIES: Dict[str, Tuple[float, float, str]] = {
    # Capitais
    "sao paulo": (-23.5505, -46.6333, "SP"),
    "rio de janeiro": (-22.9068, -43.1729, "RJ"),
    "belo horizonte": (-19.9167, -43.9345, "MG"),
    "brasilia": (-15.7975, -47.8919, "DF"),
    "salvador": (-12.9714, -38.5014, "BA"),
    "fortaleza": (-3.7172, -38.5433, "CE"),
    "curitiba": (-25.4284, -49.2733, "PR"),
    "recife": (-8.0476, -34.8770, "PE"),
    "porto alegre": (-30.0346, -51.2177, "RS"),
    "manaus": (-3.1190, -60.0217, "AM"),
    "belem": (-1.4558, -48.4902, "PA"),
    "goiania": (-16.6869, -49.2648, "GO"),
    "florianopolis": (-27.5954, -48.5480, "SC"),
    "vitoria": (-20.3155, -40.3128, "ES"),
    "natal": (-5.7945, -35.2110, "RN"),
    "joao pessoa": (-7.1195, -34.8450, "PB"),
    "maceio": (-9.6658, -35.7351, "AL"),
    "teresina": (-5.0919, -42.8034, "PI"),
    "campo grande": (-20.4697, -54.6201, "MS"),
    "cuiaba": (-15.6014, -56.0979, "MT"),
    "sao luis": (-2.5307, -44.3068, "MA"),
    "aracaju": (-10.9472, -37.0731, "SE"),
    "porto velho": (-8.7612, -63.9039, "RO"),
    "macapa": (0.0356, -51.0705, "AP"),
    "palmas": (-10.1844, -48.3336, "TO"),
    "rio branco": (-9.9754, -67.8249, "AC"),
    "boa vista": (2.8235, -60.6758, "RR"),

    # São Paulo (Polos e Cidades de Concursos)
    "campinas": (-22.9099, -47.0626, "SP"),
    "guarulhos": (-23.4542, -46.5333, "SP"),
    "santo andre": (-23.6639, -46.5383, "SP"),
    "sao bernardo do campo": (-23.6944, -46.5653, "SP"),
    "osasco": (-23.5329, -46.7916, "SP"),
    "santos": (-23.9608, -46.3336, "SP"),
    "ribeirao preto": (-21.1767, -47.8208, "SP"),
    "sao jose dos campos": (-23.1791, -45.8872, "SP"),
    "sorocaba": (-23.5015, -47.4526, "SP"),
    "sao jose do rio preto": (-20.8113, -49.3758, "SP"),
    "jundiai": (-23.1857, -46.8978, "SP"),
    "piracicaba": (-22.7253, -47.6492, "SP"),
    "bauru": (-22.3147, -49.0606, "SP"),
    "franca": (-20.5386, -47.4008, "SP"),
    "itanhaem": (-24.1833, -46.7894, "SP"),
    "assis": (-22.6617, -50.4181, "SP"),
    "boituva": (-23.2847, -47.6719, "SP"),
    "clementina": (-21.5706, -50.4497, "SP"),
    "dois corregos": (-22.3653, -48.3800, "SP"),
    "estrela do norte": (-22.4925, -51.6706, "SP"),
    "barao de antonina": (-23.6264, -49.5606, "SP"),
    "marilia": (-22.2139, -49.9458, "SP"),
    "araraquara": (-21.7946, -48.1766, "SP"),
    "presidente prudente": (-22.1256, -51.3889, "SP"),
    "limeira": (-22.5647, -47.4017, "SP"),
    "taubate": (-23.0264, -45.5553, "SP"),
    "praia grande": (-24.0058, -46.4028, "SP"),
    "guaruja": (-23.9931, -46.2564, "SP"),
    "buri": (-23.7975, -48.5928, "SP"),
    "itapeva": (-23.9826, -48.8786, "SP"),
    "capao bonito": (-24.0064, -48.3494, "SP"),
    "itapetininga": (-23.5917, -48.0531, "SP"),
    "tatui": (-23.3556, -47.8569, "SP"),
    "avare": (-23.0989, -48.9256, "SP"),
    "itarare": (-24.1167, -49.3333, "SP"),

    # Minas Gerais
    "uberlandia": (-18.9186, -48.2772, "MG"),
    "juiz de fora": (-21.7587, -43.3496, "MG"),
    "montes claros": (-16.7281, -43.8617, "MG"),
    "betim": (-19.9678, -44.1983, "MG"),
    "contagem": (-19.9317, -44.0536, "MG"),
    "uberaba": (-19.7472, -47.9392, "MG"),
    "governador valadares": (-18.8511, -41.9494, "MG"),
    "ipatinga": (-19.4686, -42.5369, "MG"),
    "pocos de caldas": (-21.7878, -46.5614, "MG"),
    "unai": (-16.3578, -46.9064, "MG"),
    "patos de minas": (-18.5789, -46.5181, "MG"),
    "pouso alegre": (-22.2300, -45.9364, "MG"),
    "varginha": (-21.5517, -45.4300, "MG"),
    "divinopolis": (-20.1439, -44.8858, "MG"),

    # Rio de Janeiro
    "niteroi": (-22.8833, -43.1036, "RJ"),
    "sao goncalo": (-22.8269, -43.0539, "RJ"),
    "duque de caxias": (-22.7856, -43.3117, "RJ"),
    "nova iguacu": (-22.7558, -43.4603, "RJ"),
    "campos dos goytacazes": (-21.7544, -41.3244, "RJ"),
    "petropolis": (-22.5050, -43.1789, "RJ"),
    "volta redonda": (-22.5231, -44.1042, "RJ"),
    "macae": (-22.3769, -41.7869, "RJ"),
    "cabo frio": (-22.8797, -42.0186, "RJ"),

    # Paraná, Santa Catarina e Rio Grande do Sul
    "londrina": (-23.3103, -51.1628, "PR"),
    "maringa": (-23.4210, -51.9331, "PR"),
    "ponta grossa": (-25.0994, -50.1583, "PR"),
    "cascavel": (-24.9578, -53.4594, "PR"),
    "foz do iguacu": (-25.5163, -54.5853, "PR"),
    "joinville": (-26.3045, -48.8487, "SC"),
    "blumenau": (-26.9194, -49.0661, "SC"),
    "caxias do sul": (-29.1681, -51.1794, "RS"),
    "pelotas": (-31.7654, -52.3376, "RS"),
    "canoas": (-29.9178, -51.1836, "RS"),
    "santa maria": (-29.6842, -53.8069, "RS"),
    "chapeco": (-27.1004, -52.6152, "SC"),
    "itajai": (-26.9078, -48.6619, "SC"),
    "criciuma": (-28.6775, -49.3697, "SC"),

    # Nordeste / Centro-Oeste / Norte
    "feira de santana": (-12.2664, -38.9663, "BA"),
    "vitoria da conquista": (-14.8661, -40.8394, "BA"),
    "caruaru": (-8.2833, -35.9761, "PE"),
    "petrolina": (-9.3986, -40.5008, "PE"),
    "campina grande": (-7.2306, -35.8811, "PB"),
    "mossoro": (-5.1878, -37.3442, "RN"),
    "anapolis": (-16.3267, -48.9533, "GO"),
    "rio verde": (-17.7925, -50.9192, "GO"),
    "dourados": (-22.2231, -54.8081, "MS"),
    "rondonopolis": (-16.4678, -54.6372, "MT"),
    "santarem": (-2.4431, -54.7083, "PA"),
    "maraba": (-5.3686, -49.1178, "PA"),
    "imperatriz": (-5.5264, -47.4725, "MA"),
    "parnaiba": (-2.9039, -41.7769, "PI"),
    "currais": (-9.0069, -44.4078, "PI"),
    "acari": (-6.4278, -36.6406, "RN"),
    "tangara": (-6.1986, -35.7997, "RN"),
    "cruzeta": (-6.4114, -36.7897, "RN"),
    "nisia floresta": (-6.0917, -35.2089, "RN"),
}

# Coordenadas Centrais de cada Estado (fallback quando cidade específica não for achada)
UF_CENTROIDS: Dict[str, Tuple[float, float, str]] = {
    "SP": (-23.5505, -46.6333, "São Paulo"),
    "RJ": (-22.9068, -43.1729, "Rio de Janeiro"),
    "MG": (-19.9167, -43.9345, "Belo Horizonte"),
    "DF": (-15.7975, -47.8919, "Brasília"),
    "ES": (-20.3155, -40.3128, "Vitória"),
    "PR": (-25.4284, -49.2733, "Curitiba"),
    "SC": (-27.5954, -48.5480, "Florianópolis"),
    "RS": (-30.0346, -51.2177, "Porto Alegre"),
    "BA": (-12.9714, -38.5014, "Salvador"),
    "PE": (-8.0476, -34.8770, "Recife"),
    "CE": (-3.7172, -38.5433, "Fortaleza"),
    "RN": (-5.7945, -35.2110, "Natal"),
    "PB": (-7.1195, -34.8450, "João Pessoa"),
    "AL": (-9.6658, -35.7351, "Maceió"),
    "SE": (-10.9472, -37.0731, "Aracaju"),
    "PI": (-5.0919, -42.8034, "Teresina"),
    "MA": (-2.5307, -44.3068, "São Luís"),
    "GO": (-16.6869, -49.2648, "Goiânia"),
    "MT": (-15.6014, -56.0979, "Cuiabá"),
    "MS": (-20.4697, -54.6201, "Campo Grande"),
    "AM": (-3.1190, -60.0217, "Manaus"),
    "PA": (-1.4558, -48.4902, "Belém"),
    "RO": (-8.7612, -63.9039, "Porto Velho"),
    "TO": (-10.1844, -48.3336, "Palmas"),
    "AC": (-9.9754, -67.8249, "Rio Branco"),
    "AP": (0.0356, -51.0705, "Macapá"),
    "RR": (2.8235, -60.6758, "Boa Vista"),
    "NACIONAL": (-15.7975, -47.8919, "Brasília (Federal)"),
}


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calcula a distância geodésica em quilômetros usando a fórmula de Haversine."""
    R = 6371.0  # Raio da Terra em km

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    return round(R * c, 1)


def normalize_city_name(name: str) -> str:
    """Normaliza o nome da cidade removendo acentos e espaços extras."""
    import unicodedata
    normalized = unicodedata.normalize('NFKD', name)
    without_accents = "".join([c for c in normalized if not unicodedata.combining(c)])
    return re.sub(r'[^a-zA-Z0-9\s]', ' ', without_accents).lower().strip()


def extract_city_and_coords(title: str, details: str, uf: str) -> Tuple[str, Optional[float], Optional[float]]:
    """
    Identifica o município do concurso a partir do título/órgão e atribui coordenadas geográficas.
    Retorna (nome_cidade, latitude, longitude).
    """
    combined = f"{title} {details}"
    norm_combined = normalize_city_name(combined)

    # 1. Tenta encontrar cidade nas conhecidas do mesmo estado
    uf_upper = uf.upper()
    for city_key, (c_lat, c_lon, c_uf) in BRAZILIAN_CITIES.items():
        if c_uf == uf_upper or uf_upper == "NACIONAL":
            # Procura por palavra inteira
            if re.search(r'\b' + re.escape(city_key) + r'\b', norm_combined):
                # Formata nome da cidade com iniciais maiúsculas
                city_name = " ".join([w.capitalize() for w in city_key.split()])
                return f"{city_name} - {c_uf}", c_lat, c_lon

    # 2. Tenta extrair padrões comuns como "Prefeitura de X", "Câmara de X"
    match = re.search(r'(?:prefeitura|camara|municipio|saae)\s+(?:municipal\s+)?(?:de\s+|da\s+|do\s+)?([a-z\s]{3,30})', norm_combined)
    if match:
        extracted = match.group(1).split()[0:3]
        candidate_city = " ".join(extracted).strip()
        for city_key, (c_lat, c_lon, c_uf) in BRAZILIAN_CITIES.items():
            if city_key in candidate_city or candidate_city in city_key:
                city_name = " ".join([w.capitalize() for w in city_key.split()])
                return f"{city_name} - {c_uf}", c_lat, c_lon
        
        # Nome extraído mas sem coordenadas exatas -> usa centroide do estado
        if uf_upper in UF_CENTROIDS:
            f_lat, f_lon, f_name = UF_CENTROIDS[uf_upper]
            return f"{" ".join(w.capitalize() for w in candidate_city.split())} - {uf_upper}", f_lat, f_lon

    # 3. Fallback para Centroide / Capital do Estado
    if uf_upper in UF_CENTROIDS:
        f_lat, f_lon, f_name = UF_CENTROIDS[uf_upper]
        return f"{f_name} - {uf_upper}", f_lat, f_lon

    # 4. Fallback final para Brasília (Federal)
    f_lat, f_lon, f_name = UF_CENTROIDS["NACIONAL"]
    return "Nacional / Brasil", f_lat, f_lon


def resolve_user_location(city_query: str) -> Optional[Tuple[str, float, float]]:
    """Resolve o nome ou CEP digitado pelo usuário para coordenadas (lat, lon)."""
    # 1. Suporte a CEP brasileiro (8 dígitos numéricos, ex: 18400-350 ou 18400350)
    clean_cep = re.sub(r'[^0-9]', '', city_query)
    if len(clean_cep) == 8:
        try:
            import urllib.request
            import json
            req = urllib.request.Request(
                f"https://viacep.com.br/ws/{clean_cep}/json/",
                headers={"User-Agent": "MonitorConcursos/1.0"}
            )
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                if not data.get("erro") and data.get("localidade"):
                    city = data["localidade"]
                    uf = data.get("uf", "SP")
                    loc = resolve_user_location(f"{city} {uf}")
                    if loc:
                        bairro_txt = f" - {data['bairro']}" if data.get('bairro') else ""
                        return f"{city} - {uf} ({clean_cep[:5]}-{clean_cep[5:]}{bairro_txt})", loc[1], loc[2]
        except Exception:
            pass

    # 2. Busca na base local de cidades conhecidas
    norm = normalize_city_name(city_query)
    for city_key, (lat, lon, uf) in BRAZILIAN_CITIES.items():
        if city_key == norm or city_key in norm:
            city_name = " ".join([w.capitalize() for w in city_key.split()])
            return f"{city_name} - {uf}", lat, lon

    # 3. Geocodificação online via OpenStreetMap Nominatim para municípios não catalogados
    if len(norm) >= 3 and not norm.isdigit():
        try:
            import urllib.request
            import urllib.parse
            import json
            encoded = urllib.parse.quote(f"{city_query}, Brasil")
            req = urllib.request.Request(
                f"https://nominatim.openstreetmap.org/search?q={encoded}&format=json&limit=1&countrycodes=br",
                headers={"User-Agent": "MonitorConcursosApp/1.0 (dev@monitor.local)"}
            )
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                geo_list = json.loads(resp.read().decode('utf-8'))
                if geo_list and len(geo_list) > 0:
                    first = geo_list[0]
                    lat = float(first["lat"])
                    lon = float(first["lon"])
                    display_city = first.get("display_name", city_query).split(",")[0].strip()
                    return f"{display_city} (Brasil)", lat, lon
        except Exception:
            pass

    # 4. Fallback para UF se digitou estado
    for uf, (lat, lon, name) in UF_CENTROIDS.items():
        if uf.lower() == norm or normalize_city_name(name) in norm:
            return f"{name} - {uf}", lat, lon

    return None
