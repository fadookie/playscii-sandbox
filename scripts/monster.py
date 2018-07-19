
from game_object import GameObject

import math, random

class BGCaco(GameObject):
    
    "lil roamin' caco"
    
    art_src = 'caco'
    state_changes_art = True
    facing_changes_art = True
    alpha = 1
    base_z = -1
    goal_spot = (0, 0)
    goal_min_x = -110
    goal_max_x = 110
    goal_min_y = -60
    goal_max_y = 60
    move_accel_x = move_accel_y = 75
    
    def pre_first_update(self):
        self.pick_new_goal()
        self.z = self.base_z
    
    def pick_new_goal(self):
        if self.goal_min_y > self.goal_max_y:
            self.goal_min_y, self.goal_max_y = self.goal_max_y, self.goal_min_y
        self.goal_spot = (random.randint(self.goal_min_x, self.goal_max_x),
                          random.randint(self.goal_min_y, self.goal_max_y))
    
    def update(self):
        dx = self.goal_spot[0] - self.x
        dy = self.goal_spot[1] - self.y
        dist_to_goal = math.sqrt(dx ** 2 + dy ** 2)
        if dist_to_goal <= 1:
            self.pick_new_goal()
        else:
            dx *= 1 / dist_to_goal
            dy *= 1 / dist_to_goal
            self.move(dx, dy)
        self.z = abs(math.sin(self.app.get_elapsed_time() / 1000))
        self.z *= 5
        self.z -= 8
        GameObject.update(self)

class BGPainElemental(BGCaco):
    art_src = 'pain'
    handle_mouse_events = True
    sound_filenames = {
        'hurt': 'DSPEPAIN.ogg'
    }
    def clicked(self, button, mouse_x, mouse_y):
        self.play_sound('hurt')
