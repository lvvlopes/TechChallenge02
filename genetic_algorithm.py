"""
genetic_algorithm.py
--------------------
Operadores genéticos do Algoritmo Genético para o VRP hospitalar.

Requisitos atendidos (PDF – Projeto 2):
  - Operadores genéticos especializados para problemas de roteamento:
      * order_crossover : crossover OX (Order Crossover) — preserva a
        ordem relativa dos genes, essencial para rotas válidas (sem
        visitar a mesma cidade duas vezes).
      * mutate          : mutação por troca de adjacentes (swap), com
        probabilidade adaptativa que diminui ao longo das gerações.
      * sort_population : ordenação por fitness para seleção e elitismo.
"""

import random
import copy
from typing import List, Tuple


def order_crossover(parent1: List[int], parent2: List[int]) -> List[int]:
    """
    Order Crossover (OX) — operador de cruzamento para problemas de
    permutação como TSP/VRP.

    Funcionamento:
      1. Copia um segmento contíguo aleatório de parent1 para o filho.
      2. Preenche as posições restantes com os genes de parent2 na
         ordem em que aparecem, ignorando os já presentes no filho.

    Essa estratégia garante que o filho seja uma permutação válida
    (cada ponto de entrega visitado exatamente uma vez).

    Parâmetros:
        parent1, parent2 : cromossomos pai (listas de IDs)

    Retorno:
        filho resultante do cruzamento
    """
    length = len(parent1)
    start  = random.randint(0, length - 1)
    end    = random.randint(start + 1, length)

    # Segmento herdado de parent1
    child = parent1[start:end]

    # Posições restantes preenchidas com genes de parent2 (sem repetição)
    remaining_positions = [i for i in range(length) if i < start or i >= end]
    remaining_genes     = [gene for gene in parent2 if gene not in child]

    for position, gene in zip(remaining_positions, remaining_genes):
        child.insert(position, gene)

    return child


def mutate(solution: List[int], mutation_probability: float) -> List[int]:
    """
    Mutação por troca de posições adjacentes (adjacent swap).

    Com probabilidade mutation_probability, dois genes consecutivos
    são trocados de posição. A taxa de mutação é adaptativa no loop
    principal: começa em 0.20 e decresce até 0.05 ao longo das gerações,
    incentivando exploração no início e refinamento no final.

    Parâmetros:
        solution            : cromossomo a ser mutado
        mutation_probability: probabilidade de ocorrer a mutação [0, 1]

    Retorno:
        cromossomo mutado (cópia — não altera o original)
    """
    mutated = copy.deepcopy(solution)

    if random.random() < mutation_probability:
        if len(solution) < 2:
            return solution
        index = random.randint(0, len(solution) - 2)
        mutated[index], mutated[index + 1] = solution[index + 1], solution[index]

    return mutated


def sort_population(
    population: List[List[int]],
    fitness: List[float]
) -> Tuple[List[List[int]], List[float]]:
    """
    Ordena a população pelo fitness em ordem crescente (menor = melhor).

    Usado após cada avaliação para:
      - Identificar o melhor indivíduo (elitismo)
      - Alimentar a seleção por torneio com índices corretos

    Parâmetros:
        population : lista de cromossomos
        fitness    : lista de valores de fitness correspondentes

    Retorno:
        tupla (população ordenada, fitness ordenado)
    """
    combined = sorted(zip(population, fitness), key=lambda x: x[1])
    sorted_pop, sorted_fit = zip(*combined)
    return list(sorted_pop), list(sorted_fit)
