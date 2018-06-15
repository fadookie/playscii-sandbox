from game_util_objects import Player, StaticTileObject
# from collision import CST_AABB


class MyGamePlayer(Player):
    "Generic starter player class for newly created games."
    art_src = 'default_player'
    # no "move" state art, so just use stand state for now
    move_state = 'stand'
    col_radius = 0.5


class MyGameObject(StaticTileObject):
    "Generic starter object class for newly created games."
    def update(self):
        # write "hello" in a color that shifts over time
        color = self.art.palette.get_random_color_index()
        self.art.write_string(0, 0, 3, 2, 'hello!', color)
        # run parent class update
        StaticTileObject.update(self)
