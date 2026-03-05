"""
Baixa tiles do OpenStreetMap e monta imagem de fundo para o Pygame.
O mapa é cacheado em disco para não baixar a cada execução.
"""
import math
import os
import io
import hashlib
import requests
from PIL import Image

CACHE_DIR = os.path.join(os.path.dirname(__file__), ".map_cache")
TILE_SIZE = 256
USER_AGENT = "TSP-Hospital-FIAP/1.0"


def _lat_lon_to_tile(lat, lon, zoom):
    n = 2 ** zoom
    x = int((lon + 180) / 360 * n)
    lat_r = math.radians(lat)
    y = int((1 - math.log(math.tan(lat_r) + 1 / math.cos(lat_r)) / math.pi) / 2 * n)
    return x, y


def _tile_to_lat_lon(x, y, zoom):
    n = 2 ** zoom
    lon = x / n * 360 - 180
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))
    return lat, lon


def _download_tile(z, x, y):
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_path = os.path.join(CACHE_DIR, f"{z}_{x}_{y}.png")

    if os.path.exists(cache_path):
        return Image.open(cache_path).convert("RGB")

    url = f"https://tile.openstreetmap.org/{z}/{x}/{y}.png"
    headers = {"User-Agent": USER_AGENT}

    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        img = Image.open(io.BytesIO(r.content)).convert("RGB")
        img.save(cache_path)
        return img
    except Exception as e:
        print(f"[map] Aviso: não foi possível baixar tile {z}/{x}/{y}: {e}")
        return Image.new("RGB", (TILE_SIZE, TILE_SIZE), (240, 240, 240))


def build_background(cities, screen_width, screen_height,
                     x_offset, node_radius, zoom=10):
    """
    Monta imagem PIL do mapa de fundo alinhada com as coordenadas
    projetadas em project_cities_to_screen().

    Retorna (pygame.Surface, offset_x_px, offset_y_px) onde os offsets
    indicam quanto a imagem foi deslocada (sempre 0 nesta implementação,
    pois o crop é feito para o tamanho exato da tela).
    """
    import pygame

    lats = [lat for _, lat, _ in cities]
    lons = [lon for _, _, lon in cities]
    min_lat, max_lat = min(lats), max(lats)
    min_lon, max_lon = min(lons), max(lons)

    # margem de 10%
    lat_margin = (max_lat - min_lat) * 0.1
    lon_margin = (max_lon - min_lon) * 0.1
    min_lat -= lat_margin
    max_lat += lat_margin
    min_lon -= lon_margin
    max_lon += lon_margin

    # tiles necessários
    x_min, y_max = _lat_lon_to_tile(min_lat, min_lon, zoom)
    x_max, y_min = _lat_lon_to_tile(max_lat, max_lon, zoom)

    # monta mosaico
    n_tiles_x = x_max - x_min + 1
    n_tiles_y = y_max - y_min + 1
    mosaic = Image.new("RGB",
                       (n_tiles_x * TILE_SIZE, n_tiles_y * TILE_SIZE),
                       (240, 240, 240))

    print(f"[map] Baixando {n_tiles_x * n_tiles_y} tiles (zoom={zoom})...")
    for tx in range(x_min, x_max + 1):
        for ty in range(y_min, y_max + 1):
            tile = _download_tile(zoom, tx, ty)
            px = (tx - x_min) * TILE_SIZE
            py = (ty - y_min) * TILE_SIZE
            mosaic.paste(tile, (px, py))

    # coordenadas lat/lon do canto superior-esquerdo do mosaico
    mosaic_lat_top, mosaic_lon_left = _tile_to_lat_lon(x_min, y_min, zoom)
    mosaic_lat_bot, mosaic_lon_right = _tile_to_lat_lon(x_max + 1, y_max + 1, zoom)

    mosaic_w, mosaic_h = mosaic.size

    # função de projeção igual à usada em project_cities_to_screen
    usable_w = screen_width - x_offset - 2 * node_radius
    usable_h = screen_height - 2 * node_radius

    # escala: quantos pixels de tela por grau
    screen_deg_lon = max_lon - min_lon
    screen_deg_lat = max_lat - min_lat

    scale_x = usable_w / screen_deg_lon   # px_tela / grau_lon
    scale_y = usable_h / screen_deg_lat   # px_tela / grau_lat

    # escala do mosaico: px_mosaico / grau
    mosaic_deg_lon = mosaic_lon_right - mosaic_lon_left
    mosaic_deg_lat = mosaic_lat_top - mosaic_lat_bot   # top > bot (lat norte > sul)
    mosaic_scale_x = mosaic_w / mosaic_deg_lon
    mosaic_scale_y = mosaic_h / mosaic_deg_lat

    # tamanho final do mapa em pixels de tela
    final_w = int(mosaic_w * scale_x / mosaic_scale_x)
    final_h = int(mosaic_h * scale_y / mosaic_scale_y)

    resized = mosaic.resize((final_w, final_h), Image.LANCZOS)

    # offset para alinhar min_lon com x_offset + node_radius na tela
    off_lon = (min_lon - mosaic_lon_left) * scale_x
    off_lat = (mosaic_lat_top - max_lat) * scale_y   # top da tela = max_lat

    paste_x = int(x_offset + node_radius - off_lon)
    paste_y = int(node_radius - off_lat)

    # canvas do tamanho da tela
    canvas = Image.new("RGB", (screen_width, screen_height), (255, 255, 255))
    canvas.paste(resized, (paste_x, paste_y))

    # PIL -> pygame Surface
    mode = canvas.mode
    data = canvas.tobytes()
    surface = pygame.image.fromstring(data, canvas.size, mode)

    return surface
