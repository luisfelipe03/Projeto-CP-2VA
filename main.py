import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import numpy as np
import random
from PIL import Image

# Constantes
MAZE_SIZE = 14
PLAYER_RADIUS = 0.2
SCREEN_WIDTH = 1080
SCREEN_HEIGHT = 720
MOUSE_SENSITIVITY = 0.12
PLAYER_SPEED = 0.13

class Maze:
    def __init__(self, size):
        self.size = size
        self.grid = self.generate_maze()

    def generate_maze(self):
        maze = np.ones((self.size, self.size), dtype=int)
        stack = [(1, 1)]
        maze[1, 1] = 0

        while stack:
            x, y = stack[-1]
            neighbors = [(x + dx, y + dy) for dx, dy in [(0, 2), (0, -2), (2, 0), (-2, 0)]]
            neighbors = [(nx, ny) for nx, ny in neighbors if 0 < nx < self.size - 1 and 0 < ny < self.size - 1 and maze[nx, ny] == 1]

            if neighbors:
                nx, ny = random.choice(neighbors)
                maze[(x + nx) // 2, (y + ny) // 2] = 0
                maze[nx, ny] = 0
                stack.append((nx, ny))
            else:
                stack.pop()

        return maze

    def draw(self, wall_texture):
        glBindTexture(GL_TEXTURE_2D, wall_texture)
        for x in range(self.size):
            for y in range(self.size):
                if self.grid[x][y] == 1:
                    self.draw_textured_cube(x, 0, y)

    def draw_textured_cube(self, x, y, z):
        size = 1
        vertices = [
            (x, y, z), (x + size, y, z), (x + size, y, z + size), (x, y, z + size),
            (x, y + size, z), (x + size, y + size, z), (x + size, y + size, z + size), (x, y + size, z + size)
        ]

        faces = [
            (0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4),
            (2, 3, 7, 6), (0, 3, 7, 4), (1, 2, 6, 5)
        ]

        tex_coords = [(0, 0), (1, 0), (1, 1), (0, 1)]

        glBegin(GL_QUADS)
        for face in faces:
            for i, vertex in enumerate(face):
                glTexCoord2fv(tex_coords[i % 4])
                glVertex3fv(vertices[vertex])
        glEnd()

class Camera:
    def __init__(self, maze):
        self.x, self.y, self.z = 1.5, 0.5, 1.5
        self.angle_yaw = 0
        self.maze = maze

    def can_move(self, new_x, new_z):
        maze_x, maze_z = int(new_x), int(new_z)
        if 0 <= maze_x < len(self.maze.grid) and 0 <= maze_z < len(self.maze.grid[0]) and self.maze.grid[maze_x][maze_z] == 0:
            for dx in [-PLAYER_RADIUS, PLAYER_RADIUS]:
                for dz in [-PLAYER_RADIUS, PLAYER_RADIUS]:
                    check_x, check_z = new_x + dx, new_z + dz
                    if self.maze.grid[int(check_x)][int(check_z)] == 1:
                        return False
            return True
        return False

    def move(self, dx, dz):
        new_x, new_z = self.x + dx, self.z + dz
        if self.can_move(new_x, self.z):
            self.x = new_x
        if self.can_move(self.x, new_z):
            self.z = new_z

    def rotate(self, angle):
        self.angle_yaw += angle

    def apply(self):
        glLoadIdentity()
        gluLookAt(self.x, self.y, self.z,
                  self.x + np.cos(np.radians(self.angle_yaw)), self.y, self.z + np.sin(np.radians(self.angle_yaw)),
                  0, 1, 0)

def load_texture(filename):
    img = Image.open(filename)
    img = img.transpose(Image.FLIP_TOP_BOTTOM)
    img_data = np.array(img.convert("RGB"), dtype=np.uint8)
    texture_id = glGenTextures(1)

    glBindTexture(GL_TEXTURE_2D, texture_id)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, img.width, img.height, 0, GL_RGB, GL_UNSIGNED_BYTE, img_data)

    return texture_id

def setup_opengl():
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_TEXTURE_2D)
    glMatrixMode(GL_PROJECTION)
    gluPerspective(60, (SCREEN_WIDTH / SCREEN_HEIGHT), 0.1, 50.0)
    glMatrixMode(GL_MODELVIEW)

def draw_floor(floor_texture):
    size = MAZE_SIZE
    glBindTexture(GL_TEXTURE_2D, floor_texture)
    glBegin(GL_QUADS)
    glTexCoord2f(0, 0)
    glVertex3f(0, 0, 0)
    glTexCoord2f(1, 0)
    glVertex3f(size, 0, 0)
    glTexCoord2f(1, 1)
    glVertex3f(size, 0, size)
    glTexCoord2f(0, 1)
    glVertex3f(0, 0, size)
    glEnd()

def handle_events(camera):
    for event in pygame.event.get():
        if event.type == QUIT or pygame.key.get_pressed()[K_ESCAPE]:
            return False
        if event.type == pygame.MOUSEMOTION:
            x, y = event.rel
            camera.rotate(x * MOUSE_SENSITIVITY)
    return True

def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), DOUBLEBUF | OPENGL)
    pygame.mouse.set_visible(False)
    pygame.event.set_grab(True)
    clock = pygame.time.Clock()

    setup_opengl()
    maze = Maze(MAZE_SIZE)
    camera = Camera(maze)

    floor_texture = load_texture("chao.jpg")
    wall_texture = load_texture("parede.jpg")

    running = True
    while running:
        running = handle_events(camera)

        keys = pygame.key.get_pressed()
        if keys[K_w]:
            camera.move(PLAYER_SPEED * np.cos(np.radians(camera.angle_yaw)), PLAYER_SPEED * np.sin(np.radians(camera.angle_yaw)))
        if keys[K_s]:
            camera.move(-PLAYER_SPEED * np.cos(np.radians(camera.angle_yaw)), -PLAYER_SPEED * np.sin(np.radians(camera.angle_yaw)))
        if keys[K_a]:
            camera.move(PLAYER_SPEED * np.sin(np.radians(camera.angle_yaw)), -PLAYER_SPEED * np.cos(np.radians(camera.angle_yaw)))
        if keys[K_d]:
            camera.move(-PLAYER_SPEED * np.sin(np.radians(camera.angle_yaw)), PLAYER_SPEED * np.cos(np.radians(camera.angle_yaw)))

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        camera.apply()
        draw_floor(floor_texture)
        maze.draw(wall_texture)

        pygame.display.flip()
        clock.tick(60)
        pygame.mouse.set_pos((SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))

    pygame.quit()

if __name__ == "__main__":
    main()