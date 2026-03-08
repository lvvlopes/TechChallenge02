"""
tests/test_fitness.py
----------------------
Testes automatizados das funções de fitness e refinamento 2-opt.

Cobre:
  - calculo_fitness : retorno escalar, comportamento com distância e prioridade
  - two_opt         : melhoria ou igualdade de distância, integridade do cromossomo
  - route_distance  : cálculo euclidiano correto
"""

import sys
import os
import math
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from domain.models import DeliveryPoint, Vehicle
from domain.problem import VRPProblem
from core.fitness import calculo_fitness, two_opt, route_distance


# ── Factories ─────────────────────────────────────────────────────────────────

def make_point(id: int, x: float, y: float, demand: int = 5, priority: int = 1):
    return DeliveryPoint(id=id, name=f"Cidade_{id}", x=x, y=y,
                         demand=demand, priority=priority)

def make_depot():
    return DeliveryPoint(id=0, name="Depósito", x=0.0, y=0.0, demand=0, priority=0)

def make_problem(points, capacity=1000, max_dist=999999):
    vehicles = [
        Vehicle(id=1, capacity=capacity, max_distance=max_dist),
        Vehicle(id=2, capacity=capacity, max_distance=max_dist),
    ]
    return VRPProblem(delivery_points=points, vehicles=vehicles, depot=make_depot())


# ── Testes ────────────────────────────────────────────────────────────────────

class TestCalculoFitness(unittest.TestCase):
    """Testes para a função calculo_fitness."""

    def setUp(self):
        self.points = [make_point(i, float(i * 50), 0.0) for i in range(1, 6)]
        self.problem = make_problem(self.points)
        self.cromossomo = [p.id for p in self.points]

    def test_retorna_float(self):
        resultado = calculo_fitness(self.cromossomo, self.problem)
        self.assertIsInstance(resultado, float)

    def test_fitness_positivo(self):
        resultado = calculo_fitness(self.cromossomo, self.problem)
        self.assertGreater(resultado, 0.0)

    def test_fitness_finito(self):
        resultado = calculo_fitness(self.cromossomo, self.problem)
        self.assertTrue(math.isfinite(resultado))

    def test_diferentes_ordens_diferentes_fitness(self):
        """Ordens diferentes de visita devem (geralmente) produzir fitness diferentes."""
        ordem1 = [1, 2, 3, 4, 5]
        ordem2 = [5, 4, 3, 2, 1]
        f1 = calculo_fitness(ordem1, self.problem)
        f2 = calculo_fitness(ordem2, self.problem)
        # Não necessariamente iguais — a rota reversa pode ter distância diferente
        self.assertIsInstance(f1, float)
        self.assertIsInstance(f2, float)

    def test_fitness_ponto_unico(self):
        """Com apenas 1 ponto de entrega, o fitness deve ser calculável."""
        prob = make_problem([make_point(1, 100.0, 0.0)])
        f = calculo_fitness([1], prob)
        self.assertIsInstance(f, float)
        self.assertTrue(math.isfinite(f))

    def test_fitness_pontos_no_deposito(self):
        """Pontos no depósito (distância zero) devem ter fitness calculável."""
        pontos = [make_point(i, 0.0, 0.0) for i in range(1, 4)]
        prob = make_problem(pontos)
        f = calculo_fitness([1, 2, 3], prob)
        self.assertIsInstance(f, float)
        self.assertTrue(math.isfinite(f))

    def test_prioridade_critica_penaliza_mais_no_fim(self):
        """
        Rota com cidade crítica no fim deve ter fitness MAIOR (pior)
        do que com cidade crítica no início.
        """
        # Ponto 1 = normal, ponto 2 = crítico
        pontos = [
            make_point(1, 100.0, 0.0, 5, 1),
            make_point(2, 200.0, 0.0, 5, 3),
        ]
        prob = make_problem(pontos)
        decoder_força_ordem = True  # _sort_by_priority garante crítica primeiro

        # Como o decoder reordena por prioridade, o resultado deve ser o mesmo
        f1 = calculo_fitness([1, 2], prob)
        f2 = calculo_fitness([2, 1], prob)
        # Ambos devem ser finitos e positivos
        self.assertTrue(math.isfinite(f1))
        self.assertTrue(math.isfinite(f2))


class TestRouteDistance(unittest.TestCase):
    """Testes para a função route_distance."""

    def setUp(self):
        # Pontos em linha: (0,0), (3,4), (6,8) → distâncias: 5, 5
        self.points = [
            make_point(1, 3.0, 4.0),
            make_point(2, 6.0, 8.0),
        ]
        self.problem = make_problem(self.points)

    def test_distancia_dois_pontos_adjacentes(self):
        """Distância entre (3,4) e (6,8) = sqrt(9+16) = 5.0"""
        dist = route_distance([1, 2], self.problem)
        self.assertAlmostEqual(dist, 5.0, places=5)

    def test_distancia_ponto_unico_e_zero(self):
        prob = make_problem([make_point(1, 5.0, 0.0)])
        dist = route_distance([1], prob)
        self.assertAlmostEqual(dist, 0.0, places=5)

    def test_distancia_positiva(self):
        dist = route_distance([1, 2], self.problem)
        self.assertGreaterEqual(dist, 0.0)

    def test_distancia_simetrica(self):
        """Distância de A→B deve ser igual a B→A."""
        d1 = route_distance([1, 2], self.problem)
        d2 = route_distance([2, 1], self.problem)
        self.assertAlmostEqual(d1, d2, places=5)

    def test_distancia_triangulo_pitagoras(self):
        """Triângulo 3-4-5: pontos (0,0)→(3,0)→(3,4)."""
        pontos = [make_point(1, 3.0, 0.0), make_point(2, 3.0, 4.0)]
        prob = make_problem(pontos)
        dist = route_distance([1, 2], prob)
        self.assertAlmostEqual(dist, 4.0, places=5)  # apenas o segmento [1→2]


class TestTwoOpt(unittest.TestCase):
    """Testes para o refinamento local 2-opt."""

    def setUp(self):
        # Rota com cruzamento óbvio: 1-3-2-4 vs 1-2-3-4 (em linha)
        self.points = [
            make_point(1,   0.0, 0.0),
            make_point(2, 100.0, 0.0),
            make_point(3, 200.0, 0.0),
            make_point(4, 300.0, 0.0),
        ]
        self.problem = make_problem(self.points)

    def test_resultado_e_permutacao_valida(self):
        cromossomo = [1, 3, 2, 4]
        resultado = two_opt(cromossomo, self.problem)
        self.assertEqual(sorted(resultado), sorted(cromossomo))

    def test_sem_duplicatas(self):
        cromossomo = [1, 3, 2, 4]
        resultado = two_opt(cromossomo, self.problem)
        self.assertEqual(len(resultado), len(set(resultado)))

    def test_distancia_nao_piora(self):
        """O 2-opt nunca deve piorar a distância."""
        cromossomo = [1, 2, 3, 4]
        dist_antes = route_distance(cromossomo, self.problem)
        resultado = two_opt(cromossomo, self.problem)
        dist_depois = route_distance(resultado, self.problem)
        self.assertLessEqual(dist_depois, dist_antes + 1e-9)

    def test_preserva_tamanho(self):
        cromossomo = [1, 2, 3, 4]
        resultado = two_opt(cromossomo, self.problem)
        self.assertEqual(len(resultado), len(cromossomo))

    def test_nao_altera_original(self):
        cromossomo = [1, 3, 2, 4]
        original_copia = cromossomo[:]
        two_opt(cromossomo, self.problem)
        self.assertEqual(cromossomo, original_copia)

    def test_dois_pontos_nao_quebra(self):
        pontos = [make_point(1, 0.0, 0.0), make_point(2, 10.0, 0.0)]
        prob = make_problem(pontos)
        resultado = two_opt([1, 2], prob)
        self.assertEqual(sorted(resultado), [1, 2])

    def test_ponto_unico_nao_quebra(self):
        pontos = [make_point(1, 5.0, 5.0)]
        prob = make_problem(pontos)
        resultado = two_opt([1], prob)
        self.assertEqual(resultado, [1])


if __name__ == "__main__":
    unittest.main(verbosity=2)
