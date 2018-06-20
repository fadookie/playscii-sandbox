from game_object import GameObject
from art import TileIter

from .opensimplex import OpenSimplex


class Canvas(GameObject):
    generate_art = True
    art_width, art_height = 54, 30  # approximately 16x9 aspect
    simplex = OpenSimplex()

    def pre_first_update(self):
        self.art.set_palette_by_name('gameboy')

        # self.set_timer_function('noise', self.noise_permutation, 0.2)

    def update(self):
        self.noise_permutation()
        GameObject.update(self)

    def noise_permutation(self):
        time = self.world.get_elapsed_time() * 0.001
        xyscale = 0.20
        for frame, layer, x, y in TileIter(self.art):
            noise = self.simplex.noise3d(
                x=x * xyscale,
                y=y * xyscale,
                z=time)
            char = self.art.charset.last_index - 5
            fg = int((noise + 0.5) * len(self.art.palette.colors))
            bg = 0 % len(self.art.palette.colors)
            self.art.set_tile_at(frame, layer, x, y, char, fg, bg)
