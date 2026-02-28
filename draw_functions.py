# -*- coding: utf-8 -*-
"""
Created on Fri Dec 22 16:03:11 2023
@author: SérgioPolimante
"""

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg
import pygame
from typing import List, Tuple


def draw_plot(screen: pygame.Surface, x: list, y: list,
              x_label: str = 'Generation',
              y_label: str = 'Fitness') -> None:

    fig, ax = plt.subplots(figsize=(4, 4), dpi=100)
    ax.plot(x, y)
    ax.set_ylabel(y_label)
    ax.set_xlabel(x_label)
    plt.tight_layout()

    canvas = FigureCanvasAgg(fig)
    canvas.draw()

    renderer = canvas.get_renderer()
    raw_data = renderer.buffer_rgba()
    raw_data = raw_data.tobytes()

    size = canvas.get_width_height()
    surf = pygame.image.fromstring(raw_data, size, "RGBA")

    screen.blit(surf, (0, 0))
    plt.close(fig)

def draw_cities(screen: pygame.Surface,
                cities_locations: List[Tuple[int, int]],
                rgb_color: Tuple[int, int, int],
                node_radius: int,
                labels_map: dict = None,
                label_color: pygame.Color = (0, 0, 0),
                start_city=None) -> None:

    pygame.font.init()
    font = pygame.font.SysFont('Arial', 12)

    for city_location in cities_locations:

        x, y = city_location

        # destaque da cidade inicial (verde)
        if start_city and city_location == start_city:
            pygame.draw.circle(screen, (0, 255, 0), city_location, node_radius + 3)
        else:
            pygame.draw.circle(screen, rgb_color, city_location, node_radius)

        # label baseado na rota
        if labels_map and city_location in labels_map:
            text_surface = font.render(labels_map[city_location], True, label_color)
            text_rect = text_surface.get_rect()
            text_rect.midbottom = (x, y - node_radius - 2)
            screen.blit(text_surface, text_rect)


def draw_paths(screen: pygame.Surface,
               path: List[Tuple[int, int]],
               rgb_color: Tuple[int, int, int],
               width: int = 1):

    pygame.draw.lines(screen, rgb_color, True, path, width=width)


def draw_text(screen: pygame.Surface,
              text: str,
              color: pygame.Color,
              position: Tuple[int, int] = (10, 10)) -> None:

    pygame.font.init()
    font_size = 15
    my_font = pygame.font.SysFont('Arial', font_size)
    text_surface = my_font.render(text, False, color)

    screen.blit(text_surface, position)
