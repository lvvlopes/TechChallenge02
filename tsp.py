"""
tsp.py
------
Entry point do sistema de otimização de rotas para distribuição de
medicamentos e insumos na Região Metropolitana de São Paulo (RMSP).

Este módulo implementa o loop principal do Algoritmo Genético para o
Problema de Roteamento de Veículos (VRP), integrando:
  - Geração e evolução da população de soluções
  - Decodificação do cromossomo em rotas reais
  - Visualização em tempo real via Pygame com mapa OSM de fundo

Requisitos atendidos (PDF – Projeto 2):
  - Sistema de otimização de rotas via AG (TSP/VRP)
  - Restrições realistas: capacidade, autonomia, múltiplos veículos,
    prioridades de entrega
  - Operadores genéticos: seleção por torneio, crossover OX, mutação
    adaptativa, elitismo (top-3), refinamento 2-opt
  - Visualização das rotas otimizadas em mapa geográfico real (OSM)
  - Distância exibida em KM reais via fórmula de Haversine

Para executar:
    python tsp.py

Controles:
    Q / fechar janela → encerra a execução
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pygame
from pygame.locals import *
import random
import itertools
import math

from core.algorithm import generate_random_population1, generate_nearest_neighbour, generate_convex_like
from core.fitness import calculo_fitness, two_opt
from genetic_algorithm import mutate, order_crossover, sort_population
from draw_functions import draw_plot, draw_routes, ROUTE_COLORS_RGB
from benchmark_greater_sp import greater_sp_cities, project_cities_to_screen
from domain.models import DeliveryPoint, Vehicle
from domain.problem import VRPProblem
from vrp.decoder import VRPDecoder
from map_background import build_background


# ── Configurações Pygame ──────────────────────────────────────────────────────
WIDTH, HEIGHT = 1500, 800   # dimensões da janela
NODE_RADIUS   = 10           # raio dos círculos dos pontos no mapa
FPS           = 30           # frames por segundo
PLOT_X_OFFSET = 450          # largura reservada para os gráficos (lado esquerdo)

# ── Configurações do Algoritmo Genético ───────────────────────────────────────
POPULATION_SIZE = 100   # tamanho da população
TOURNAMENT_SIZE = 3     # torneio menor = menos pressão seletiva, mais diversidade
ELITE_SIZE      = 5     # elitismo baixo: preserva bons mas não estagna
STAGNATION_STOP = 400   # gerações sem melhoria no MELHOR para encerrar
MUTATION_START  = 0.30  # mutação inicial alta para explorar espaço
MUTATION_MIN    = 0.05  # mutação mínima mantém diversidade mesmo no final


# ── Funções auxiliares ────────────────────────────────────────────────────────

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calcula a distância real em quilômetros entre dois pontos
    geográficos usando a fórmula de Haversine.

    Usado para converter distâncias de pixels para KM reais no gráfico.
    """
    R    = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a    = (math.sin(dlat / 2) ** 2
            + math.cos(math.radians(lat1))
            * math.cos(math.radians(lat2))
            * math.sin(dlon / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


def calc_route_km(routes, depot_name: str, city_geo: dict) -> float:
    """
    Soma a distância total de todas as rotas da solução em KM reais,
    usando as coordenadas geográficas reais (lat/lon) de cada cidade.

    Parâmetros:
        routes     : lista de Route gerada pelo VRPDecoder
        depot_name : nome da cidade depósito
        city_geo   : dicionário {nome: (lat, lon)}
    """
    total_km   = 0.0
    dlat, dlon = city_geo[depot_name]
    for route in routes:
        prev_lat, prev_lon = dlat, dlon
        for stop in route.stops:
            slat, slon = city_geo[stop.name]
            total_km  += haversine_km(prev_lat, prev_lon, slat, slon)
            prev_lat, prev_lon = slat, slon
        total_km += haversine_km(prev_lat, prev_lon, dlat, dlon)
    return total_km


def tournament_selection(population, fitness, k: int = TOURNAMENT_SIZE):
    """
    Seleção por torneio: escolhe k indivíduos aleatórios e retorna
    o de menor fitness.

    Requisito atendido: operador de seleção especializado para VRP.
    """
    indices = random.sample(range(len(population)), k)
    best    = min(indices, key=lambda i: fitness[i])
    return population[best]


# ── Construção do problema VRP ────────────────────────────────────────────────

# Projeta as coordenadas lat/lon das 39 cidades da RMSP para pixels de tela
cities_locations = project_cities_to_screen(
    greater_sp_cities, width=WIDTH, height=HEIGHT,
    x_offset=PLOT_X_OFFSET, node_radius=NODE_RADIUS,
)

depot_name = "Barueri"   # cidade que serve como depósito central

# Mapas auxiliares para lookup rápido
city_map = {name: coord for (name, _, _), coord in zip(greater_sp_cities, cities_locations)}
city_geo = {name: (lat, lon) for name, lat, lon in greater_sp_cities}

# Cria o nó depósito (demand=0, priority=0 pois não é ponto de entrega)
depot_x, depot_y = city_map[depot_name]
depot = DeliveryPoint(id=0, name=depot_name, x=depot_x, y=depot_y, demand=0, priority=0)

# Prioridades fixas por cidade — definidas conforme necessidade hospitalar
# 3 = crítica  (medicamentos essenciais — visitar o mais cedo possível)
# 2 = alta     (entregas importantes)
# 1 = normal   (insumos regulares — default para cidades não listadas)
CITY_PRIORITY = {
    "São Paulo":       3,
    "Guarulhos":       3,
    "Santo André":     3,
    "Suzano":          3,
    "Mogi das Cruzes": 2,
    "Mauá":            2,
}

# Cria os pontos de entrega com demandas simuladas e prioridades fixas
# Em produção as demandas também viriam de um sistema hospitalar real
delivery_points = []
for idx, ((name, _, _), (x, y)) in enumerate(zip(greater_sp_cities, cities_locations), start=1):
    if name == depot_name:
        continue
    delivery_points.append(DeliveryPoint(
        id=idx, name=name, x=x, y=y,
        demand=random.randint(5, 20),          # unidades de medicamento/insumo
        priority=CITY_PRIORITY.get(name, 1),   # prioridade fixa por cidade
    ))

# Define a frota de veículos com restrições realistas
# Requisito: capacidade limitada, autonomia limitada, múltiplos veículos
vehicles = [
    Vehicle(id=1, capacity=150, max_distance=5000),  # veículo leve
    Vehicle(id=2, capacity=150, max_distance=5000),  # veículo leve
    Vehicle(id=3, capacity=500, max_distance=8000),  # veículo pesado / regional
]

problem = VRPProblem(depot=depot, delivery_points=delivery_points, vehicles=vehicles)


# ── Inicialização do Pygame ───────────────────────────────────────────────────
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("VRP — Distribuição de Medicamentos RMSP")
clock             = pygame.time.Clock()
generation_counter = itertools.count(start=1)

# Carrega mapa de fundo OpenStreetMap
# Na 1ª execução: baixa ~20 tiles e salva em .map_cache/
# Execuções seguintes: carrega do cache (instantâneo)
print("[map] Carregando mapa de fundo...")
try:
    map_surface = build_background(
        greater_sp_cities, screen_width=WIDTH, screen_height=HEIGHT,
        x_offset=PLOT_X_OFFSET, node_radius=NODE_RADIUS, zoom=10,
    )
    print("[map] Mapa carregado.")
except Exception as e:
    print(f"[map] Sem mapa de fundo: {e}")
    map_surface = None


# ── População inicial híbrida ─────────────────────────────────────────────────
# Requisito: diferentes estratégias de inicialização para balancear
# diversidade (aleatório) e qualidade inicial (heurísticas)
n_random = int(POPULATION_SIZE * 0.3)             # 30% aleatório
n_nn     = int(POPULATION_SIZE * 0.3)             # 30% nearest neighbour
n_ch     = POPULATION_SIZE - n_random - n_nn      # 40% convex-like

population = (
    generate_random_population1(problem, n_random)
    + generate_nearest_neighbour(problem, n_nn)
    + generate_convex_like(problem, n_ch)
)


# ── Loop principal do Algoritmo Genético ──────────────────────────────────────
best_fitness_values = []   # histórico de fitness para o gráfico
best_km_values      = []   # histórico de KM reais para o gráfico
best_global         = float('inf')  # melhor fitness já encontrado (global)
sem_melhoria        = 0             # gerações sem melhorar o melhor global
WHITE               = (255, 255, 255)

running = True
while running:

    # Eventos Pygame
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_q:
            running = False

    generation = next(generation_counter)

    # Fundo: mapa OSM ou branco se offline
    screen.blit(map_surface, (0, 0)) if map_surface else screen.fill(WHITE)

    # ── Avaliação do fitness ──────────────────────────────────────────────────
    # Calcula fitness para toda a população e ordena (menor = melhor)
    population_fitness = [calculo_fitness(ind, problem) for ind in population]
    population, population_fitness = sort_population(population, population_fitness)

    # Refinamento local 2-opt no melhor indivíduo da geração
    population[0] = two_opt(population[0], problem)

    best_solution = population[0]
    best_fitness  = calculo_fitness(best_solution, problem)

    # Decodifica o melhor cromossomo em rotas reais para visualização
    decoder = VRPDecoder(problem)
    routes  = decoder.decode(best_solution)

    # Registra histórico para os gráficos
    best_fitness_values.append(best_fitness)
    best_km_values.append(calc_route_km(routes, depot_name, city_geo))

    # ── Visualização ──────────────────────────────────────────────────────────
    # Painel esquerdo: gráfico de fitness + gráfico de KM com legenda de veículos
    draw_plot(
        screen,
        list(range(len(best_fitness_values))),
        best_fitness_values,
        y_km=best_km_values,
        routes=routes,
        y_label="Fitness (norm.)",
    )

    # Rotas coloridas no mapa (cada veículo tem sua cor)
    draw_routes(screen, routes, problem.depot)

    # Labels das paradas: "Nº°VX NomeCidade" na cor do veículo
    font      = pygame.font.SysFont("Arial", 15, bold=True)
    font_small = pygame.font.SysFont("Arial", 13, bold=True)

    vehicle_color_map = {}
    cidx              = 0
    for route in routes:
        if route.vehicle_id not in vehicle_color_map:
            vehicle_color_map[route.vehicle_id] = cidx
            cidx += 1

    def draw_label(surface, text, x, y, text_color):
        """Renderiza label com fundo branco semitransparente para legibilidade."""
        label = font_small.render(text, True, text_color)
        w, h  = label.get_size()
        pad   = 2
        bg    = pygame.Surface((w + pad * 2, h + pad * 2), pygame.SRCALPHA)
        bg.fill((255, 255, 255, 175))  # branco 68% opaco
        surface.blit(bg,    (x - pad, y - pad))
        surface.blit(label, (x, y))

    for route in routes:
        text_color = ROUTE_COLORS_RGB[vehicle_color_map[route.vehicle_id] % len(ROUTE_COLORS_RGB)]
        for i, stop in enumerate(route.stops):
            pygame.draw.circle(screen, (0, 0, 0), (stop.x, stop.y), 7)
            pygame.draw.circle(screen, text_color,  (stop.x, stop.y), 5)
            draw_label(screen, f"{i+1}°V{route.vehicle_id} {stop.name}",
                       stop.x + 8, stop.y - 9, text_color)

    # Depósito destacado em verde com label
    pygame.draw.circle(screen, (0, 150, 0), (problem.depot.x, problem.depot.y), 12)
    pygame.draw.circle(screen, (255, 255, 255), (problem.depot.x, problem.depot.y), 6)
    draw_label(screen, f"⬤ {problem.depot.name}",
               problem.depot.x + 14, problem.depot.y - 9, (0, 120, 0))

    print(f"Gen {generation:4d} | Fitness: {best_fitness:.4f} | KM: {best_km_values[-1]:.1f} | Melhor: {best_global:.4f} ({sem_melhoria} sem melhoria)")

    # ── Critério de parada: sem melhoria no melhor global ─────────────────────
    if best_fitness < best_global - 1e-6:
        best_global   = best_fitness
        sem_melhoria  = 0
    else:
        sem_melhoria += 1

    if sem_melhoria >= STAGNATION_STOP:
        print(f"Convergiu após {generation} gerações — melhor fitness: {best_global:.4f}")
        running = False

    # ── Nova geração ──────────────────────────────────────────────────────────
    # Elitismo: preserva os ELITE_SIZE melhores indivíduos
    new_population = list(population[:ELITE_SIZE])

    # Taxa de mutação adaptativa: sobe quando há estagnação (fuga de ótimo local)
    # e desce quando há melhoria consistente (refinamento fino)
    stagnation_ratio = sem_melhoria / STAGNATION_STOP
    mutation_prob = MUTATION_MIN + (MUTATION_START - MUTATION_MIN) * stagnation_ratio
    mutation_prob = min(mutation_prob, MUTATION_START)

    # ── Reinicialização parcial quando a população estagna muito ──────────────
    # Se ficou 40% do limite sem melhoria, substitui metade da população
    # por novos indivíduos aleatórios — escapa do ótimo local
    RESTART_THRESHOLD = int(STAGNATION_STOP * 0.4)
    if sem_melhoria > 0 and sem_melhoria % RESTART_THRESHOLD == 0:
        n_restart = POPULATION_SIZE // 2
        print(f"[restart] Reinicializando {n_restart} indivíduos para escapar do ótimo local...")
        new_population.extend(generate_random_population1(problem, n_restart))

    while len(new_population) < POPULATION_SIZE:
        # Seleção por torneio para os dois pais
        parent1 = tournament_selection(population, population_fitness)
        parent2 = tournament_selection(population, population_fitness)

        # Crossover OX + mutação adaptativa
        child = order_crossover(parent1, parent2)
        child = mutate(child, mutation_prob)

        # 2-opt nos filhos desativado — muito lento com populações grandes
        # O 2-opt é aplicado apenas no melhor indivíduo de cada geração (acima)

        new_population.append(child)

    population = new_population

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()
sys.exit()
