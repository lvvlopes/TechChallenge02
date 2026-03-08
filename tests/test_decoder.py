"""
tests/test_decoder.py
----------------------
Testes automatizados do VRPDecoder.

Cobre:
  - _sort_by_priority : ordenação correta por prioridade (crítica > alta > normal)
  - decode            : restrições de capacidade, autonomia, múltiplos veículos
  - Integridade       : todos os pontos entregues, sem duplicatas
"""

import sys
import os
import math
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from domain.models import DeliveryPoint, Vehicle, Route
from domain.problem import VRPProblem
from vrp.decoder import VRPDecoder


# ── Factories de objetos de teste ─────────────────────────────────────────────

def make_point(id: int, x: float, y: float, demand: int, priority: int) -> DeliveryPoint:
    return DeliveryPoint(id=id, name=f"Cidade_{id}", x=x, y=y,
                         demand=demand, priority=priority)

def make_depot() -> DeliveryPoint:
    return DeliveryPoint(id=0, name="Depósito", x=0.0, y=0.0, demand=0, priority=0)

def make_problem(points, vehicles, depot=None) -> VRPProblem:
    d = depot or make_depot()
    return VRPProblem(delivery_points=points, vehicles=vehicles, depot=d)


# ── Testes ────────────────────────────────────────────────────────────────────

class TestSortByPriority(unittest.TestCase):
    """Testes para o método _sort_by_priority do VRPDecoder."""

    def setUp(self):
        self.points = [
            make_point(1, 10, 10, 5, 1),  # normal
            make_point(2, 20, 20, 5, 3),  # crítica
            make_point(3, 30, 30, 5, 2),  # alta
            make_point(4, 40, 40, 5, 1),  # normal
            make_point(5, 50, 50, 5, 3),  # crítica
        ]
        vehicles = [Vehicle(id=1, capacity=500, max_distance=999999)]
        self.problem = make_problem(self.points, vehicles)
        self.decoder = VRPDecoder(self.problem)

    def test_criticas_vem_primeiro(self):
        cromossomo = [1, 2, 3, 4, 5]
        ordenado = self.decoder._sort_by_priority(cromossomo)
        prioridades = [self.problem.get_point(g).priority for g in ordenado]
        # As duas primeiras devem ser críticas (3)
        self.assertEqual(prioridades[0], 3)
        self.assertEqual(prioridades[1], 3)

    def test_altas_vem_antes_de_normais(self):
        cromossomo = [1, 2, 3, 4, 5]
        ordenado = self.decoder._sort_by_priority(cromossomo)
        prioridades = [self.problem.get_point(g).priority for g in ordenado]
        # Índice 2 deve ser alta (2), índices 3 e 4 devem ser normais (1)
        self.assertEqual(prioridades[2], 2)
        self.assertIn(prioridades[3], [1])
        self.assertIn(prioridades[4], [1])

    def test_ordem_decrescente_de_prioridade(self):
        cromossomo = [1, 2, 3, 4, 5]
        ordenado = self.decoder._sort_by_priority(cromossomo)
        prioridades = [self.problem.get_point(g).priority for g in ordenado]
        self.assertEqual(prioridades, sorted(prioridades, reverse=True))

    def test_preserva_todos_os_genes(self):
        cromossomo = [1, 2, 3, 4, 5]
        ordenado = self.decoder._sort_by_priority(cromossomo)
        self.assertEqual(sorted(ordenado), sorted(cromossomo))

    def test_todos_normais_mantem_ordem_relativa(self):
        """Quando todos têm prioridade 1, a ordem original é preservada."""
        pontos = [make_point(i, i*10, i*10, 5, 1) for i in range(1, 6)]
        prob = make_problem(pontos, [Vehicle(id=1, capacity=500, max_distance=999999)])
        dec = VRPDecoder(prob)
        cromossomo = [1, 2, 3, 4, 5]
        ordenado = dec._sort_by_priority(cromossomo)
        self.assertEqual(ordenado, cromossomo)

    def test_todos_criticos_mantem_ordem_relativa(self):
        pontos = [make_point(i, i*10, i*10, 5, 3) for i in range(1, 6)]
        prob = make_problem(pontos, [Vehicle(id=1, capacity=500, max_distance=999999)])
        dec = VRPDecoder(prob)
        cromossomo = [1, 2, 3, 4, 5]
        ordenado = dec._sort_by_priority(cromossomo)
        self.assertEqual(ordenado, cromossomo)


class TestDecoderIntegridade(unittest.TestCase):
    """Testes de integridade: todos os pontos devem ser entregues."""

    def _make_simple_problem(self, n_points=5, capacity=1000, max_dist=999999):
        points = [make_point(i, i*10.0, 0.0, 5, 1) for i in range(1, n_points + 1)]
        vehicles = [Vehicle(id=1, capacity=capacity, max_distance=max_dist)]
        return make_problem(points, vehicles), points

    def test_todos_pontos_entregues_veículo_unico(self):
        prob, points = self._make_simple_problem(5)
        decoder = VRPDecoder(prob)
        routes = decoder.decode([p.id for p in points])
        entregues = [s.id for r in routes for s in r.stops]
        self.assertEqual(sorted(entregues), [p.id for p in points])

    def test_sem_duplicatas_nas_rotas(self):
        prob, points = self._make_simple_problem(8)
        decoder = VRPDecoder(prob)
        routes = decoder.decode([p.id for p in points])
        entregues = [s.id for r in routes for s in r.stops]
        self.assertEqual(len(entregues), len(set(entregues)))

    def test_retorna_lista_de_routes(self):
        prob, points = self._make_simple_problem(3)
        decoder = VRPDecoder(prob)
        routes = decoder.decode([p.id for p in points])
        self.assertIsInstance(routes, list)
        for r in routes:
            self.assertIsInstance(r, Route)


class TestDecoderCapacidade(unittest.TestCase):
    """Testes das restrições de capacidade do veículo."""

    def test_rota_fechada_ao_exceder_capacidade(self):
        """Com capacidade 10 e demanda 6 por ponto, cada rota leva 1 ponto."""
        points = [make_point(i, float(i*10), 0.0, 6, 1) for i in range(1, 4)]
        # Capacidade 10: cabe 1 ponto (6 unid), o segundo (12 unid) excede
        vehicles = [
            Vehicle(id=1, capacity=10, max_distance=999999),
            Vehicle(id=2, capacity=10, max_distance=999999),
            Vehicle(id=3, capacity=10, max_distance=999999),
        ]
        prob = make_problem(points, vehicles)
        decoder = VRPDecoder(prob)
        routes = decoder.decode([1, 2, 3])

        # Cada rota deve ter no máximo 1 ponto
        for route in routes:
            carga = sum(s.demand for s in route.stops)
            self.assertLessEqual(carga, 10)

    def test_carga_nunca_excede_capacidade_do_veiculo(self):
        points = [make_point(i, float(i*5), 0.0, 3, 1) for i in range(1, 10)]
        vehicles = [
            Vehicle(id=1, capacity=20, max_distance=999999),
            Vehicle(id=2, capacity=20, max_distance=999999),
        ]
        prob = make_problem(points, vehicles)
        decoder = VRPDecoder(prob)
        routes = decoder.decode([p.id for p in points])

        for route in routes:
            carga = sum(s.demand for s in route.stops)
            # Busca capacidade do veículo responsável
            veh_cap = next(v.capacity for v in vehicles if v.id == route.vehicle_id)
            self.assertLessEqual(carga, veh_cap)

    def test_todos_pontos_entregues_mesmo_com_capacidade_baixa(self):
        points = [make_point(i, float(i*10), 0.0, 5, 1) for i in range(1, 6)]
        vehicles = [
            Vehicle(id=v, capacity=6, max_distance=999999) for v in range(1, 7)
        ]
        prob = make_problem(points, vehicles)
        decoder = VRPDecoder(prob)
        routes = decoder.decode([p.id for p in points])
        entregues = [s.id for r in routes for s in r.stops]
        self.assertEqual(sorted(entregues), [p.id for p in points])


class TestDecoderAutonomia(unittest.TestCase):
    """Testes das restrições de autonomia do veículo."""

    def test_rota_fechada_ao_exceder_autonomia(self):
        """Pontos distantes entre si com autonomia curta → múltiplas rotas."""
        # Pontos em linha com 100px de espaçamento
        points = [make_point(i, float(i * 100), 0.0, 1, 1) for i in range(1, 5)]
        # Autonomia de 150px: cabe ir a 1 ponto (100px) e voltar (100px) = 200px > 150px
        # Então precisa de veículos individuais para cada ponto distante
        vehicles = [Vehicle(id=v, capacity=500, max_distance=150) for v in range(1, 6)]
        prob = make_problem(points, vehicles)
        decoder = VRPDecoder(prob)
        routes = decoder.decode([p.id for p in points])

        # Com autonomia curta, devem haver múltiplas rotas
        self.assertGreater(len(routes), 1)

    def test_todos_pontos_entregues_mesmo_com_autonomia_limitada(self):
        points = [make_point(i, float(i * 50), 0.0, 1, 1) for i in range(1, 6)]
        vehicles = [Vehicle(id=v, capacity=500, max_distance=120) for v in range(1, 7)]
        prob = make_problem(points, vehicles)
        decoder = VRPDecoder(prob)
        routes = decoder.decode([p.id for p in points])
        entregues = [s.id for r in routes for s in r.stops]
        self.assertEqual(sorted(entregues), [p.id for p in points])


class TestDecoderMultiplosVeiculos(unittest.TestCase):
    """Testes para distribuição entre múltiplos veículos."""

    def test_usa_multiplos_veiculos_quando_necessario(self):
        """Com capacidade restritiva, deve usar mais de um veículo."""
        points = [make_point(i, float(i*10), 0.0, 8, 1) for i in range(1, 5)]
        vehicles = [
            Vehicle(id=1, capacity=10, max_distance=999999),
            Vehicle(id=2, capacity=10, max_distance=999999),
            Vehicle(id=3, capacity=10, max_distance=999999),
            Vehicle(id=4, capacity=10, max_distance=999999),
        ]
        prob = make_problem(points, vehicles)
        decoder = VRPDecoder(prob)
        routes = decoder.decode([1, 2, 3, 4])
        veiculos_usados = set(r.vehicle_id for r in routes)
        self.assertGreater(len(veiculos_usados), 1)

    def test_vehicle_ids_validos(self):
        """Todos os vehicle_ids nas rotas devem existir na frota."""
        points = [make_point(i, float(i*10), 0.0, 5, 1) for i in range(1, 6)]
        vehicles = [Vehicle(id=v, capacity=15, max_distance=999999) for v in range(1, 4)]
        prob = make_problem(points, vehicles)
        decoder = VRPDecoder(prob)
        routes = decoder.decode([p.id for p in points])
        ids_validos = {v.id for v in vehicles}
        for route in routes:
            self.assertIn(route.vehicle_id, ids_validos)

    def test_sem_veiculos_retorna_lista_vazia(self):
        points = [make_point(1, 10.0, 10.0, 5, 1)]
        prob = make_problem(points, [])
        decoder = VRPDecoder(prob)
        routes = decoder.decode([1])
        self.assertEqual(routes, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
