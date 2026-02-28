import pygame
from pygame.locals import *
import random
import itertools
from genetic_algorithm import generate_convex_hull_population, generate_nearest_neighbour_population, mutate, order_crossover, generate_random_population, calculate_fitness, sort_population, default_problems
from draw_functions import draw_paths, draw_plot, draw_cities
import sys
import numpy as np
import pygame
from benchmark_greater_sp import fix_start, greater_sp_cities, project_cities_to_screen


# Define constant values
# pygame
WIDTH, HEIGHT = 800, 400
NODE_RADIUS = 10
FPS = 30
PLOT_X_OFFSET = 450

# GA
N_CITIES = 15
POPULATION_SIZE = 100
N_GENERATIONS = None
MUTATION_PROBABILITY = 0.5
CIDADE_INICIAL = "Guarulhos"  # Cidade inicial para o TSP (pode ser alterada conforme necessário)

# Define colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)

# minhas constantes
TOURNAMENT_SIZE = 5


def build_city_labels(cities):
    return [city_name for city_name, *_ in cities]

def tournament_selection(population, fitness, k=TOURNAMENT_SIZE):
    # escolhe k indivíduos aleatórios
    selected_indices = random.sample(range(len(population)), k)

    # pega o melhor entre eles (menor fitness)
    best_index = min(selected_indices, key=lambda i: fitness[i])
    return population[best_index]


# Initialize problem
# Using Random cities generation
# cities_locations = [(random.randint(NODE_RADIUS + PLOT_X_OFFSET, WIDTH - NODE_RADIUS), random.randint(NODE_RADIUS, HEIGHT - NODE_RADIUS))
#                     for _ in range(N_CITIES)]


# # # Using Deault Problems: 10, 12 or 15
# WIDTH, HEIGHT = 800, 400
# cities_locations = default_problems[15]


# Using Greater São Paulo (RMSP) municipalities
WIDTH, HEIGHT = 1500, 800
cities_locations = project_cities_to_screen(
    greater_sp_cities,
    width=WIDTH,
    height=HEIGHT,
    x_offset=PLOT_X_OFFSET,
    node_radius=NODE_RADIUS,
)

# mapa nome -> coordenada
city_map = {
    name: coord
    for (name, _, _), coord in zip(greater_sp_cities, cities_locations)
}

# mapa coordenada -> nome
coord_to_name = {coord: name for name, coord in city_map.items()}

#start_city = cities_locations[0]
start_city = city_map[CIDADE_INICIAL]

# Gerar demandas e prioridades aleatórias para cada cidade 
city_demand = {
    city: random.randint(1, 20)
    for city in cities_locations
}

city_priority = {
    city: random.randint(1, 3)
    for city in cities_locations
}

city_labels = build_city_labels(greater_sp_cities)


# ----- Using Greater São Paulo (RMSP)


# Initialize Pygame
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("TSP Solver using Pygame")
clock = pygame.time.Clock()
generation_counter = itertools.count(start=1)  # Start the counter at 1


# Create Initial Population

#n_random = POPULATION_SIZE #// 3
n_nn = POPULATION_SIZE #// 3
n_ch = POPULATION_SIZE #- n_random - n_nn

population = []
#population.extend(generate_random_population(cities_locations, n_random)) #250794.16 #12832.1
#population.extend(generate_nearest_neighbour_population(cities_locations, n_nn)) #86328.23 #5355.24
population.extend(generate_convex_hull_population(cities_locations, n_ch)) # 79671.14 #4995.2

# fixa cidade inicial para o TSP
population = [fix_start(ind, start_city) for ind in population]

best_fitness_values = []
best_solutions = []


# Main game loop
best_fitness_old = None
sem_mudanca = 0
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_q:
                running = False

    generation = next(generation_counter)

    screen.fill(WHITE)

    # Calculate fitness for the population
    population_fitness = [
        calculate_fitness(individual, city_demand, city_priority, start_city)
        for individual in population
    ]


    population, population_fitness = sort_population(
        population,  population_fitness)

    # Get the best solution and its fitness
    # The calculate_fitness function defined in genetic_algorithm.py requires
    # city_demand, city_priority and start_city arguments (plus optional
    # capacity/autonomy). The previous call omitted start_city, causing a
    # TypeError at runtime.
    best_fitness = calculate_fitness(
        population[0], city_demand, city_priority, start_city)
    
    best_solution = population[0]
    
    # criar labels para as cidades do melhor caminho
    labels_map = {
        city: f"{i+1} - {coord_to_name[city]}"
        for i, city in enumerate(best_solution)
}

    best_fitness_values.append(best_fitness)
    best_solutions.append(best_solution)

    draw_plot(screen, list(range(len(best_fitness_values))),
              best_fitness_values, y_label="Fitness - Distance (pxls)")

    draw_cities(screen,
        cities_locations,
        RED,
        NODE_RADIUS,
        labels_map=labels_map,
        start_city=start_city
    )
    
    draw_paths(screen, best_solution, BLUE, width=3)
    draw_paths(screen, population[1], rgb_color=(128, 128, 128), width=1)

    print(f"Generation {generation}: Best fitness = {round(best_fitness, 2)}")

    fitness_atual = round(best_fitness, 2)

    if best_fitness_old == fitness_atual:
        sem_mudanca += 1
    else:
        sem_mudanca = 0

    best_fitness_old = fitness_atual
    if sem_mudanca >= 1000:
        running = False


    new_population = [population[0]]  # Keep the best individual: ELITISM

    while len(new_population) < POPULATION_SIZE:

        # selection
        # simple selection based on first 10 best solutions
        # parent1, parent2 = random.choices(population[:10], k=2)

        # solution based on fitness probability
        #probability = 1 / np.array(population_fitness)
        #parent1, parent2 = random.choices(population, weights=probability, k=2)

        # tournament selection
        parent1 = tournament_selection(population, population_fitness)
        parent2 = tournament_selection(population, population_fitness)


        # child1 = order_crossover(parent1, parent2)
        child1 = order_crossover(parent1, parent2)

        child1 = mutate(child1, MUTATION_PROBABILITY)

        child1 = fix_start(child1, start_city)

        new_population.append(child1)

    population = new_population

    pygame.display.flip()
    clock.tick(FPS)



pygame.quit()
sys.exit()
