
from game_object import GameObject

import os, random, math, datetime
import zipfile, tempfile
import subprocess
import webbrowser
from shutil import copyfile

import games.doomlaunch.scripts.omg as omg


# all path handling code assumes dir names have a slash at the end!
IDGAMES_PATH = '/home/jpl/idgames/'
IDGAMES_URL = 'https://www.doomworld.com/idgames/'
IWAD_DIR = '/home/jpl/game/doom/iwad/'
GZDOOM_BIN = 'gzdoom'
SLADE_BIN = '/home/jpl/game/slade/dist/slade'
ARCHIVE_BASE_DIR = '/home/jpl/projects/wadnesday_stream/'
OBS_NAME_TEXT_FILE = '/home/jpl/wadname.txt'
LOG_FILE = '/home/jpl/wads_played.log'
TXT_ENCODING = 'cp1252' # as opposed to 'utf-8'
# ignore files with these strings in their path
EXCLUDED_PATH_STRINGS = [
    'roguestuff/', 'deathmatch/', 'historic/', 'source/', 'utils/', 'lmps/'
]

# if non-empty, use this file instead of a random pick
#DEBUG_FILE = 'levels/doom2/Ports/d-f/d3prxsit.zip'
#DEBUG_FILE = 'levels/doom2/m-o/nldoom25.zip'
#DEBUG_FILE = 'levels/doom2/a-c/aloha808.zip'
#DEBUG_FILE = 'levels/doom2/s-u/swblstcs.zip'
#DEBUG_FILE = 'levels/doom2/megawads/btsx_e1.zip'
#DEBUG_FILE = 'levels/doom2/Ports/s-u/sarin.zip' # weird readme
#DEBUG_FILE = 'levels/doom/g-i/goth1.zip' # unsupported compression
#DEBUG_FILE = 'levels/doom2/Ports/p-r/pott.zip' # long lines in readme
#DEBUG_FILE = 'levels/doom2/deathmatch/a-c/coolcty2.zip' # unix newlines
#DEBUG_FILE = 'levels/doom/v-z/zone3.zip' # readme starts with weird characters
#DEBUG_FILE = 'levels/doom2/Ports/a-c/cmphm.zip' # invalid wad
#DEBUG_FILE = 'levels/doom2/Ports/m-o/nh5.zip' # invalid zip entries
#DEBUG_FILE = 'levels/reviews/d1rev0bg.zip' # no readme
#DEBUG_FILE = 'levels/doom2/Ports/megawads/cchest.zip' # included DEH (map names only)
#DEBUG_FILE = 'graphics/spooon.zip' # some BMP images
#DEBUG_FILE = 'themes/x-rated/i_am_old_enough_to_look_at_this/demltion.zip' # jpg
#DEBUG_FILE = 'graphics/doom2gif.zip' # many gifs
#DEBUG_FILE = 'levels/doom2/m-o/mordeth.zip' # pcxs
DEBUG_FILE = ''

# when false launch into release mode, ie no editing
DEBUG = False

class LauncherBrain(GameObject):
    
    handle_key_events = True
    cmdline = None
    readme_view = None
    sound_filenames = {
        'play1': 'DSDOROPN.ogg',
        'random1': 'DSTELEPT.ogg',
        'switch1': 'DSSWTCHN.ogg'
    }
    
    def pre_first_update(self):
        self.files = []
        self.selected_file_name = ''
        self.rand_picks = []
        self.included_files = []
        self.included_dehs = []
        self.rand_file_title = ''
        self.rand_file_author = ''
        self.randfile = None
        self.gzdoom_process = None
        if not DEBUG:
            self.app.can_edit = False
            self.app.ui.set_game_edit_ui_visibility(False)
            self.app.update_window_title()
            self.app.ui.message_line.post_line('', 5)
        self.world.camera.set_loc_from_obj(self.world.objects['cameramark1'])
        # remember camera home position for swim
        self.camera_base_x, self.camera_base_y = self.world.camera.x, self.world.camera.y
        self.world.allow_pause = False
        # grab objects we send data to
        self.titlebar = self.world.get_first_object_of_type("TitleBar")
        self.readme_view = self.world.get_first_object_of_type("ReadmeView")
        self.files_view = self.world.get_first_object_of_type("FilesView")
        self.levels_view = self.world.get_first_object_of_type("LevelsView")
        self.extra_files_view = self.world.get_first_object_of_type("ExtraFilesView")
        self.random_button = self.world.get_first_object_of_type("RandomButton")
        self.play_button = self.world.get_first_object_of_type("PlayButton")
        self.launch_menu = self.world.get_first_object_of_type("LaunchMenu")
        self.launch_button = self.world.get_first_object_of_type("LaunchButton")
        self.cancel_button = self.world.get_first_object_of_type("CancelButton")
        self.begin_button = self.world.get_first_object_of_type("BeginButton")
        self.include_button = self.world.get_first_object_of_type("IncludeButton")
        self.clear_extras_button = self.world.get_first_object_of_type("ClearExtraFilesButton")
        self.cmdline = self.world.get_first_object_of_type("CommandLine")
        for element in self.get_intro_ui_objects():
            element.visible = True
        for element in self.get_main_ui_objects() + self.get_launch_ui_objects():
            if element:
                element.brain = self
                element.visible = False
        self.begin_button.brain = self
        self.image_view = self.world.spawn_object_of_class("ImageView")
        self.image_view.visible = False
        # pain buddy on start
        self.startbuddy = self.world.spawn_object_of_class("BGPainElemental")
    
    def get_main_ui_objects(self):
        return [self.files_view, self.levels_view, self.titlebar,
                self.readme_view, self.random_button, self.play_button,
                self.extra_files_view, self.include_button,
                self.clear_extras_button]
    
    def get_launch_ui_objects(self):
        return [self.launch_menu, self.launch_button, self.cancel_button,
                self.cmdline]
    
    def get_intro_ui_objects(self):
        return [self.begin_button, self.world.objects['date'],
                self.world.objects['titlecard']]
    
    def begin(self):
        self.startbuddy.destroy()
        # stop swim
        self.world.camera.x, self.world.camera.y = self.camera_base_x, self.camera_base_y
        self.world.camera.x_tilt = 0
        self.world.camera.y_tilt = 0
        # show main UI, hide intro UI
        for element in self.get_main_ui_objects():
            element.visible = True
        for element in self.get_intro_ui_objects():
            element.visible = False
        self.files = []
        for root, dirs, files in os.walk(IDGAMES_PATH):
            for filename in files:
                if not filename.lower().endswith('.zip'):
                    continue
                filepath = os.path.join(root, filename)
                filepath = filepath[len(IDGAMES_PATH):]
                exclude = False
                for s in EXCLUDED_PATH_STRINGS:
                    if filepath.find(s) != -1:
                        exclude = True
                        break
                if exclude:
                    continue
                self.files.append(filepath)
        self.files.sort()
        self.new_random_file()
    
    def update(self):
        GameObject.update(self)
        if self.world.objects['titlecard'].visible:
            swim_x = math.cos(self.world.app.frames / 50) / 2
            swim_y = math.sin(self.world.app.frames / 50) / 2
            self.world.camera.x = self.camera_base_x + swim_x * 5
            self.world.camera.y = self.camera_base_y + swim_y * 3
            self.world.camera.x_tilt = -swim_x
            self.world.camera.y_tilt = -swim_y
        if self.gzdoom_process:
            self.gzdoom_process = None
            # clear OBS text
            obs_file = open(OBS_NAME_TEXT_FILE, 'w')
            obs_file.write('')
            obs_file.close()
            # spawn another background caco
            class_to_spawn = "BGPainElemental" if random.random() < 0.1 else "BGCaco"
            self.world.spawn_object_of_class(class_to_spawn)
    
    def handle_key_down(self, key, shift_pressed, alt_pressed, ctrl_pressed):
        if self.cmdline and self.cmdline.visible:
            self.cmdline.handle_key(key, shift_pressed, alt_pressed, ctrl_pressed)
            return
        focused = self.readme_view
        if not focused:
            return
        if key == 'up':
            focused.top_view_line -= 1
        elif key == 'down':
            focused.top_view_line += 1
        elif key == 'pageup':
            focused.top_view_line -= 10
        elif key == 'pagedown':
            focused.top_view_line += 10
        elif key == 'home':
            focused.top_view_line = 0
        elif key == 'end':
            focused.top_view_line = len(focused.lines) - 5
        elif key == 'return':
            self.show_launch_controls()
        # move through history
        elif key == 'left':
            idx = self.rand_picks.index(self.selected_file_name)
            if idx > 0:
                self.select_file(self.rand_picks[idx-1])
                self.play_sound('switch1')
        elif key == 'right':
            idx = self.rand_picks.index(self.selected_file_name)
            if idx < len(self.rand_picks) - 1:
                self.select_file(self.rand_picks[idx+1])
                self.play_sound('switch1')
        elif key == 'f3':
            webbrowser.open(IDGAMES_URL + self.selected_file_name)
        elif key == 'f4':
            subprocess.run([SLADE_BIN, IDGAMES_PATH + self.selected_file_name])
        elif key == 'f5':
            subprocess.run(['file-roller', IDGAMES_PATH + self.selected_file_name])
        elif key == 'r' and not shift_pressed:
            subprocess.run(['gedit', IDGAMES_PATH + os.path.splitext(self.selected_file_name)[0] + '.txt'])
        focused.top_view_line = max(0, min(focused.top_view_line,
                                           len(focused.lines) - 1))
        focused.redraw()
    
    def display_readme(self):
        readme_filename = os.path.splitext(self.selected_file_name)[0] + '.txt'
        try:
            readme_file = open(IDGAMES_PATH + readme_filename)
            readme_lines = readme_file.readlines()
        except:
            if not os.path.exists(IDGAMES_PATH + readme_filename):
                return []
            readme_file = open(IDGAMES_PATH + readme_filename, 'rb')
            readme_lines = readme_file.read().decode(TXT_ENCODING, errors='ignore').split('\n')
        self.readme_view.update_title(os.path.basename(readme_filename))
        self.readme_view.update_lines(readme_lines)
        return readme_lines
    
    def display_zip_text_file(self, filename):
        try:
            readme_data = self.randfile.read(filename)
            readme_lines = readme_data.decode(TXT_ENCODING, errors='ignore').split('\r\n')
        except:
            readme_lines = ["[ERROR, couldn't display!]"]
        self.readme_view.update_title(os.path.basename(filename))
        self.readme_view.update_lines(readme_lines)
    
    def display_image(self, filename):
        # extract image to temp file, hand it to viewer object's SpriteRenderable
        image_filename = '/tmp/' + filename
        image_file = open(image_filename, 'wb')
        image_file.write(self.randfile.read(filename))
        image_file.close()
        self.image_view.set_image(image_filename)
    
    def fill_levels_view(self):
        if not self.levels_view:
            return
        # string list of eg: "MyWad.wad: MAP01"
        levels = []
        # from wadls.py:
        for f in self.randfile.namelist():
            if os.path.splitext(f.lower())[1] == '.wad':
                wad = omg.WAD()
                # read file from zip
                temp_file = tempfile.NamedTemporaryFile()
                try:
                    zipped_file = self.randfile.open(f)
                except:
                    continue
                temp_file.write(zipped_file.read())
                # flush so omg can read it
                temp_file.flush()
                try:
                    wad.from_file(temp_file.name)
                except:
                    print('%s invalid' % f)
                    continue
                maps = wad.maps.find('*')
                if len(maps) == 0:
                    continue
                for map_name in maps:
                    levels.append('%s: %s' % (f, map_name))
        levels.sort()
        title = '%s Level%s' % (len(levels), ['s', ''][len(levels) == 1])
        self.levels_view.update_title(title)
        self.levels_view.update_lines(levels)
    
    def select_file(self, filename):
        self.selected_file_name = filename
        self.randfile = zipfile.ZipFile(IDGAMES_PATH + filename)
        # list of files in zip
        files = self.randfile.namelist()
        files.sort()
        self.files_view.selected_line = -1
        self.files_view.update_title(os.path.basename(filename))
        self.files_view.update_lines(files)
        self.readme_view.top_view_line = 0
        self.rand_file_title = ''
        self.rand_file_author = ''
        readme_lines = self.display_readme()
        # scan readme for title and author
        for line in readme_lines:
            if line.strip().lower().startswith('title'):
                self.rand_file_title = line[line.find(':')+1:].strip()
            elif self.rand_file_author == '' and line.strip().lower().startswith('author'):
                self.rand_file_author = line[line.find(':')+1:].strip()
        title = self.rand_file_title if self.rand_file_title != '' else filename
        if self.rand_file_author != '':
            title += ' - ' + self.rand_file_author
        self.titlebar.update_title(title)
        # show this in window title bar
        self.world.game_title = 'WAD Wednesday: %s' % title
        self.app.update_window_title()
        # show filename and date beneath title bar
        file_line = filename
        file_dt = os.path.getmtime(IDGAMES_PATH + filename)
        file_dt = datetime.datetime.fromtimestamp(file_dt)
        file_date = file_dt.strftime('%Y-%m-%d')
        # pad
        date_width = self.titlebar.art.width - len(file_line)
        date_width -= len(file_date) - 4
        file_line += file_date.rjust(date_width)
        self.titlebar.update_lines([file_line])
        self.fill_levels_view()
    
    def new_random_file(self):
        rand_file_name = random.choice(self.files)
        if DEBUG_FILE != '':
            rand_file_name = DEBUG_FILE
        self.rand_picks.append(rand_file_name)
        self.app.log('picked: %s' % rand_file_name)
        self.select_file(rand_file_name)
        self.play_sound('random1')
    
    def include_current_file(self):
        if self.selected_file_name in self.included_files:
            return
        self.included_files.append(self.selected_file_name)
        # add any enclosed DEHs to list
        z = zipfile.ZipFile(IDGAMES_PATH + self.selected_file_name)
        for f in z.namelist():
            if f.lower().endswith('.deh'):
                self.included_dehs.append(f)
        self.extra_files_view.update_lines(self.included_files)
    
    def clear_included_files(self):
        self.included_files = []
        self.included_dehs = []
    
    def show_launch_controls(self):
        for element in self.get_launch_ui_objects():
            element.visible = True
        for element in self.get_main_ui_objects():
            element.renderable.alpha = 0.25
        self.launch_menu.set_selection(0)
        self.cmdline.redraw()
    
    def hide_launch_controls(self):
        for element in self.get_launch_ui_objects():
            element.visible = False
        for element in self.get_main_ui_objects():
            element.renderable.alpha = 1
    
    def get_full_command_line(self, parse_dehs=True):
        s = self.cmdline.contents
        s = s.replace('$GZDOOM', GZDOOM_BIN)
        if self.launch_menu.iwad in ['', 'wadsmoosh']:
            s = s.replace('$IWAD', '')
        else:
            s = s.replace('$IWAD', '-iwad %s%s.wad' % (IWAD_DIR, self.launch_menu.iwad))
        s = s.replace('$MAINZIP', '-file ' + IDGAMES_PATH + self.selected_file_name)
        includes = ''
        for include in self.included_files:
            includes += IDGAMES_PATH + include + ' '
        s = s.replace('$EXTRAZIPS', includes)
        if parse_dehs:
            dehs = ''
            for f in self.randfile.namelist():
                if f.lower().endswith('.deh'):
                    dehs += f + ' '
            for deh in self.included_dehs:
                dehs += deh + ' '
            if len(dehs) == 0:
                s = s.replace('$DEHFILES', '')
            else:
                s = s.replace('$DEHFILES', '-deh ' + dehs)
        s = s.replace('  ', ' ')
        return s
    
    def process_dehs(self):
        # extract all dehs from main file and included files,
        # return string with -deh [files]; if none, return ''
        dehs = []
        zips = [self.randfile]
        for filename in self.included_files:
            zips.append(zipfile.ZipFile(IDGAMES_PATH + filename))
        for zf in zips:
            for filename in zf.namelist():
                if filename.lower().endswith('.deh'):
                    f = open('/tmp/' + filename, 'wb')
                    f.write(zf.open(filename).read())
                    f.flush()
                    dehs.append(f)
        if len(dehs) == 0:
            return ''
        return '-deh ' + ' '.join(d.name for d in dehs)
    
    def launch(self):
        # copy files to archive dir
        archive_dir = ARCHIVE_BASE_DIR + datetime.datetime.now().strftime('%Y%m%d/')
        if not os.path.exists(archive_dir):
            os.mkdir(archive_dir)
        for filename in [self.selected_file_name] + self.included_files:
            src_filename = IDGAMES_PATH + filename
            dest_filename = archive_dir + os.path.basename(filename)
            copyfile(src_filename, dest_filename)
        # write to a file that OBS uses to display wad's name on stream
        obs_text = self.rand_file_title
        if self.rand_file_author != '':
            obs_text += ' - ' + self.rand_file_author
        obs_file = open(OBS_NAME_TEXT_FILE, 'w')
        obs_file.write(obs_text)
        obs_file.close()
        # log level we're playing to a file
        log_text = '%s: %s\n' % (obs_text,
                                 IDGAMES_URL + self.selected_file_name)
        self.logfile = open(LOG_FILE, 'a')
        self.logfile.write(log_text)
        self.logfile.close()
        # get contents of command line
        cmd = self.get_full_command_line(parse_dehs=False)
        # if any DEHs should be loaded, extract and pipe them in
        cmd = cmd.replace('$DEHFILES', self.process_dehs())
        # get ready and launch
        self.hide_launch_controls()
        self.play_sound('play1')
        self.gzdoom_process = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
        # playscii won't continue until stdout ceases, ie gzdoom stops
        for line in self.gzdoom_process.stdout:
            pass
