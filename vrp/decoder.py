"""
vrp/decoder.py
--------------
Decodifica um cromossomo (permutação de IDs) em rotas concretas para
cada veículo, respeitando as restrições de capacidade e autonomia.

Requisitos atendidos (PDF – Projeto 2):
  - Representação genética adequada para rotas: o cromossomo é uma
    permutação de IDs dos pontos de entrega; este módulo interpreta
    essa representação e gera as rotas reais.
  - Capacidade limitada dos veículos: a rota é fechada quando
    current_load + demand ultrapassa vehicle.capacity.
  - Autonomia limitada dos veículos: a rota é fechada quando
    current_distance + dist_to_point + dist_back_depot ultrapassa
    vehicle.max_distance.
  - Múltiplos veículos (VRP): ao fechar uma rota, avança para o
    próximo veículo disponível na frota.
"""

import math
from typing import List
from domain.models import Route, DeliveryPoint
from domain.problem import VRPProblem


class VRPDecoder:
    """
    Converte um cromossomo em lista de Route, distribuindo os pontos
    de entrega entre os veículos disponíveis.

    A lógica segue o padrão "sequential decoder":
      1. Percorre o cromossomo gene a gene.
      2. Tenta adicionar o próximo ponto à rota do veículo atual.
      3. Se violar capacidade ou autonomia, fecha a rota atual e
         avança para o próximo veículo.
      4. Repete até processar todos os genes.
    """

    def __init__(self, problem: VRPProblem):
        self.problem = problem

    def euclidean_distance(self, a: DeliveryPoint, b: DeliveryPoint) -> float:
        """Distância euclidiana em pixels entre dois pontos."""
        return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2)

    def decode(self, chromosome: List[int]) -> List[Route]:
        """
        Decodifica o cromossomo em uma lista de rotas.

        Parâmetros:
            chromosome : lista de IDs de pontos de entrega (permutação)

        Retorno:
            lista de Route, uma por segmento de viagem realizado
        """
        routes   = []
        vehicles = self.problem.vehicles

        if not vehicles:
            return routes

        vehicle_index  = 0
        vehicle        = vehicles[vehicle_index]
        current_route  = Route(vehicle_id=vehicle.id, stops=[])
        current_load   = 0
        current_distance = 0
        last_point     = self.problem.depot

        for gene in chromosome:
            point = self.problem.get_point(gene)

            dist_to_point  = self.euclidean_distance(last_point, point)
            dist_back_depot = self.euclidean_distance(point, self.problem.depot)

            # Verifica restrições: capacidade e autonomia (ida + retorno ao depot)
            exceeds_capacity  = current_load + point.demand > vehicle.capacity
            exceeds_autonomy  = (current_distance + dist_to_point + dist_back_depot
                                 > vehicle.max_distance)

            if exceeds_capacity or exceeds_autonomy:
                # Fecha rota atual e avança para o próximo veículo
                if current_route.stops:
                    routes.append(current_route)

                vehicle_index += 1
                if vehicle_index < len(vehicles):
                    vehicle = vehicles[vehicle_index]
                else:
                    # Sem mais veículos — reutiliza o último para não perder entregas
                    vehicle_index = len(vehicles) - 1
                    vehicle = vehicles[vehicle_index]

                current_route    = Route(vehicle_id=vehicle.id, stops=[])
                current_load     = 0
                current_distance = 0
                last_point       = self.problem.depot

            # Adiciona ponto à rota atual
            current_route.stops.append(point)
            current_load     += point.demand
            current_distance += dist_to_point
            last_point        = point

        # Fecha a última rota se houver entregas pendentes
        if current_route.stops:
            routes.append(current_route)

        return routes
