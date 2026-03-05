"""
core/algorithm.py
-----------------
Funções de geração da população inicial do Algoritmo Genético.

Requisitos atendidos (PDF – Projeto 2):
  - Representação genética adequada para rotas: cada cromossomo é uma
    lista de IDs de pontos de entrega (permutação), representando a
    ordem em que o(s) veículo(s) deve(m) visitar as cidades.
  - População inicial híbrida para acelerar a convergência:
      * generate_random_population1  → 30% aleatório (diversidade)
      * generate_nearest_neighbour   → 30% vizinho mais próximo (qualidade local)
      * generate_convex_like         → 40% varredura angular (boa estrutura geográfica)
"""

import random
import math
from typing import List
from domain.problem import VRPProblem


def generate_random_population1(problem: VRPProblem, size: int) -> List[List[int]]:
    """
    Gera cromossomos completamente aleatórios.
    Garante diversidade genética alta na população inicial.

    Parâmetros:
        problem : instância do VRPProblem
        size    : número de indivíduos a gerar

    Retorno:
        lista de cromossomos (permutações aleatórias dos IDs)
    """
    ids = [p.id for p in problem.delivery_points]
    population = []
    for _ in range(size):
        chromosome = ids[:]
        random.shuffle(chromosome)
        population.append(chromosome)
    return population


def generate_nearest_neighbour(problem: VRPProblem, size: int) -> List[List[int]]:
    """
    Gera cromossomos usando a heurística do vizinho mais próximo.
    Produz soluções iniciais com boa qualidade local, reduzindo o
    tempo de convergência do AG.

    A cada indivíduo, escolhe um ponto de partida aleatório e
    sempre visita o ponto não visitado mais próximo.

    Parâmetros:
        problem : instância do VRPProblem
        size    : número de indivíduos a gerar

    Retorno:
        lista de cromossomos ordenados por proximidade geográfica
    """
    population = []
    for _ in range(size):
        unvisited = problem.delivery_points[:]
        current   = random.choice(unvisited)
        route     = [current.id]
        unvisited.remove(current)

        while unvisited:
            next_point = min(
                unvisited,
                key=lambda p: (p.x - current.x) ** 2 + (p.y - current.y) ** 2
            )
            route.append(next_point.id)
            unvisited.remove(next_point)
            current = next_point

        population.append(route)
    return population


def generate_convex_like(problem: VRPProblem, size: int) -> List[List[int]]:
    """
    Gera cromossomos ordenando os pontos por ângulo polar em relação
    ao centroide da nuvem de cidades (varredura angular).

    Produz soluções sem cruzamentos de arestas, próximas de rotas
    convexas — boa estrutura geográfica para o TSP/VRP.

    Parâmetros:
        problem : instância do VRPProblem
        size    : número de indivíduos a gerar

    Retorno:
        lista de cromossomos ordenados angularmente
    """
    pts = problem.delivery_points
    cx  = sum(p.x for p in pts) / len(pts)
    cy  = sum(p.y for p in pts) / len(pts)

    sorted_points = sorted(pts, key=lambda p: math.atan2(p.y - cy, p.x - cx))
    base_route    = [p.id for p in sorted_points]

    return [base_route[:] for _ in range(size)]
