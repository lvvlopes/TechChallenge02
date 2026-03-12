import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg
import pygame
from typing import List, Tuple

# Cores compartilhadas entre draw_routes (Pygame RGB) e draw_plot (matplotlib hex)
ROUTE_COLORS_RGB = [
    (255, 0,   0),    # vermelho  — Veículo 1
    (0,   0,   255),  # azul      — Veículo 2
    (0,   200, 0),    # verde     — Veículo 3
    (200, 0,   200),  # roxo      — Veículo 4
    (255, 165, 0),    # laranja   — Veículo 5
]
ROUTE_COLORS_HEX = [
    '#FF0000',
    '#0000FF',
    '#00C800',
    '#C800C8',
    '#FFA500',
]


def draw_plot(screen: pygame.Surface, x: list, y_fitness: list,
              y_km: list = None,
              y_best: list = None,
              y_best_km: list = None,
              routes: list = None,
              x_label: str = 'Generation',
              y_label: str = 'Fitness') -> None:
    """
    Painel duplo:
      - superior: fitness normalizado por geração
      - inferior: distância total em KM reais + legenda de veículos
    """
    if y_km:
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(4, 4), dpi=100)
    else:
        fig, ax1 = plt.subplots(1, 1, figsize=(4, 4), dpi=100)

    # Melhor global desenhado PRIMEIRO (atrás), geração atual por cima
    if y_best:
        ax1.plot(x, y_best, color='red', linewidth=1.5, label='Melhor global', zorder=1)
    ax1.plot(x, y_fitness, color='steelblue', alpha=0.7, linewidth=1.0, label='Geração atual', zorder=2)
    if y_best:
        ax1.legend(fontsize=6, loc='upper right')
    ax1.set_ylabel(y_label, fontsize=8)
    ax1.tick_params(labelsize=7)
    if not y_km:
        ax1.set_xlabel(x_label, fontsize=8)

    if y_km:
        # Melhor KM desenhado PRIMEIRO (atrás), geração atual por cima
        if y_best_km:
            ax2.plot(x, y_best_km, color='red', linewidth=1.5, label='Melhor KM', zorder=1)
        ax2.plot(x, y_km, color='darkorange', alpha=0.6, linewidth=1.0, label='KM geração', zorder=2)
        if y_best_km:
            best_km = y_best_km[-1]
            ax2.annotate(
                f'{best_km:.1f} km',
                xy=(x[-1], best_km),
                xytext=(-55, 8),
                textcoords='offset points',
                fontsize=8,
                color='red',
                fontweight='bold'
            )
        else:
            current_km = y_km[-1]
            ax2.annotate(
                f'{current_km:.1f} km',
                xy=(x[-1], current_km),
                xytext=(-55, 8),
                textcoords='offset points',
                fontsize=8,
                color='darkorange',
                fontweight='bold'
            )
        ax2.set_ylabel('Distância total (km)', fontsize=8)
        ax2.set_xlabel(x_label, fontsize=8)
        ax2.tick_params(labelsize=7)

        # legenda de veículos
        if routes:
            vehicle_color_map = {}
            color_idx = 0
            for route in routes:
                if route.vehicle_id not in vehicle_color_map:
                    vehicle_color_map[route.vehicle_id] = color_idx
                    color_idx += 1

            legend_patches = []
            for vid, cidx in sorted(vehicle_color_map.items()):
                color = ROUTE_COLORS_HEX[cidx % len(ROUTE_COLORS_HEX)]
                patch = plt.Line2D([0], [0], color=color, linewidth=3,
                                   label=f'Veículo {vid}')
                legend_patches.append(patch)

            ax2.legend(
                handles=legend_patches,
                loc='upper right',
                fontsize=7,
                framealpha=0.7,
                title='Veículos',
                title_fontsize=7,
            )

    plt.tight_layout()

    canvas = FigureCanvasAgg(fig)
    canvas.draw()
    raw_data = canvas.get_renderer().buffer_rgba().tobytes()
    size = canvas.get_width_height()
    surf = pygame.image.fromstring(raw_data, size, "RGBA")
    screen.blit(surf, (0, 0))
    plt.close(fig)


def draw_routes(screen, routes, depot):
    """Desenha as rotas no mapa, cada veículo com sua cor."""
    vehicle_color_map = {}
    color_idx = 0
    for route in routes:
        if route.vehicle_id not in vehicle_color_map:
            vehicle_color_map[route.vehicle_id] = color_idx
            color_idx += 1

    for route in routes:
        color = ROUTE_COLORS_RGB[vehicle_color_map[route.vehicle_id] % len(ROUTE_COLORS_RGB)]
        last_x, last_y = depot.x, depot.y

        for stop in route.stops:
            pygame.draw.line(screen, color, (last_x, last_y), (stop.x, stop.y), 3)
            last_x, last_y = stop.x, stop.y

        pygame.draw.line(screen, color, (last_x, last_y), (depot.x, depot.y), 3)
