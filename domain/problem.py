"""
domain/problem.py
-----------------
Define o problema VRP (Vehicle Routing Problem) hospitalar.

Requisito atendido (PDF – Projeto 2):
  - Múltiplos veículos disponíveis (VRP): a classe agrega depot, pontos
    de entrega e frota de veículos em uma única estrutura de problema.
  - get_point() usa dicionário interno para acesso O(1) por ID,
    necessário para decodificação eficiente do cromossomo.
"""

from typing import List
from .models import DeliveryPoint, Vehicle


class VRPProblem:
    """
    Encapsula todos os dados do problema de roteamento de veículos.

    Atributos:
        depot            : ponto de partida/retorno de todos os veículos
        delivery_points  : lista de pontos de entrega a serem visitados
        vehicles         : frota de veículos disponíveis
        point_map        : dicionário {id -> DeliveryPoint} para acesso rápido
    """

    def __init__(
        self,
        depot:            DeliveryPoint,
        delivery_points:  List[DeliveryPoint],
        vehicles:         List[Vehicle],
    ):
        self.depot           = depot
        self.delivery_points = delivery_points
        self.vehicles        = vehicles
        # índice para lookup O(1) durante a decodificação do cromossomo
        self.point_map = {p.id: p for p in delivery_points}

    def get_point(self, pid: int) -> DeliveryPoint:
        """Retorna o DeliveryPoint pelo seu ID."""
        return self.point_map[pid]
