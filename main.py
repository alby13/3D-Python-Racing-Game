import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import math
import random
import sys
import time

# Initialize Pygame and OpenGL
pygame.init()
WIDTH, HEIGHT = 1024, 768
pygame.display.set_mode((WIDTH, HEIGHT), DOUBLEBUF | OPENGL)
glClearColor(0.0, 0.0, 0.0, 1.0) 
original_flags = DOUBLEBUF | OPENGL
screen = pygame.display.set_mode((WIDTH, HEIGHT), original_flags)
pygame.display.set_caption("Python Racing USA")

# Initialize mixer and start background music  <-- ADDED THIS BLOCK
pygame.mixer.init()
try:
    pygame.mixer.music.load('bgmusic.mp3')  # Make sure 'bgmusic.mp3' is in the correct directory!
    pygame.mixer.music.play(-1) # Loop indefinitely
except pygame.error as e:
    print(f"Could not load or play music: {e}")  #Error handling

# Global font objects (initialized once)
hud_font = pygame.font.SysFont("Arial", 24)
countdown_font = pygame.font.SysFont("Arial", 100)
game_over_font = pygame.font.SysFont("Arial", 60)

# Setup OpenGL perspective
glEnable(GL_DEPTH_TEST)
glEnable(GL_LIGHTING)
glEnable(GL_LIGHT0)
glEnable(GL_COLOR_MATERIAL)
glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)

glMatrixMode(GL_PROJECTION)
glLoadIdentity()
gluPerspective(60, (WIDTH / HEIGHT), 0.1, 500.0)

# --- OpenGL Setup ---
def resize_viewport(width, height):
    """Handles window resizing and fullscreen toggling."""
    global WIDTH, HEIGHT
    WIDTH = width
    HEIGHT = height

    # Set the viewport
    glViewport(0, 0, WIDTH, HEIGHT)

    # Update the projection matrix
    glViewport(0, 0, width, height)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(60, float(width) / float(height), 0.1, 500.0)  # Re-calculate perspective
    glMatrixMode(GL_MODELVIEW)  # Switch back to modelview matrix
    glLoadIdentity()


glEnable(GL_DEPTH_TEST)
glEnable(GL_LIGHTING)
glEnable(GL_LIGHT0)
glEnable(GL_COLOR_MATERIAL)
glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)

# Initial resize call to set up the viewport
resize_viewport(WIDTH, HEIGHT)

# Game state variables
class GameState:
    def __init__(self):
        self.game_started = False
        self.game_over = False
        self.countdown_active = False
        self.countdown_value = 3
        self.laps = 0
        self.total_laps = 3
        self.race_position = 1
        self.start_time = 0
        self.total_time = 0
        self.lap_times = []
        self.best_lap = float('inf')

# Player car variables
class PlayerCar:
    def __init__(self):
        self.position = [0, 0.5, 0]  # x, y, z
        self.rotation = 0  # Rotation in degrees (yaw)
        self.speed = 0
        self.acceleration = 0
        self.max_speed = 0.8
        self.steering_speed = 2.0
        self.gear = 0
        self.max_gear = 5
        self.collision_radius = 1.0
        self.laps = 0

# AI Car class
class AICar:
    def __init__(self, start_position, color):
        self.position = list(start_position)
        self.rotation = 0
        self.speed = random.uniform(0.2, 0.6)
        self.target_speed = random.uniform(0.3, 0.7)
        self.color = color
        self.track_position = 0
        self.laps = 0
        self.collision_radius = 1.0
        
    def update(self, track, dt):
        # Move forward based on speed
        self.position[0] += math.sin(math.radians(self.rotation)) * self.speed
        self.position[2] += math.cos(math.radians(self.rotation)) * self.speed
        
        # Get nearest track segment to follow
        nearest_point, nearest_idx = track.get_nearest_point(self.position)
        next_idx = (nearest_idx + 1) % len(track.points)
        next_point = track.points[next_idx]
        
        # Calculate direction to next point
        direction = [next_point[0] - self.position[0], next_point[2] - self.position[2]]
        target_angle = math.degrees(math.atan2(direction[0], direction[1])) % 360
        
        # Steering
        angle_diff = (target_angle - self.rotation) % 360
        if angle_diff > 180:
            angle_diff -= 360
        self.rotation += angle_diff * dt * 2
        
        # Adjust speed based on curve sharpness
        curve = abs(angle_diff)
        if curve > 30:
            self.target_speed = max(0.2, self.target_speed - 0.001 * curve)
        else:
            self.target_speed = min(random.uniform(0.3, 0.7), self.target_speed + 0.01)
        
        # Adjust actual speed toward target speed
        if self.speed < self.target_speed:
            self.speed += 0.01
        elif self.speed > self.target_speed:
            self.speed -= 0.02
            
        # Update track position for race standings
        self.track_position = nearest_idx + self.laps * len(track.points)
        
        # Check for lap completion
        if nearest_idx < 5 and self.position[2] > 0 and abs(self.position[0]) < 5:
            if track.last_checkpoint[self] < len(track.points) - 10:
                self.laps += 1
                track.last_checkpoint[self] = 0
                
        # Update checkpoint tracking
        if nearest_idx > track.last_checkpoint.get(self, 0):
            track.last_checkpoint[self] = nearest_idx

# Track class
class Track:
    def __init__(self):
        self.points = []
        self.width = 10.0
        self.generate_track()
        self.last_checkpoint = {}  # Keeps track of the last checkpoint for each car
        self.tree_positions = [] # List to store tree positions
        self.generate_trees()   # Call generate_trees() to initialize the trees
        
    # Precompute mountain positions and heights
    mountain_data = [
        (-100, 0, -150, random.uniform(20, 40)),
        (150, 0, -200, random.uniform(20, 40)),
        (0, 0, -250, random.uniform(20, 40)),
        (-200, 0, -180, random.uniform(20, 40)),
        (80, 0, -220, random.uniform(20, 40))
    ]

    def generate_track(self):
        # Generate an oval track
        num_points = 100
        track_length = 100
        track_width = 50
        
        for i in range(num_points):
            angle = 2 * math.pi * i / num_points
            x = math.sin(angle) * track_width
            z = math.cos(angle) * track_length
            
            # Add some elevation changes
            y = math.sin(angle * 2) * 2
            
            self.points.append((x, y, z))
    
    def get_nearest_point(self, position):
        min_dist = float('inf')
        nearest_idx = 0
        nearest_point = self.points[0]
        
        for i, point in enumerate(self.points):
            dist = math.sqrt((position[0] - point[0])**2 + (position[2] - point[2])**2)
            if dist < min_dist:
                min_dist = dist
                nearest_idx = i
                nearest_point = point
                
        return nearest_point, nearest_idx
    
    def get_road_boundaries(self, idx):
        point = self.points[idx]
        next_idx = (idx + 1) % len(self.points)
        next_point = self.points[next_idx]
        
        # Calculate direction vector
        dx = next_point[0] - point[0]
        dz = next_point[2] - point[2]
        length = math.sqrt(dx*dx + dz*dz)
        
        if length > 0:
            dx /= length
            dz /= length
            
        # Perpendicular vector
        px, pz = -dz, dx
        
        # Left and right road boundaries
        left_x = point[0] + px * self.width / 2
        left_z = point[2] + pz * self.width / 2
        right_x = point[0] - px * self.width / 2
        right_z = point[2] - pz * self.width / 2
        
        return (left_x, point[1], left_z), (right_x, point[1], right_z)
    
    def render(self):
        glColor3f(0.4, 0.4, 0.4)  # Gray road
        
        # Draw the road segments
        for i in range(len(self.points)):
            next_idx = (i + 1) % len(self.points)
            
            point = self.points[i]
            next_point = self.points[next_idx]
            
            left1, right1 = self.get_road_boundaries(i)
            left2, right2 = self.get_road_boundaries(next_idx)
            
            # Draw road segment as quad strip
            glBegin(GL_QUADS)
            
            # Add checkerboard pattern near the start/finish line
            if i < 5 or i > len(self.points) - 5:
                if i % 2 == 0:
                    glColor3f(1.0, 1.0, 1.0)  # White
                else:
                    glColor3f(0.0, 0.0, 0.0)  # Black
            else:
                glColor3f(0.4, 0.4, 0.4)  # Regular road color
            
            glVertex3f(left1[0], left1[1], left1[2])
            glVertex3f(right1[0], right1[1], right1[2])
            glVertex3f(right2[0], right2[1], right2[2])
            glVertex3f(left2[0], left2[1], left2[2])
            glEnd()
            
            # Draw yellow line down the middle
            glColor3f(1.0, 1.0, 0.0)  # Yellow
            glBegin(GL_LINES)
            mid1 = ((left1[0] + right1[0])/2, left1[1] + 0.01, (left1[2] + right1[2])/2)
            mid2 = ((left2[0] + right2[0])/2, left2[1] + 0.01, (left2[2] + right2[2])/2)
            
            # Draw dashed line
            if i % 2 == 0:
                glVertex3f(mid1[0], mid1[1], mid1[2])
                glVertex3f(mid2[0], mid2[1], mid2[2])
            glEnd()
            
            # Draw guardrails
            glColor3f(0.6, 0.6, 0.6)  # Light gray
            glBegin(GL_LINES)
            # Left guardrail
            glVertex3f(left1[0], left1[1] + 0.5, left1[2])
            glVertex3f(left2[0], left2[1] + 0.5, left2[2])
            
            # Right guardrail
            glVertex3f(right1[0], right1[1] + 0.5, right1[2])
            glVertex3f(right2[0], right2[1] + 0.5, right2[2])
            glEnd()
        
        # Draw the landscape
        self.render_landscape()
    
    def render_landscape(self):
        # Draw green ground
        glColor3f(0.0, 0.6, 0.0)  # Green
        glBegin(GL_QUADS)
        glVertex3f(-500, -0.1, -500)
        glVertex3f(-500, -0.1, 500)
        glVertex3f(500, -0.1, 500)
        glVertex3f(500, -0.1, -500)
        glEnd()
        
        # Draw mountains in the distance
        glColor3f(0.5, 0.5, 0.5)  # Mountain color
        
        # Draw a few simple mountains
        for pos in self.mountain_data:
            draw_mountain(pos[0], pos[1], pos[2], pos[3])

        # Draw trees
        for pos in self.tree_positions:
          draw_tree(pos[0], pos[1], pos[2], pos[3])

    def generate_trees(self):
        # Generate trees along the track
        num_trees = 200
        for _ in range(num_trees):
            # Randomly select a point index from the track
            idx = random.randint(0, len(self.points) - 1)
            point = self.points[idx]

            # Get road boundaries to place trees outside
            left_bound, right_bound = self.get_road_boundaries(idx)

            # Determine if the tree will be on the left or right
            side = random.choice([-1, 1])  # -1 for left, 1 for right

            # Offset from the road boundary (add some randomness)
            offset = random.uniform(2, 5)

            # Calculate the perpendicular vector 
            dx = left_bound[0] - point[0]  # Vector from center to left edge
            dz = left_bound[2] - point[2]
            # Normalize the perpendicular vector
            length = math.sqrt(dx*dx + dz*dz)
            if length > 0:  # Avoid division by zero
                dx /= length
                dz /= length

            # Calculate tree position.  Corrected calculation:
            tree_x = point[0] + side * (self.width / 2 + offset) * dx
            tree_z = point[2] + side * (self.width / 2 + offset) * dz

            # Get y position from track point (add small offset for ground)
            tree_y = point[1] + 0.1

            # Random tree height
            tree_height = random.uniform(3, 6)
            self.tree_positions.append((tree_x, tree_y, tree_z, tree_height))

def draw_car(x, y, z, rotation, color=(1.0, 0.0, 0.0)):
    glPushMatrix()
    
    # Position and rotate the car
    glTranslatef(x, y, z)
    glRotatef(rotation, 0, 1, 0)
    
    # Main car body
    glColor3f(color[0], color[1], color[2])
    glBegin(GL_QUADS)
    
    # Bottom
    glVertex3f(-0.7, 0.0, -1.5)
    glVertex3f(0.7, 0.0, -1.5)
    glVertex3f(0.7, 0.0, 1.5)
    glVertex3f(-0.7, 0.0, 1.5)
    
    # Front
    glVertex3f(-0.7, 0.0, 1.5)
    glVertex3f(0.7, 0.0, 1.5)
    glVertex3f(0.7, 0.5, 1.2)
    glVertex3f(-0.7, 0.5, 1.2)
    
    # Back
    glVertex3f(-0.7, 0.0, -1.5)
    glVertex3f(0.7, 0.0, -1.5)
    glVertex3f(0.7, 0.5, -1.3)
    glVertex3f(-0.7, 0.5, -1.3)
    
    # Left side
    glVertex3f(-0.7, 0.0, -1.5)
    glVertex3f(-0.7, 0.0, 1.5)
    glVertex3f(-0.7, 0.5, 1.2)
    glVertex3f(-0.7, 0.5, -1.3)
    
    # Right side
    glVertex3f(0.7, 0.0, -1.5)
    glVertex3f(0.7, 0.0, 1.5)
    glVertex3f(0.7, 0.5, 1.2)
    glVertex3f(0.7, 0.5, -1.3)
    
    # Top
    glVertex3f(-0.7, 0.5, -1.3)
    glVertex3f(0.7, 0.5, -1.3)
    glVertex3f(0.7, 0.5, -0.3)
    glVertex3f(-0.7, 0.5, -0.3)
    
    # Windshield
    glColor3f(0.1, 0.1, 0.7)  # Blue tint
    glVertex3f(-0.65, 0.5, 1.0)
    glVertex3f(0.65, 0.5, 1.0)
    glVertex3f(0.65, 1.0, 0.0)
    glVertex3f(-0.65, 1.0, 0.0)
    
    # Roof
    glColor3f(color[0], color[1], color[2])
    glVertex3f(-0.65, 1.0, 0.0)
    glVertex3f(0.65, 1.0, 0.0)
    glVertex3f(0.65, 1.0, -1.0)
    glVertex3f(-0.65, 1.0, -1.0)
    
    # Rear window
    glColor3f(0.1, 0.1, 0.7)  # Blue tint
    glVertex3f(-0.65, 1.0, -1.0)
    glVertex3f(0.65, 1.0, -1.0)
    glVertex3f(0.65, 0.5, -1.3)
    glVertex3f(-0.65, 0.5, -1.3)
    
    glEnd()
    
    # Wheels
    glColor3f(0.1, 0.1, 0.1)  # Black
    
    # Front-left wheel
    glPushMatrix()
    glTranslatef(-0.7, 0.2, 1.0)
    glScalef(0.3, 0.3, 0.5)
    draw_cylinder()
    glPopMatrix()
    
    # Front-right wheel
    glPushMatrix()
    glTranslatef(0.7, 0.2, 1.0)
    glScalef(0.3, 0.3, 0.5)
    draw_cylinder()
    glPopMatrix()
    
    # Rear-left wheel
    glPushMatrix()
    glTranslatef(-0.7, 0.2, -1.0)
    glScalef(0.3, 0.3, 0.5)
    draw_cylinder()
    glPopMatrix()
    
    # Rear-right wheel
    glPushMatrix()
    glTranslatef(0.7, 0.2, -1.0)
    glScalef(0.3, 0.3, 0.5)
    draw_cylinder()
    glPopMatrix()
    
    glPopMatrix()

def draw_cylinder():
    # A very simple cylinder approximation with quads
    glBegin(GL_QUADS)
    
    num_segments = 8
    for i in range(num_segments):
        angle1 = 2 * math.pi * i / num_segments
        angle2 = 2 * math.pi * (i + 1) / num_segments
        
        # Calculate points on the circle
        x1 = math.cos(angle1)
        y1 = math.sin(angle1)
        x2 = math.cos(angle2)
        y2 = math.sin(angle2)
        
        # Side face
        glVertex3f(x1, y1, -0.5)
        glVertex3f(x2, y2, -0.5)
        glVertex3f(x2, y2, 0.5)
        glVertex3f(x1, y1, 0.5)
        
        # End cap 1
        glVertex3f(0, 0, -0.5)
        glVertex3f(x1, y1, -0.5)
        glVertex3f(x2, y2, -0.5)
        
        # End cap 2
        glVertex3f(0, 0, 0.5)
        glVertex3f(x1, y1, 0.5)
        glVertex3f(x2, y2, 0.5)
    
    glEnd()

def draw_mountain(x, y, z, height):
    glPushMatrix()
    glTranslatef(x, y, z)

    # Enable polygon offset to prevent z-fighting
    glEnable(GL_POLYGON_OFFSET_FILL)
    glPolygonOffset(1.0, 1.0)

    # Draw a simple cone for the mountain
    glBegin(GL_TRIANGLE_FAN)
    glVertex3f(0, height, 0)  # Peak

    num_segments = 12
    radius = height * 0.8

    for i in range(num_segments + 1):
        angle = 2 * math.pi * i / num_segments
        glVertex3f(radius * math.cos(angle), 0, radius * math.sin(angle))

    glEnd()

    # Disable polygon offset
    glDisable(GL_POLYGON_OFFSET_FILL)

    glPopMatrix()

def draw_sky():
    glPushMatrix()

    glDisable(GL_LIGHTING)
    
    # Light blue color for the sky
    glColor3f(0.5, 0.7, 1.0)
    
    # Draw a half sphere for the sky
    num_lat = 15
    num_long = 30
    radius = 3000
    glTranslatef(0,0,0)
    
    for i in range(num_lat):
        lat0 = math.pi * (-0.5 + (i - 1) / num_lat)
        z0 = radius * math.sin(lat0)
        zr0 = radius * math.cos(lat0)
        
        lat1 = math.pi * (-0.5 + i / num_lat)
        z1 = radius * math.sin(lat1)
        zr1 = radius * math.cos(lat1)
        
        # Only draw the top half
        if z0 < 0 or z1 < 0:
            continue
        
        glBegin(GL_QUAD_STRIP)
        for j in range(num_long + 1):
            lng = 2 * math.pi * j / num_long
            x = math.cos(lng)
            y = math.sin(lng)
            
            glVertex3f(x * zr0, z0, y * zr0)
            glVertex3f(x * zr1, z1, y * zr1)
        
        glEnd()

    glEnable(GL_LIGHTING)
    
    glPopMatrix()

def draw_text(x, y, text, font, color=(255, 255, 255)):
    """
    Render text at (x, y) using OpenGL.
    """
    # Render the text to a Pygame surface
    text_surface = font.render(text, True, color)
    text_data = pygame.image.tostring(text_surface, "RGBA", True)
    text_width, text_height = text_surface.get_size()

    # Adjust y coordinate because OpenGL's origin is at the bottom left.
    y = HEIGHT - y - text_height

    # Set pixel storage mode
    glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
    
    # Enable blending for transparency
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    
    # Set the raster position for drawing pixels
    glWindowPos2i(x, y)
    
    # Draw the text pixels
    glDrawPixels(text_width, text_height, GL_RGBA, GL_UNSIGNED_BYTE, text_data)
    
    # Optionally, disable blending if not needed elsewhere
    glDisable(GL_BLEND)

def draw_tree(x, y, z, height):  # <---  HERE, in the global scope
    glPushMatrix()
    glTranslatef(x, y, z)

    # Draw trunk (brown cylinder)
    glColor3f(0.5, 0.35, 0.05)  # Brown color
    glPushMatrix()
    glRotatef(-90, 1, 0, 0)  # Rotate to stand upright
    gluCylinder(gluNewQuadric(), 0.2, 0.2, height, 10, 2)
    glPopMatrix()

    # Draw leaves (green cone)
    glColor3f(0.0, 0.8, 0.0)  # Green color
    glTranslatef(0, height, 0)  # Move to top of trunk
    glRotatef(-90, 1, 0, 0)
    gluCylinder(gluNewQuadric(), 0, 1.0, 2.0, 10, 2) #Simplified from a cone

    glPopMatrix()

def render_hud(game_state, player):
    # Switch to orthographic projection for HUD rendering
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    glOrtho(0, WIDTH, 0, HEIGHT, -1, 1)  # Note: (0,0) now at lower left
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    
    # Disable depth testing and lighting so text draws on top
    glDisable(GL_DEPTH_TEST)
    glDisable(GL_LIGHTING)
    
    # Render HUD elements using draw_text
    current_time = time.time() - game_state.start_time if game_state.game_started else 0
    time_str = format_time(current_time)
    draw_text(20, HEIGHT - 40, f"TIME: {time_str}", hud_font)
    draw_text(20, HEIGHT - 70, f"LAP: {game_state.laps + 1}/{game_state.total_laps}", hud_font)
    draw_text(20, HEIGHT - 100, f"POSITION: {game_state.race_position}/8", hud_font)
    
    speed_percent = abs(player.speed / player.max_speed * 100)
    draw_text(WIDTH - 200, HEIGHT - 40, f"SPEED: {int(speed_percent)} MPH", hud_font)
    gear_text = "N" if player.gear == 0 else str(player.gear)
    draw_text(WIDTH - 200, HEIGHT - 70, f"GEAR: {gear_text}", hud_font)
    
    if game_state.best_lap < float('inf'):
        best_lap_str = format_time(game_state.best_lap)
        draw_text(WIDTH - 200, HEIGHT - 100, f"BEST LAP: {best_lap_str}", hud_font)
    
    if game_state.countdown_active:
        count_text = str(game_state.countdown_value) if game_state.countdown_value > 0 else "GO!"
        # Center the countdown text (roughly)
        count_surface = countdown_font.render(count_text, True, (255, 255, 0))
        text_width, text_height = count_surface.get_size()
        center_x = (WIDTH - text_width) // 2
        center_y = (HEIGHT - text_height) // 2
        draw_text(center_x, center_y, count_text, countdown_font, (255, 255, 0))
    
    if game_state.game_over:
        go_text = "RACE COMPLETE!"
        center_x = (WIDTH - game_over_font.size(go_text)[0]) // 2
        draw_text(center_x, HEIGHT - 200, go_text, game_over_font, (255, 255, 0))
        draw_text((WIDTH - 200) // 2, HEIGHT - 250, f"Total Time: {format_time(game_state.total_time)}", hud_font)
        draw_text((WIDTH - 200) // 2, HEIGHT - 280, f"Final Position: {get_ordinal(game_state.race_position)}", hud_font)
        if game_state.best_lap < float('inf'):
            draw_text((WIDTH - 200) // 2, HEIGHT - 310, f"Best Lap: {format_time(game_state.best_lap)}", hud_font)
        draw_text((WIDTH - 200) // 2, HEIGHT - 340, "Press ENTER to restart", hud_font)
    
    # Restore OpenGL state
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    glPopMatrix()

def format_time(seconds):
    minutes = int(seconds // 60)
    seconds = seconds % 60
    return f"{minutes:02d}:{seconds:06.3f}"

def get_ordinal(n):
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"

def check_collision(obj1, obj2):
    dx = obj1.position[0] - obj2.position[0]
    dz = obj1.position[2] - obj2.position[2]
    distance = math.sqrt(dx*dx + dz*dz)
    return distance < (obj1.collision_radius + obj2.collision_radius)

def start_countdown(game_state):
    game_state.countdown_active = True
    game_state.countdown_value = 3
    pygame.time.set_timer(pygame.USEREVENT, 1000)  # 1 second timer

def end_race(game_state):
    game_state.game_over = True
    game_state.total_time = time.time() - game_state.start_time
    pygame.time.set_timer(pygame.USEREVENT, 0)  # Disable the timer

def reset_game(game_state, player, ai_cars, track):
    # Reset player
    player.position = [0, 0.5, 0]
    player.rotation = 0
    player.speed = 0
    player.gear = 0
    
    # Reset AI cars
    for i, car in enumerate(ai_cars):
        start_offset = 5 + i * 2
        car.position = [random.uniform(-3, 3), 0.5, -start_offset]
        car.rotation = 0
        car.speed = random.uniform(0.2, 0.6)
        car.laps = 0
    
    # Reset track checkpoints
    track.last_checkpoint = {}
    track.tree_positions = []  # Clear existing tree positions
    track.generate_trees()     # Re-generate tree positions
    
    # Reset game state
    game_state.game_started = False
    game_state.game_over = False
    game_state.countdown_active = False
    game_state.laps = 0
    game_state.race_position = 1
    game_state.total_time = 0
    game_state.lap_times = []
    
    # Start new countdown
    start_countdown(game_state)

def main():
    global WIDTH, HEIGHT 
    original_flags = DOUBLEBUF | OPENGL | RESIZABLE

    WIDTH, HEIGHT = 1024, 768

    # Initialize game components
    game_state = GameState()
    player = PlayerCar()
    track = Track()

    # Set up proper lighting
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    
    # Set light properties for better outdoor lighting
    ambient_light = [0.4, 0.4, 0.4, 1.0]  # Brighter ambient light
    diffuse_light = [0.8, 0.8, 0.8, 1.0]  # Strong diffuse light
    
    glLightfv(GL_LIGHT0, GL_AMBIENT, ambient_light)
    glLightfv(GL_LIGHT0, GL_DIFFUSE, diffuse_light)
    
    # Material settings
    glEnable(GL_COLOR_MATERIAL)
    glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
    
    # Set clear color to match sky color
    glClearColor(0.5, 0.7, 1.0, 1.0)
    
    # Create AI cars
    ai_cars = []
    car_colors = [
        (1.0, 0.0, 0.0),  # Red
        (0.0, 1.0, 0.0),  # Green
        (0.0, 0.0, 1.0),  # Blue
        (1.0, 1.0, 0.0),  # Yellow
        (1.0, 0.0, 1.0),  # Magenta
        (0.0, 1.0, 1.0),  # Cyan
        (1.0, 0.5, 0.0)   # Orange
    ]
    
    for i in range(7):
        start_offset = 5 + i * 2
        ai_cars.append(AICar([random.uniform(-3, 3), 0.5, -start_offset], car_colors[i]))
    
    # Start countdown
    start_countdown(game_state)
    
    # Main game loop
    clock = pygame.time.Clock()
    running = True
    last_time = time.time()
    lap_start_time = 0

    # Variables to track button press state
    shift_pressed = False
    ctrl_pressed = False
    fullscreen = False
    
    while running:
        glViewport(0, 0, WIDTH, HEIGHT)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        # Calculate delta time
        current_time = time.time()
        dt = current_time - last_time
        last_time = current_time
        
        # Button Press Process events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            # --- Event Handling ---
            if event.type == pygame.KEYDOWN:
                if event.key == K_RETURN and (game_state.game_over or not game_state.game_started):
                    reset_game(game_state, player, ai_cars, track)
                if event.key == K_f: # Check for 'F' key press
                    fullscreen = not fullscreen  # Toggle fullscreen state
                    if fullscreen:
                        new_width, new_height = 1920, 1080
                        screen = pygame.display.set_mode((new_width, new_height), original_flags | FULLSCREEN)
                        resize_viewport(new_width, new_height)  # Resize the viewport
                        WIDTH, HEIGHT = new_width, new_height  # update globals
                    else:
                        screen = pygame.display.set_mode((1024, 768), original_flags)
                        resize_viewport(1024, 768)
                        WIDTH, HEIGHT = 1024, 768

            
            if event.type == pygame.VIDEORESIZE:  # Handle window resizing (if not fullscreen)
                if not fullscreen:  # Only resize if NOT in fullscreen
                    new_width, new_height = event.size
                    screen = pygame.display.set_mode((new_width, new_height), original_flags | RESIZABLE)
                    resize_viewport(new_width, new_height)
            if event.type == pygame.USEREVENT:  # 1-second timer for countdown
                if game_state.countdown_value > 0:
                    game_state.countdown_value -= 1
                else:
                    game_state.countdown_active = False
                    game_state.game_started = True
                    game_state.start_time = time.time()
                    lap_start_time = time.time()
                    pygame.time.set_timer(pygame.USEREVENT, 0)  # Disable the timer
        
        # Get keyboard input
        keys = pygame.key.get_pressed()
        
        # Game logic
        if game_state.game_started and not game_state.game_over:
            # Acceleration
            if keys[K_UP] or keys[K_w]:
                if player.gear > 0:
                    player.acceleration = 0.01 * player.gear
                else:
                    player.acceleration = 0
            elif keys[K_DOWN] or keys[K_s]:
                player.acceleration = -0.02
            else:
                player.acceleration = -0.005
            
            # Apply acceleration
            player.speed += player.acceleration
            
            # Apply gear limits
            gear_max_speed = (player.gear / player.max_gear) * player.max_speed
            player.speed = max(-0.3, min(player.speed, gear_max_speed))
            
            # Braking
            if keys[K_SPACE]:
                player.speed *= 0.95
            
            # Gear shifting (using button press/release logic)
            if keys[K_LSHIFT] and not shift_pressed:  # Key pressed and not already pressed
                shift_pressed = True  # Mark key as pressed
                if player.gear < player.max_gear and (player.gear == 0 or player.speed >= player.gear * 0.1):
                    player.gear = min(player.gear + 1, player.max_gear)
            elif not keys[K_LSHIFT]:  # Key released
                shift_pressed = False  # Mark key as released
                
            if keys[K_LCTRL] and not ctrl_pressed: # Key pressed and not already pressed
                ctrl_pressed = True # Mark key as pressed
                if player.gear > 0:
                   player.gear = max(player.gear - 1, 0)
            elif not keys[K_LCTRL]:  # Key released
                ctrl_pressed = False # Mark Key as released
            
            # Steering
            if keys[K_LEFT] or keys[K_a]:
                player.rotation += player.steering_speed * (1 - abs(player.speed / player.max_speed) * 0.5)
            if keys[K_RIGHT] or keys[K_d]:
                player.rotation -= player.steering_speed * (1 - abs(player.speed / player.max_speed) * 0.5)
            
            # Movement
            player.position[0] += math.sin(math.radians(player.rotation)) * player.speed
            player.position[2] += math.cos(math.radians(player.rotation)) * player.speed
            
            # Update AI cars
            for car in ai_cars:
                car.update(track, dt)
            
            # Check for collisions between player and AI cars
            for car in ai_cars:
                if check_collision(player, car):
                    # Slow down both cars
                    player.speed *= 0.5
                    car.speed *= 0.5
                    
                    # Calculate push direction
                    dx = player.position[0] - car.position[0]
                    dz = player.position[2] - car.position[2]
                    dist = math.sqrt(dx*dx + dz*dz)
                    
                    if dist > 0:
                        # Normalize
                        dx /= dist
                        dz /= dist
                        
                        # Push cars apart
                        push_force = 0.2
                        player.position[0] += dx * push_force
                        player.position[2] += dz * push_force
                        car.position[0] -= dx * push_force
                        car.position[2] -= dz * push_force
            
            # Keep player on the track (simple boundary check)
            nearest_point, nearest_idx = track.get_nearest_point(player.position)
            left_bound, right_bound = track.get_road_boundaries(nearest_idx)
            
            # Calculate distance to track center
            center_x = (left_bound[0] + right_bound[0]) / 2
            center_z = (left_bound[2] + right_bound[2]) / 2
            dist_to_center = math.sqrt((player.position[0] - center_x)**2 + (player.position[2] - center_z)**2)
            
            # If player is too far from center, slow them down (off-track penalty)
            if dist_to_center > track.width / 2:
                player.speed *= 0.95
            
            # Check for lap completion
            if nearest_idx < 5 and player.position[2] > 0 and abs(player.position[0]) < 5:
                last_checkpoint = track.last_checkpoint.get(player, 0)
                if last_checkpoint > len(track.points) / 2:
                    # Completed a lap
                    current_lap_time = time.time() - lap_start_time
                    game_state.lap_times.append(current_lap_time)
                    
                    if current_lap_time < game_state.best_lap:
                        game_state.best_lap = current_lap_time
                    
                    game_state.laps += 1
                    lap_start_time = time.time()
                    
                    if game_state.laps >= game_state.total_laps:
                        end_race(game_state)
            
            # Update checkpoint tracking
            if nearest_idx > track.last_checkpoint.get(player, 0):
                track.last_checkpoint[player] = nearest_idx
            
            # Update race position
            all_cars = [player] + ai_cars
            sorted_cars = sorted(all_cars, key=lambda car: car.laps * len(track.points) + track.last_checkpoint.get(car, 0), reverse=True)
            game_state.race_position = sorted_cars.index(player) + 1
        
        # Clear the screen
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        # Set up camera
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        
        # Third-person camera view
        camera_distance = 5
        camera_height = 2
        
        # Calculate camera position
        camera_x = player.position[0] - camera_distance * math.sin(math.radians(player.rotation))
        camera_y = player.position[1] + camera_height
        camera_z = player.position[2] - camera_distance * math.cos(math.radians(player.rotation))
        
        # Look at player car
        gluLookAt(
            camera_x, camera_y, camera_z,          # Camera position
            player.position[0], player.position[1], player.position[2],  # Look at point
            0, 1, 0                                 # Up vector
        )
        
        # --- DRAW SKY FIRST ---
        glDisable(GL_DEPTH_TEST)  # Temporarily disable depth testing
        glDisable(GL_LIGHTING)   # Disable lighting for the sky
        draw_sky()
        glEnable(GL_DEPTH_TEST)  # Re-enable depth testing
        glEnable(GL_LIGHTING)    # Re-enable lighting

        # Set up lighting (AFTER drawing the sky)
        light_position = [0, 100, 0, 1]
        glLightfv(GL_LIGHT0, GL_POSITION, light_position)
        
        # Render the track
        track.render()
        
        # Render the player car
        draw_car(player.position[0], player.position[1], player.position[2], player.rotation, (0.9, 0.1, 0.1))
        
        # Render the AI cars
        for car in ai_cars:
            draw_car(car.position[0], car.position[1], car.position[2], car.rotation, car.color)
        
        # Update the screen
        screen = pygame.display.get_surface()
        render_hud(game_state, player)
        pygame.display.flip()
        
        # Cap the frame rate
        clock.tick(60)
    
    # Quit pygame
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
