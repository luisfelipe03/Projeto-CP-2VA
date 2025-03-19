import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import numpy as np
import random
from PIL import Image

# Tamanho do labirinto
MAZE_SIZE = 10

# Algoritmo para gerar o labirinto (DFS recursivo)
def generate_maze(size):
    maze = np.ones((size, size), dtype=int)
    stack = [(1, 1)]
    maze[1, 1] = 0

    while stack:
        x, y = stack[-1]
        neighbors = [(x + dx, y + dy) for dx, dy in [(0, 2), (0, -2), (2, 0), (-2, 0)]]
        neighbors = [(nx, ny) for nx, ny in neighbors if 0 < nx < size - 1 and 0 < ny < size - 1 and maze[nx, ny] == 1]

        if neighbors:
            nx, ny = random.choice(neighbors)
            maze[(x + nx) // 2, (y + ny) // 2] = 0
            maze[nx, ny] = 0
            stack.append((nx, ny))
        else:
            stack.pop()

    return maze

# Carregar textura
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

# Configuração do OpenGL
def setup_opengl():
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_TEXTURE_2D)
    glMatrixMode(GL_PROJECTION)
    gluPerspective(60, (800 / 600), 0.1, 50.0)
    glMatrixMode(GL_MODELVIEW)

# Renderiza as paredes do labirinto com textura
def draw_maze(maze, wall_texture):
    glBindTexture(GL_TEXTURE_2D, wall_texture)
    for x in range(len(maze)):
        for y in range(len(maze[x])):
            if maze[x][y] == 1:
                draw_textured_cube(x, 0, y)

# Desenha o chão com textura
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

# Desenha um cubo com textura para as paredes
def draw_textured_cube(x, y, z):
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

# Classe para controlar a câmera com colisão
class Camera:
    def __init__(self, maze):
        self.x, self.y, self.z = 1.5, 0.5, 1.5
        self.angle_yaw = 0
        self.maze = maze

    def can_move(self, new_x, new_z):
        maze_x, maze_z = int(new_x), int(new_z)
        return 0 <= maze_x < len(self.maze) and 0 <= maze_z < len(self.maze[0]) and self.maze[maze_x][maze_z] == 0

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

# Desenha o mini-mapa
def draw_minimap(maze, player_x, player_z, portal_x, portal_z):
    minimap_size = 100
    pygame.draw.rect(screen, (255, 255, 255), (10, 10, minimap_size, minimap_size))

    scale = minimap_size / MAZE_SIZE
    for x in range(len(maze)):
        for z in range(len(maze[0])):
            color = (0, 0, 0) if maze[x][z] == 1 else (200, 200, 200)
            pygame.draw.rect(screen, color, (10 + x * scale, 10 + z * scale, scale, scale))

    pygame.draw.circle(screen, (0, 0, 255), (int(10 + player_x * scale), int(10 + player_z * scale)), 5)
    pygame.draw.circle(screen, (255, 0, 0), (int(10 + portal_x * scale), int(10 + portal_z * scale)), 5)

# Loop principal do jogo
def main():
    global screen
    pygame.init()
    screen = pygame.display.set_mode((800, 600), DOUBLEBUF | OPENGL)
    pygame.mouse.set_visible(False)
    pygame.event.set_grab(True)
    clock = pygame.time.Clock()

    pygame.mixer.init()
    step_sound = pygame.mixer.Sound("step.wav")
    win_sound = pygame.mixer.Sound("win.wav")

    setup_opengl()
    maze = generate_maze(MAZE_SIZE)
    camera = Camera(maze)

    floor_texture = load_texture("chao.jpg")
    wall_texture = load_texture("parede.jpg")

    portal_x, portal_z = MAZE_SIZE - 2, MAZE_SIZE - 2

    running = True
    last_step_time = 0
    mouse_sensitivity = 0.1  # Sensibilidade do mouse

    while running:
        current_time = pygame.time.get_ticks()
        for event in pygame.event.get():
            if event.type == QUIT or pygame.key.get_pressed()[K_ESCAPE]:
                running = False

            # Captura o movimento do mouse
            if event.type == pygame.MOUSEMOTION:
                x, y = event.rel
                camera.rotate(x * mouse_sensitivity)  # Ajusta o ângulo da câmera

        keys = pygame.key.get_pressed()
        speed = 0.1

        if keys[K_w]:
            camera.move(speed * np.cos(np.radians(camera.angle_yaw)), speed * np.sin(np.radians(camera.angle_yaw)))
        if keys[K_s]:
            camera.move(-speed * np.cos(np.radians(camera.angle_yaw)), -speed * np.sin(np.radians(camera.angle_yaw)))
        if keys[K_a]:
            camera.move(speed * np.sin(np.radians(camera.angle_yaw)), -speed * np.cos(np.radians(camera.angle_yaw)))
        if keys[K_d]:
            camera.move(-speed * np.sin(np.radians(camera.angle_yaw)), speed * np.cos(np.radians(camera.angle_yaw)))

        if keys[K_w] or keys[K_s] or keys[K_a] or keys[K_d]:
            if current_time - last_step_time > 500:  # Toca o som a cada 500ms
                step_sound.play()
                last_step_time = current_time

        if int(camera.x) == portal_x and int(camera.z) == portal_z:
            win_sound.play()
            print("🏆 Você venceu! 🏆")
            running = False

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        camera.apply()
        draw_floor(floor_texture)
        draw_maze(maze, wall_texture)
        draw_minimap(maze, camera.x, camera.z, portal_x, portal_z)

        pygame.display.flip()
        clock.tick(60)

        # Centraliza o mouse na tela
        pygame.mouse.set_pos((400, 300))

    pygame.quit()

if __name__ == "__main__":
    main()