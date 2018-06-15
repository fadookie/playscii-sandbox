
from game_object import GameObject
from game_util_objects import Player


class MyGamePlayer(Player):
    "Generic starter player class for newly created games."
    art_src = 'default_player'
    # no "move" state art, so just use stand state for now
    move_state = 'stand'


class MyGameObject(GameObject):
    "Generic starter object class for newly created games."
    def update(self):
        # write "hello" in a color that shifts over time
        color = self.art.palette.get_random_color_index()
        self.art.write_string(0, 0, 3, 2, 'hello!', color)
        # run parent class update
        GameObject.update(self)
