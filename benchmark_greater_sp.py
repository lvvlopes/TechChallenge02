"""Dataset with municipalities from Greater São Paulo (RMSP)."""

# (city_name, latitude, longitude)
# Coordinates are approximate city-center values.
greater_sp_cities = [
    ("Arujá", -23.3964, -46.3200),
    ("Barueri", -23.5110, -46.8760),
    ("Biritiba-Mirim", -23.5720, -46.0410),
    ("Caieiras", -23.3640, -46.7400),
    ("Cajamar", -23.3550, -46.8760),
    ("Carapicuíba", -23.5230, -46.8400),
    ("Cotia", -23.6030, -46.9190),
    ("Diadema", -23.6860, -46.6230),
    ("Embu das Artes", -23.6500, -46.8520),
    ("Embu-Guaçu", -23.8320, -46.8130),
    ("Ferraz de Vasconcelos", -23.5400, -46.3690),
    ("Francisco Morato", -23.2810, -46.7450),
    ("Franco da Rocha", -23.3220, -46.7260),
    ("Guararema", -23.4150, -46.0360),
    ("Guarulhos", -23.4540, -46.5340),
    ("Itapecerica da Serra", -23.7170, -46.8490),
    ("Itapevi", -23.5480, -46.9340),
    ("Itaquaquecetuba", -23.4860, -46.3480),
    ("Jandira", -23.5270, -46.9020),
    ("Juquitiba", -23.9240, -47.0690),
    ("Mairiporã", -23.3180, -46.5860),
    ("Mauá", -23.6680, -46.4610),
    ("Mogi das Cruzes", -23.5230, -46.1880),
    ("Osasco", -23.5320, -46.7910),
    ("Pirapora do Bom Jesus", -23.3960, -47.0020),
    ("Poá", -23.5290, -46.3450),
    ("Ribeirão Pires", -23.7100, -46.4140),
    ("Rio Grande da Serra", -23.7440, -46.3990),
    ("Salesópolis", -23.5330, -45.8460),
    ("Santa Isabel", -23.3150, -46.2210),
    ("Santana de Parnaíba", -23.4440, -46.9170),
    ("Santo André", -23.6630, -46.5380),
    ("São Bernardo do Campo", -23.6940, -46.5650),
    ("São Caetano do Sul", -23.6230, -46.5510),
    ("São Lourenço da Serra", -23.8510, -46.9430),
    ("São Paulo", -23.5505, -46.6333),
    ("Suzano", -23.5430, -46.3110),
    ("Taboão da Serra", -23.6260, -46.7910),
    ("Vargem Grande Paulista", -23.6030, -47.0240),
]


def project_cities_to_screen(cities, width, height, x_offset, node_radius):
    """Project lat/lon coordinates into screen coordinates."""
    lats = [lat for _, lat, _ in cities]
    lons = [lon for _, _, lon in cities]

    min_lat, max_lat = min(lats), max(lats)
    min_lon, max_lon = min(lons), max(lons)

    usable_width = width - x_offset - (2 * node_radius)
    usable_height = height - (2 * node_radius)

    projected = []
    for _, lat, lon in cities:
        # Longitude maps left-to-right.
        x = x_offset + node_radius + int(((lon - min_lon) / (max_lon - min_lon)) * usable_width)
        # Latitude maps top-to-bottom inversely (north on top).
        y = node_radius + int(((max_lat - lat) / (max_lat - min_lat)) * usable_height)
        projected.append((x, y))

    return projected
