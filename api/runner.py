"""
api/runner.py
-------------
Executa o Algoritmo Genético sem Pygame (headless).
Retorna as rotas otimizadas, métricas e chama a LLM ao convergir.

Usado pela API FastAPI como função chamada em thread separada.
"""

import math
import random
import threading
import time
from typing import List, Dict, Any, Callable, Optional

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from benchmark_greater_sp import greater_sp_cities
from core.algorithm import (
    generate_random_population1,
    generate_nearest_neighbour,
    generate_convex_like,
)
from core.fitness import calculo_fitness, two_opt
from domain.models import DeliveryPoint, Vehicle
from domain.problem import VRPProblem
from genetic_algorithm import order_crossover, mutate, sort_population
from vrp.decoder import VRPDecoder
from llm_report import generate_report


# ── Haversine ────────────────────────────────────────────────────────────────

def haversine_km(lat1, lon1, lat2, lon2) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dlon / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


def calc_total_km(routes, depot_name: str, city_geo: dict) -> float:
    total = 0.0
    dlat, dlon = city_geo[depot_name]
    for route in routes:
        prev_lat, prev_lon = dlat, dlon
        for stop in route.stops:
            slat, slon = city_geo[stop.name]
            total += haversine_km(prev_lat, prev_lon, slat, slon)
            prev_lat, prev_lon = slat, slon
        total += haversine_km(prev_lat, prev_lon, dlat, dlon)
    return total


def tournament_selection(population, fitness, k=3):
    candidates = random.sample(range(len(population)), k)
    best = min(candidates, key=lambda i: fitness[i])
    return population[best]


# ── Runner principal ──────────────────────────────────────────────────────────

def run_ag(
    config: Dict[str, Any],
    job: Dict[str, Any],          # objeto compartilhado de estado do job
    on_progress: Optional[Callable] = None,
):
    """
    Executa o AG completo de forma headless.

    Parâmetros:
        config      : dicionário com parâmetros do AG e da frota
        job         : dicionário compartilhado (status, progresso, resultado)
        on_progress : callback opcional chamado a cada geração
    """

    # ── Parâmetros ────────────────────────────────────────────────────────────
    POPULATION_SIZE = config.get("population_size", 100)
    TOURNAMENT_SIZE = config.get("tournament_size", 3)
    ELITE_SIZE      = config.get("elite_size", 5)
    STAGNATION_STOP = config.get("stagnation_stop", 400)
    MUTATION_START  = config.get("mutation_start", 0.30)
    MUTATION_MIN    = config.get("mutation_min", 0.05)
    RESTART_THRESHOLD = int(STAGNATION_STOP * 0.4)

    CITY_PRIORITY = {
        "São Paulo":       3,
        "Guarulhos":       3,
        "Santo André":     3,
        "Suzano":          3,
        "Mogi das Cruzes": 2,
        "Mauá":            2,
    }

    depot_name = config.get("depot", "Barueri")

    # ── Monta o problema ──────────────────────────────────────────────────────
    city_geo = {name: (lat, lon) for name, lat, lon in greater_sp_cities}

    delivery_points = []
    for i, (name, lat, lon) in enumerate(greater_sp_cities):
        if name == depot_name:
            continue
        delivery_points.append(DeliveryPoint(
            id=i + 1,
            name=name,
            x=lon,   # usamos lon/lat como coordenadas para distância euclidiana
            y=lat,
            demand=random.randint(5, 20),
            priority=CITY_PRIORITY.get(name, 1),
        ))

    depot_entry = next(
        (name, lat, lon) for name, lat, lon in greater_sp_cities if name == depot_name
    )
    depot = DeliveryPoint(
        id=0, name=depot_name,
        x=depot_entry[2], y=depot_entry[1],
        demand=0, priority=0,
    )

    vehicles_cfg = config.get("vehicles", [
        {"id": 1, "capacity": 150, "max_distance": 5.0},
        {"id": 2, "capacity": 150, "max_distance": 5.0},
        {"id": 3, "capacity": 500, "max_distance": 8.0},
    ])
    vehicles = [
        Vehicle(id=v["id"], capacity=v["capacity"], max_distance=v["max_distance"])
        for v in vehicles_cfg
    ]

    problem = VRPProblem(depot=depot, delivery_points=delivery_points, vehicles=vehicles)

    # ── População inicial ─────────────────────────────────────────────────────
    n_random = int(POPULATION_SIZE * 0.3)
    n_nn     = int(POPULATION_SIZE * 0.3)
    n_ch     = POPULATION_SIZE - n_random - n_nn

    population = (
        generate_random_population1(problem, n_random)
        + generate_nearest_neighbour(problem, n_nn)
        + generate_convex_like(problem, n_ch)
    )
    random.shuffle(population)

    fitness_values = [calculo_fitness(c, problem) for c in population]
    population, fitness_values = sort_population(population, fitness_values)

    best_global        = fitness_values[0]
    previous_global    = float('inf')
    best_global_km     = float('inf')
    best_solution_ever = population[0][:]
    sem_melhoria       = 0
    generation         = 0
    fitness_history    = []   # fitness por geração
    best_global_hist   = []   # melhor global acumulado
    km_history         = []   # km por geração
    best_km_history    = []   # melhor km acumulado

    job["status"]   = "running"
    job["progress"] = 0

    # ── Loop AG ───────────────────────────────────────────────────────────────
    while True:
        # Critério de parada
        if sem_melhoria >= STAGNATION_STOP:
            break
        if job.get("cancel"):
            job["status"] = "cancelled"
            return

        generation += 1

        # Melhora local no melhor
        population[0] = two_opt(population[0], problem)
        fitness_values[0] = calculo_fitness(population[0], problem)

        # Decoda rotas e calcula KM da geração atual
        decoder = VRPDecoder(problem)
        routes  = decoder.decode(population[0])
        km      = calc_total_km(routes, depot_name, city_geo)

        # Salva previous_global ANTES de atualizar — critério de parada correto
        previous_global = best_global

        # Rastreia melhor global — preserva melhor cromossomo
        if fitness_values[0] < best_global:
            best_global        = fitness_values[0]
            best_global_km     = km
            best_solution_ever = population[0][:]

        # Critério de parada: melhoria real no best_global
        if best_global < previous_global - 1e-6:
            sem_melhoria = 0
        else:
            sem_melhoria += 1

        fitness_history.append(round(fitness_values[0], 4))
        best_global_hist.append(round(best_global, 4))
        km_history.append(round(km, 1))
        best_km_history.append(round(best_global_km if best_global_km != float('inf') else km, 1))

        # Progresso (0–100%)
        progress = min(int(sem_melhoria / STAGNATION_STOP * 100), 99)
        job["progress"]         = progress
        job["generation"]       = generation
        job["best_fitness"]     = round(best_global, 4)
        job["current_fitness"]  = round(fitness_values[0], 4)
        job["current_km"]       = round(km, 1)
        job["best_km"]          = round(best_global_km if best_global_km != float('inf') else km, 1)
        job["sem_melhoria"]     = sem_melhoria
        job["fitness_history"]  = fitness_history
        job["best_global_hist"] = best_global_hist
        job["km_history"]       = km_history
        job["best_km_history"]  = best_km_history

        if on_progress:
            on_progress(job)

        # Elitismo + nova geração
        new_population = list(population[:ELITE_SIZE])

        stagnation_ratio = sem_melhoria / STAGNATION_STOP
        mutation_prob = MUTATION_MIN + (MUTATION_START - MUTATION_MIN) * stagnation_ratio
        mutation_prob = min(mutation_prob, MUTATION_START)

        if sem_melhoria > 0 and sem_melhoria % RESTART_THRESHOLD == 0:
            ids = [p.id for p in problem.delivery_points]
            for _ in range(POPULATION_SIZE // 2):
                c = ids[:]
                random.shuffle(c)
                new_population.append(c)

        while len(new_population) < POPULATION_SIZE:
            p1 = tournament_selection(population, fitness_values, TOURNAMENT_SIZE)
            p2 = tournament_selection(population, fitness_values, TOURNAMENT_SIZE)
            child = order_crossover(p1, p2)
            child = mutate(child, mutation_prob)

            if random.random() < 0.05:
                child = two_opt(child, problem)

            new_population.append(child)

        population     = new_population
        fitness_values = [calculo_fitness(c, problem) for c in population]
        population, fitness_values = sort_population(population, fitness_values)

    # ── Resultado final ───────────────────────────────────────────────────────
    decoder = VRPDecoder(problem)
    routes  = decoder.decode(population[0])
    km      = calc_total_km(routes, depot_name, city_geo)

    # Serializa rotas para JSON
    routes_json = []
    for route in routes:
        stops_json = []
        for stop in route.stops:
            lat, lon = city_geo[stop.name]
            stops_json.append({
                "id":       stop.id,
                "name":     stop.name,
                "lat":      lat,
                "lon":      lon,
                "demand":   stop.demand,
                "priority": stop.priority,
            })
        # coordenadas do depot para fechar a polyline
        dlat, dlon = city_geo[depot_name]
        routes_json.append({
            "vehicle_id": route.vehicle_id,
            "stops":      stops_json,
            "total_km":   round(build_route_km(route, depot_name, city_geo), 1),
            "total_load": sum(s.demand for s in route.stops),
            "depot":      {"lat": dlat, "lon": dlon, "name": depot_name},
        })

    # Gera relatório LLM
    try:
        llm_text = generate_report(
            routes=routes,
            problem=problem,
            city_geo=city_geo,
            depot_name=depot_name,
            generation=generation,
            best_fitness=best_global,
            total_km=km,
        )
    except Exception as e:
        llm_text = f"[Erro ao gerar relatório LLM: {e}]"

    job["status"]          = "done"
    job["progress"]        = 100
    job["generation"]      = generation
    job["best_fitness"]    = round(best_global, 4)
    job["total_km"]        = round(km, 1)
    job["routes"]          = routes_json
    job["fitness_history"] = fitness_history
    job["km_history"]      = km_history
    job["llm_report"]      = llm_text
    job["depot"]           = {
        "lat": city_geo[depot_name][0],
        "lon": city_geo[depot_name][1],
        "name": depot_name,
    }


def build_route_km(route, depot_name, city_geo):
    total = 0.0
    dlat, dlon = city_geo[depot_name]
    prev_lat, prev_lon = dlat, dlon
    for stop in route.stops:
        slat, slon = city_geo[stop.name]
        total += haversine_km(prev_lat, prev_lon, slat, slon)
        prev_lat, prev_lon = slat, slon
    total += haversine_km(prev_lat, prev_lon, dlat, dlon)
    return total
