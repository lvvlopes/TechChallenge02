"""
domain/models.py
----------------
Define as entidades do domínio do problema VRP hospitalar.

Requisito atendido (PDF – Projeto 2):
  - Representação das restrições realistas:
      * DeliveryPoint.demand  → capacidade limitada dos veículos
      * DeliveryPoint.priority → prioridades de entrega (1=normal, 2=alta, 3=crítica)
      * Vehicle.capacity       → carga máxima por veículo
      * Vehicle.max_distance   → autonomia máxima por veículo
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class DeliveryPoint:
    """
    Representa um ponto de entrega (unidade hospitalar ou domicílio).

    Atributos:
        id            : identificador único do ponto
        name          : nome da cidade/unidade
        x, y          : coordenadas em pixels na tela (projetadas de lat/lon)
        demand        : quantidade de medicamentos/insumos a entregar
        priority      : urgência da entrega — 1=normal, 2=alta, 3=crítica
    """
    id:       int
    name:     str
    x:        float
    y:        float
    demand:   int    # quantidade a entregar
    priority: int    # 1 = normal | 2 = alta | 3 = crítica


@dataclass
class Vehicle:
    """
    Representa um veículo de entrega.

    Atributos:
        id           : identificador único do veículo
        capacity     : carga máxima (unidades de demanda)
        max_distance : autonomia máxima em pixels de tela
    """
    id:           int
    capacity:     int
    max_distance: float


@dataclass
class Route:
    """
    Representa a rota executada por um veículo em uma viagem.

    Atributos:
        vehicle_id     : veículo responsável pela rota
        stops          : sequência ordenada de pontos de entrega
        total_distance : distância total percorrida (calculada pelo decoder)
        total_load     : carga total transportada (calculada pelo decoder)
    """
    vehicle_id:     int
    stops:          list   # List[DeliveryPoint]
    total_distance: float = 0.0
    total_load:     int   = 0
