import pygame
import sys

from menu import MainMenu
from game import Game


WIDTH = 1920
HEIGHT = 1080
FPS = 60


def main():
    pygame.init()

    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Pražská honička")

    clock = pygame.time.Clock()

    menu = MainMenu(screen)
    game = Game(screen)

    state = "menu"

    while True:

        dt = clock.tick(FPS) / 1000.0

        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if state == "menu":
                result = menu.handle_event(event)

                if result == "start":
                    game.reset()
                    state = "game"

                elif result == "quit":
                    pygame.quit()
                    sys.exit()

            elif state == "game":

                result = game.handle_event(event)

                if result == "menu":
                    state = "menu"

        if state == "menu":
            menu.update(dt)
            menu.draw()

        elif state == "game":

            game.update(dt)
            game.draw()

            if game.game_over:
                state = "menu"

        pygame.display.flip()


if __name__ == "__main__":
    main()
