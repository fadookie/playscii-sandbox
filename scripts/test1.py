from game_object import GameObject
from art import TileIter


class Canvas(GameObject):
    generate_art = True
    art_width, art_height = 54, 30  # approximately 16x9 aspect

    def pre_first_update(self):
        self.art.set_palette_by_name('gameboy')

    def update(self):
        for frame, layer, x, y in TileIter(self.art):
            char = self.art.charset.last_index - 5
            fg = self.art.palette.get_random_color_index()
            bg = 3 % len(self.art.palette.colors)
            self.art.set_tile_at(frame, layer, x, y, char, fg, bg)
        GameObject.update(self)
