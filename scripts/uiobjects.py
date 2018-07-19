
import os, datetime

from game_object import GameObject
from renderable_sprite import SpriteRenderable

from key_shifts import shift_map


# ignore wad, pk3, exe files etc
NON_TEXT_EXTENSIONS = ['.wad', '.pk3', '.exe', '.lmp']
# extensions supported by PIL
IMAGE_EXTENSIONS = ['.bmp', '.jpg', '.gif', '.png', '.pcx']


class DOSWindow(GameObject):
    
    top_bar_char = 205
    base_fg_color = 8
    base_bg_color = 0
    top_view_line = 0
    selected_line = -1
    physics_move = False
    lines = []
    
    def update_title(self, new_title):
        # clear top bar first
        for x in range(1, self.art.width - 1):
            self.art.set_tile_at(0, 0, x, 0, self.top_bar_char,
                                 self.base_fg_color, self.base_bg_color)
        new_title = ' %s ' % new_title
        x = int((self.art.width / 2) - (len(new_title) / 2))
        self.art.write_string(0, 0, x, 0, new_title,
                              fg_color_index=self.base_bg_color,
                              bg_color_index=self.base_fg_color)
    
    def redraw(self):
        # clear previous text
        for y in range(1, self.art.height - 1):
            selected = self.selected_line - self.top_view_line == y
            fg = self.base_bg_color if selected else self.base_fg_color
            bg = self.base_fg_color if selected else self.base_bg_color
            self.art.write_string(0, 0, 2, y, ' ' * (self.art.width - 3),
                                  fg_color_index=fg, bg_color_index=bg)
        y = 1
        for line in self.lines[self.top_view_line:]:
            self.art.write_string(0, 0, 2, y, line)
            y += 1
            if y >= self.art.height - 1:
                break
    
    def update_lines(self, lines):
        self.lines = lines
        # wrap wider-than-window lines
        margin = 4
        for i,line in enumerate(lines):
            if len(line) >= self.art.width - margin:
                new_line = line[:self.art.width - margin]
                last_space_index = new_line.rfind(' ')
                if last_space_index == -1:
                    last_space_index = self.art.width - margin
                new_line = line[:last_space_index]
                lines[i] = new_line
                lines.insert(i+1, line[last_space_index+1:])
        self.redraw()
    
    def mouse_wheeled(self, wheel_y):
        if wheel_y > 0:
            self.top_view_line -= 1
        elif wheel_y < 0:
            self.top_view_line += 1
        self.top_view_line = min(max(0, self.top_view_line),
                                 len(self.lines) - 1)
        self.redraw()


class TitleBar(DOSWindow):
    art_src = 'titlebar'

class ReadmeView(DOSWindow):
    art_src = 'readme'
    handle_mouse_events = True

class FilesView(DOSWindow):
    handle_mouse_events = True
    art_src = 'filelist'
    def clicked(self, button, mouse_x, mouse_y):
        # mouse loc -> row # clicked -> list item # -> file to view
        _,tile_y = self.get_tile_at_point(mouse_x, mouse_y)
        tile_y -= 1
        if tile_y == 0:
            self.selected_line = -1
            self.brain.display_readme()
            self.redraw()
            return
        tile_y += self.top_view_line
        if tile_y > len(self.lines):
            return
        filename = self.lines[tile_y - 1]
        if os.path.splitext(filename)[1].lower() in NON_TEXT_EXTENSIONS:
            return
        if os.path.splitext(filename)[1].lower() in IMAGE_EXTENSIONS:
            self.brain.display_image(filename)
        else:
            self.brain.display_zip_text_file(filename)
        self.selected_line = tile_y
        self.redraw()

class ExtraFilesView(DOSWindow):
    art_src = 'extrafileslist'
    def update(self):
        self.visible = len(self.brain.included_files) > 0

class LevelsView(DOSWindow):
    handle_mouse_events = True
    art_src = 'levellist'

class RandomButton(GameObject):
    handle_mouse_events = True
    art_src = 'randobutton'
    def clicked(self, button, mouse_x, mouse_y):
        self.brain.new_random_file()

class PlayButton(GameObject):
    handle_mouse_events = True
    art_src = 'playbutton'
    def clicked(self, button, mouse_x, mouse_y):
        self.brain.show_launch_controls()

class IncludeButton(GameObject):
    handle_mouse_events = True
    art_src = 'includebutton'
    def clicked(self, button, mouse_x, mouse_y):
        self.brain.include_current_file()

class ClearExtraFilesButton(GameObject):
    handle_mouse_events = True
    art_src = 'clearincludesbutton'
    def clicked(self, button, mouse_x, mouse_y):
        self.brain.clear_included_files()
    def update(self):
        self.visible = len(self.brain.included_files) > 0

class LaunchMenu(GameObject):
    
    handle_mouse_events = True
    art_src = 'launchmenu'
    base_fg_color = DOSWindow.base_fg_color
    base_bg_color = DOSWindow.base_bg_color
    iwad = ''
    menu_items = {
        0: 'wadsmoosh',
        1: 'doom',
        2: 'doom2',
        3: 'tnt',
        4: 'plutonia',
        5: 'heretic',
        6: 'hexen',
        7: 'chex'
    }
    
    def pre_first_update(self):
        self.cmdline = self.world.get_first_object_of_type("CommandLine")
    
    def set_selection(self, selection_index):
        # highlight selected line
        for y in range(1, self.art.height - 1):
            selected = selection_index == y - 1
            fg = self.base_bg_color if selected else self.base_fg_color
            bg = self.base_fg_color if selected else self.base_bg_color
            for x in range(1, self.art.width - 1):
                self.art.set_color_at(0, 0, x, y, fg, fg=True)
                self.art.set_color_at(0, 0, x, y, bg, fg=False)
        if self.menu_items[selection_index] == 0:
            self.iwad = ''
        else:
            self.iwad = self.menu_items[selection_index]
        contents = '$GZDOOM $IWAD $MAINZIP $EXTRAZIPS $DEHFILES '
        self.cmdline.set_contents(contents)
    
    def clicked(self, button, mouse_x, mouse_y):
        _,tile_y = self.get_tile_at_point(mouse_x, mouse_y)
        tile_y -= 1
        if tile_y == 0 or tile_y == self.art.height:
            return
        self.set_selection(tile_y - 1)


class LaunchButton(GameObject):
    handle_mouse_events = True
    art_src = 'launchbutton'
    def clicked(self, button, mouse_x, mouse_y):
        self.brain.launch()

class CancelButton(GameObject):
    handle_mouse_events = True
    art_src = 'cancelbutton'
    def clicked(self, button, mouse_x, mouse_y):
        self.brain.hide_launch_controls()

class BeginButton(GameObject):
    handle_mouse_events = True
    art_src = 'beginbutton'
    def clicked(self, button, mouse_x, mouse_y):
        self.brain.begin()

class DateDisplay(GameObject):
    art_src = 'date'
    def pre_first_update(self):
        s = datetime.datetime.now().strftime('%Y-%m-%d')
        self.art.write_string(0, 0, 0, 0, s)


class CommandLine(GameObject):
    art_src = 'cmdline'
    input_start_x = 2
    input_y = 1
    output_y = 4
    
    def pre_first_update(self):
        self.contents = ''
        self.caret_index = 0
    
    def set_contents(self, new_contents):
        self.contents = new_contents
        self.caret_index = len(self.contents)
        self.redraw()
    
    def handle_key(self, key, shift_pressed, alt_pressed, ctrl_pressed):
        if key == 'left' and self.caret_index > 0:
            self.caret_index -= 1
        elif key == 'right' and self.caret_index < len(self.contents):
            self.caret_index += 1
        elif key == 'return':
            self.brain.launch()
        elif key == 'home' or key == 'pageup' or key == 'keypad 7':
            self.caret_index = 0
        elif key == 'end' or key == 'pagedown' or key == 'keypad 1':
            self.caret_index = len(self.contents)
        elif key == 'backspace':
            # alt-backspace handling
            if alt_pressed:
                idx = self.contents[:self.caret_index].rfind(' ')
                self.contents = self.contents[:idx] + self.contents[self.caret_index:]
                self.caret_index = idx
            elif self.caret_index == len(self.contents):
                self.contents = self.contents[:len(self.contents) - 1]
                self.caret_index -= 1
            else:
                self.contents = self.contents[:self.caret_index-1] + self.contents[self.caret_index:]
                self.caret_index -= 1
        elif key == 'escape':
            self.brain.hide_launch_controls()
        elif key == 'space':
            self.insert_at(' ', self.caret_index)
            self.caret_index += 1
        # normal alphanumeric key
        elif len(key) == 1:
            if shift_pressed:
                if key.isalpha():
                    key = key.upper()
                else:
                    key = shift_map.get(key, '')
            if not key:
                return
            self.insert_at(key, self.caret_index)
            self.caret_index += 1
        self.redraw()
    
    def insert_at(self, to_insert, index):
        new_contents = self.contents[:index] + to_insert
        new_contents += self.contents[index:]
        self.contents = new_contents
    
    def redraw(self):
        # clear lines first
        for x in range(1, self.art.width - 1):
            self.art.write_string(0, 1, 1, self.input_y,
                                  ' ' * (self.art.width - 2))
            self.art.write_string(0, 1, 1, self.output_y,
                                  ' ' * (self.art.width - 2))
            self.art.write_string(0, 1, 1, self.output_y + 1,
                                  ' ' * (self.art.width - 2))
            self.art.write_string(0, 1, 1, self.output_y + 2,
                                  ' ' * (self.art.width - 2))
        self.art.write_string(0, 1, self.input_start_x, self.input_y,
                              self.contents)
        # show full command line
        s = self.brain.get_full_command_line()
        y = self.output_y
        # overflow to lower lines if needed
        lines_drawn = 0
        while True:
            lines_drawn += 1
            line = s[:min(len(s), self.art.width - 3)]
            self.art.write_string(0, 1, self.input_start_x, y, line)
            s = s.replace(line, '')
            y += 1
            if len(s) <= 0:
                break
    
    def update(self):
        GameObject.update(self)
        if not self.visible:
            return
        # clear line and set caret
        if self.caret_index >= self.art.width - 3:
            return
        for x in range(1, self.art.width - 1):
            self.art.set_char_index_at(0, 2, x, self.input_y, 0)
        # blink
        if self.app.get_elapsed_time() % 3 != 0:
            return
        caret_char = self.art.charset.get_char_index('_')
        self.art.set_char_index_at(0, 2, self.caret_index + 2, self.input_y, caret_char)


class ImageView(GameObject):
    
    # rough screen dimensions - scale within this
    min_x = -110
    max_x = 110
    min_y = -60
    max_y = 60
    
    art_off_pct_x, art_off_pct_y = 0., 0.
    handle_mouse_events = True
    consume_mouse_events = True
    art_src = 'imagebg'
    
    def pre_first_update(self):
        self.sr = None
    
    def set_image(self, filename):
        self.sr = SpriteRenderable(self.app, filename)
        self.visible = True
        #
        # scale and position image
        #
        aspect = self.sr.texture.width / self.sr.texture.height
        inv_aspect = self.sr.texture.height / self.sr.texture.width
        screen_aspect = self.app.window_width / self.app.window_height
        self.sr.scale_x = aspect
        self.sr.scale_y = self.sr.scale_x * inv_aspect * screen_aspect
        # scale up to fill a reasonable % of screen
        self.sr.scale_x = (self.max_x - self.min_x) / 2 * aspect
        self.sr.scale_y = self.sr.scale_x * inv_aspect
        self.sr.scale_x /= 2
        self.sr.scale_y /= 2
        # center
        self.sr.x = -self.sr.scale_x / 2
        self.sr.y = -self.sr.scale_y / 2
        # GO should shadow sprite
        self.x = self.sr.x
        self.y = self.sr.y + self.sr.scale_y
        self.z = 1
        self.set_scale(self.sr.scale_x, self.sr.scale_y, 1)
    
    def clicked(self, button, mouse_x, mouse_y):
        self.visible = False
        self.sr = None
    
    def render(self, layer, z_override=None):
        GameObject.render(self, layer, z_override)
        if self.sr:
            self.sr.render()
