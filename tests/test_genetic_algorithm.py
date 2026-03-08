"""
tests/test_genetic_algorithm.py
--------------------------------
Testes automatizados dos operadores genéticos.

Cobre:
  - order_crossover : validade da permutação, preservação de genes
  - mutate          : integridade do cromossomo, comportamento probabilístico
  - sort_population : ordenação correta por fitness
"""

import sys
import os
import random
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from genetic_algorithm import order_crossover, mutate, sort_population


class TestOrderCrossover(unittest.TestCase):
    """Testes para o operador Order Crossover (OX)."""

    def setUp(self):
        self.parent1 = [1, 2, 3, 4, 5, 6, 7, 8]
        self.parent2 = [8, 7, 6, 5, 4, 3, 2, 1]

    def test_filho_tem_mesmo_tamanho_dos_pais(self):
        filho = order_crossover(self.parent1, self.parent2)
        self.assertEqual(len(filho), len(self.parent1))

    def test_filho_e_permutacao_valida(self):
        """Cada gene deve aparecer exatamente uma vez."""
        for _ in range(50):
            filho = order_crossover(self.parent1, self.parent2)
            self.assertEqual(sorted(filho), sorted(self.parent1))

    def test_filho_sem_duplicatas(self):
        for _ in range(50):
            filho = order_crossover(self.parent1, self.parent2)
            self.assertEqual(len(filho), len(set(filho)))

    def test_filho_contem_todos_os_genes_do_pai1(self):
        """Todos os genes de parent1 devem estar no filho."""
        for _ in range(30):
            filho = order_crossover(self.parent1, self.parent2)
            self.assertEqual(set(filho), set(self.parent1))

    def test_pais_identicos_geram_filho_identico(self):
        pai = [1, 2, 3, 4, 5]
        filho = order_crossover(pai, pai)
        self.assertEqual(sorted(filho), sorted(pai))
        self.assertEqual(len(filho), len(set(filho)))

    def test_cromossomo_de_um_elemento(self):
        filho = order_crossover([42], [42])
        self.assertEqual(filho, [42])

    def test_cromossomo_de_dois_elementos(self):
        for _ in range(20):
            filho = order_crossover([1, 2], [2, 1])
            self.assertIn(sorted(filho), [[1, 2]])

    def test_nao_altera_pais_originais(self):
        p1 = [1, 2, 3, 4, 5]
        p2 = [5, 4, 3, 2, 1]
        p1_copia = p1[:]
        p2_copia = p2[:]
        order_crossover(p1, p2)
        self.assertEqual(p1, p1_copia)
        self.assertEqual(p2, p2_copia)


class TestMutate(unittest.TestCase):
    """Testes para o operador de mutação por adjacent swap."""

    def setUp(self):
        self.cromossomo = [1, 2, 3, 4, 5, 6, 7, 8]

    def test_mutacao_preserva_todos_os_genes(self):
        for _ in range(100):
            mutado = mutate(self.cromossomo, mutation_probability=1.0)
            self.assertEqual(sorted(mutado), sorted(self.cromossomo))

    def test_mutacao_sem_duplicatas(self):
        for _ in range(100):
            mutado = mutate(self.cromossomo, mutation_probability=1.0)
            self.assertEqual(len(mutado), len(set(mutado)))

    def test_mutacao_probabilidade_zero_nao_altera(self):
        """Com prob=0, o cromossomo não deve mudar."""
        for _ in range(50):
            mutado = mutate(self.cromossomo, mutation_probability=0.0)
            self.assertEqual(mutado, self.cromossomo)

    def test_mutacao_probabilidade_um_sempre_troca(self):
        """Com prob=1.0, exatamente dois genes adjacentes são trocados."""
        random.seed(42)
        mutado = mutate(self.cromossomo, mutation_probability=1.0)
        diferencas = sum(1 for a, b in zip(self.cromossomo, mutado) if a != b)
        # Uma troca adjacente muda exatamente 2 posições
        self.assertEqual(diferencas, 2)

    def test_mutacao_nao_altera_original(self):
        """A mutação deve retornar uma cópia, não modificar o original."""
        original_copia = self.cromossomo[:]
        mutate(self.cromossomo, mutation_probability=1.0)
        self.assertEqual(self.cromossomo, original_copia)

    def test_mutacao_cromossomo_de_um_elemento(self):
        mutado = mutate([99], mutation_probability=1.0)
        self.assertEqual(mutado, [99])

    def test_mutacao_cromossomo_de_dois_elementos(self):
        """Com 2 elementos e prob=1, os elementos devem ser trocados."""
        random.seed(0)
        mutado = mutate([1, 2], mutation_probability=1.0)
        self.assertEqual(sorted(mutado), [1, 2])
        self.assertEqual(len(mutado), 2)

    def test_mutacao_preserva_tamanho(self):
        for _ in range(50):
            mutado = mutate(self.cromossomo, mutation_probability=0.5)
            self.assertEqual(len(mutado), len(self.cromossomo))


class TestSortPopulation(unittest.TestCase):
    """Testes para a ordenação da população por fitness."""

    def test_ordena_por_fitness_crescente(self):
        pop     = [[3, 1, 2], [1, 2, 3], [2, 3, 1]]
        fitness = [0.9, 0.3, 0.6]
        pop_ord, fit_ord = sort_population(pop, fitness)
        self.assertEqual(fit_ord, [0.3, 0.6, 0.9])

    def test_cromossomos_acompanham_fitness(self):
        """O cromossomo deve mover junto com seu fitness."""
        pop     = [[3, 1, 2], [1, 2, 3], [2, 3, 1]]
        fitness = [0.9, 0.3, 0.6]
        pop_ord, fit_ord = sort_population(pop, fitness)
        self.assertEqual(pop_ord[0], [1, 2, 3])   # fitness 0.3
        self.assertEqual(pop_ord[1], [2, 3, 1])   # fitness 0.6
        self.assertEqual(pop_ord[2], [3, 1, 2])   # fitness 0.9

    def test_populacao_ja_ordenada_permanece_igual(self):
        pop     = [[1, 2], [3, 4], [5, 6]]
        fitness = [0.1, 0.5, 0.9]
        pop_ord, fit_ord = sort_population(pop, fitness)
        self.assertEqual(fit_ord, [0.1, 0.5, 0.9])
        self.assertEqual(pop_ord, [[1, 2], [3, 4], [5, 6]])

    def test_fitness_iguais_mantem_todos_cromossomos(self):
        pop     = [[1, 2], [3, 4], [5, 6]]
        fitness = [0.5, 0.5, 0.5]
        pop_ord, fit_ord = sort_population(pop, fitness)
        self.assertEqual(len(pop_ord), 3)
        self.assertEqual(fit_ord, [0.5, 0.5, 0.5])

    def test_populacao_de_um_elemento(self):
        pop_ord, fit_ord = sort_population([[1, 2, 3]], [0.7])
        self.assertEqual(pop_ord, [[1, 2, 3]])
        self.assertEqual(fit_ord, [0.7])

    def test_tamanho_preservado_apos_ordenacao(self):
        pop     = [[i] for i in range(10)]
        fitness = [float(9 - i) for i in range(10)]
        pop_ord, fit_ord = sort_population(pop, fitness)
        self.assertEqual(len(pop_ord), 10)
        self.assertEqual(len(fit_ord), 10)


if __name__ == "__main__":
    unittest.main(verbosity=2)
