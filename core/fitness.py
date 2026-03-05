"""
core/fitness.py
---------------
Função de fitness e refinamento local (2-opt) para o VRP hospitalar.

Requisitos atendidos (PDF – Projeto 2):
  - Função fitness que considera distância, prioridade de entregas e
    outras restrições relevantes:
      * w_distance (0.55): minimiza a distância total percorrida
      * w_priority (0.15): penaliza entregas críticas visitadas tarde
      * w_balance  (0.05): incentiva balanceamento de carga entre rotas
      * w_routes   (0.25): penaliza fragmentação excessiva de viagens
  - Todos os componentes são normalizados antes de combinar, garantindo
    que nenhuma métrica domine por diferença de escala.
  - Refinamento local 2-opt aplicado ao melhor indivíduo de cada geração
    e a 5% da nova população, melhorando a qualidade sem custo genético.
"""

from vrp.decoder import VRPDecoder
import math
from typing import List
from domain.problem import VRPProblem


def calculo_fitness(chromosome: List[int], problem: VRPProblem) -> float:
    """
    Calcula o fitness de um cromossomo para o VRP hospitalar.

    O fitness é uma combinação ponderada e normalizada de quatro componentes:
      1. Distância total percorrida por todos os veículos
      2. Penalidade de prioridade: cidades críticas visitadas tarde custam mais
      3. Variância de carga entre rotas: incentiva balanceamento
      4. Número de rotas: penaliza fragmentação (muitas viagens curtas)

    Menor fitness = melhor solução.

    Parâmetros:
        chromosome : permutação de IDs de pontos de entrega
        problem    : instância do VRPProblem com depot, pontos e veículos

    Retorno:
        valor escalar de fitness (float, quanto menor melhor)
    """
    decoder  = VRPDecoder(problem)
    routes   = decoder.decode(chromosome)

    total_distance        = 0.0
    priority_penalty      = 0.0
    load_variance_penalty = 0.0
    n_routes              = len(routes)
    loads                 = []

    for route in routes:
        last          = problem.depot
        route_dist    = 0.0
        route_load    = 0

        for position, stop in enumerate(route.stops):
            # Distância ao próximo ponto
            dist = math.sqrt((last.x - stop.x) ** 2 + (last.y - stop.y) ** 2)
            route_dist += dist

            # Penalidade de prioridade: posição relativa * prioridade
            # (0.0 = primeira parada, 1.0 = última parada)
            # Entregas críticas (priority=3) no final da rota são mais penalizadas
            rel_pos = position / max(len(route.stops) - 1, 1)
            priority_penalty += rel_pos * stop.priority

            route_load += stop.demand
            last = stop

        # Retorno ao depósito
        route_dist += math.sqrt(
            (last.x - problem.depot.x) ** 2 + (last.y - problem.depot.y) ** 2
        )
        total_distance += route_dist
        loads.append(route_load)

    # Variância de carga entre rotas (incentiva distribuição uniforme)
    if loads:
        avg_load = sum(loads) / len(loads)
        load_variance_penalty = sum((l - avg_load) ** 2 for l in loads)

    # ── Normalização ─────────────────────────────────────────────────────────
    n_points = len(problem.delivery_points)

    # Distância normalizada pela distância média esperada (n_cidades × 150px)
    norm_dist   = total_distance / (n_points * 150)

    # Prioridade normalizada pelo máximo possível (todas críticas na última pos.)
    norm_pri    = priority_penalty / (n_points * 3)

    # Variância normalizada pela variância máxima possível
    max_demand  = sum(p.demand for p in problem.delivery_points)
    norm_bal    = load_variance_penalty / max(max_demand ** 2, 1)

    # Fragmentação: razão entre nº de rotas e nº de cidades
    norm_routes = n_routes / n_points

    # ── Pesos (ajustáveis conforme necessidade operacional) ───────────────────
    w_distance = 0.55   # distância é o objetivo principal
    w_priority = 0.15   # garantir entregas críticas no início das rotas
    w_balance  = 0.05   # equilíbrio de carga entre veículos
    w_routes   = 0.25   # evitar fragmentação excessiva de viagens

    return (
        w_distance * norm_dist
        + w_priority * norm_pri
        + w_balance  * norm_bal
        + w_routes   * norm_routes
    )


def two_opt(route: List[int], problem: VRPProblem, max_iter: int = 5) -> List[int]:
    """
    Refinamento local 2-opt: melhora iterativamente a ordem de visita
    revertendo segmentos do cromossomo que reduzam a distância total.

    O 2-opt é aplicado:
      - Ao melhor indivíduo de cada geração (sempre)
      - A 5% dos filhos gerados (aleatoriamente)

    Parâmetros:
        route    : cromossomo a ser otimizado
        problem  : instância do VRPProblem
        max_iter : número máximo de passagens sem melhoria

    Retorno:
        cromossomo otimizado (igual ou melhor que o original)
    """
    best = route[:]

    for _ in range(max_iter):
        improved = False

        for i in range(1, len(best) - 2):
            for j in range(i + 1, len(best)):
                if j - i == 1:
                    continue  # troca adjacente — sem efeito no 2-opt

                # Testa reversão do segmento [i:j]
                candidate = best[:]
                candidate[i:j] = reversed(best[i:j])

                if route_distance(candidate, problem) < route_distance(best, problem):
                    best     = candidate
                    improved = True
                    break

            if improved:
                break

        if not improved:
            break  # convergiu localmente

    return best


def route_distance(route: List[int], problem: VRPProblem) -> float:
    """
    Calcula a distância euclidiana total de um cromossomo (sem considerar
    as restrições de capacidade/autonomia — apenas a sequência de visitas).

    Usado internamente pelo 2-opt para comparar variantes de rota.
    """
    distance = 0.0
    for i in range(len(route) - 1):
        a = problem.get_point(route[i])
        b = problem.get_point(route[i + 1])
        distance += math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2)
    return distance
