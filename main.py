import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import numpy as np
import random
from PIL import Image

# Constantes
MAZE_SIZE = 5
PLAYER_RADIUS = 0.2
SCREEN_WIDTH = 1080
SCREEN_HEIGHT = 720
MOUSE_SENSITIVITY = 0.12
PLAYER_SPEED = 0.13

class Maze:
    def __init__(self, size):
        self.size = size
        self.grid = self.generate_maze()
        self.portal_pos = self.find_valid_portal_position()  # Encontra uma posição válida para o portal

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

    def find_valid_portal_position(self):
        """Encontra uma posição válida para o portal (onde não há parede)."""
        for x in range(self.size - 1, 0, -1):
            for z in range(self.size - 1, 0, -1):
                if self.grid[x][z] == 0:  # Verifica se é um caminho válido
                    return (x, z)
        return (1, 1)  # Fallback: posição inicial

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

    def draw_portal(self, portal_texture):
        x, z = self.portal_pos
        glBindTexture(GL_TEXTURE_2D, portal_texture)
        glBegin(GL_QUADS)
        glTexCoord2f(0, 0)
        glVertex3f(x, 0, z)
        glTexCoord2f(1, 0)
        glVertex3f(x + 1, 0, z)
        glTexCoord2f(1, 1)
        glVertex3f(x + 1, 1, z)
        glTexCoord2f(0, 1)
        glVertex3f(x, 1, z)
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

    def check_portal_collision(self, portal_pos):
        portal_x, portal_z = portal_pos
        distance = np.sqrt((self.x - portal_x) ** 2 + (self.z - portal_z) ** 2)
        return distance < 0.5  # Colisão se estiver próximo o suficiente

def load_texture(filename):
    img = Image.open(filename).convert("RGBA")  # Usa RGBA para garantir canal alpha
    img = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)  # Corrige a inversão

    img_data = np.array(img, dtype=np.uint8)  # Converte para array numpy

    texture_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, texture_id)

    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)  # Evita distorções
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)

    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, img.width, img.height, 0, GL_RGBA, GL_UNSIGNED_BYTE, img_data)

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

def show_menu():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    font = pygame.font.Font(None, 74)
    title_text = font.render("Labirinto Mágico", True, (255, 255, 255))
    start_text = pygame.font.Font(None, 50).render("Pressione ESPAÇO para começar", True, (255, 255, 255))

    while True:
        screen.fill((0, 0, 0))
        screen.blit(title_text, (SCREEN_WIDTH // 2 - 200, SCREEN_HEIGHT // 2 - 100))
        screen.blit(start_text, (SCREEN_WIDTH // 2 - 250, SCREEN_HEIGHT // 2 + 50))
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                exit()  # Fecha o jogo corretamente
            if event.type == KEYDOWN and event.key == K_SPACE:
                return  # Sai do menu e começa o jogo


def show_win_screen():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    font = pygame.font.Font(None, 74)
    win_text = font.render("Você encontrou o portal! Parabéns!", True, (255, 255, 255))
    restart_text = pygame.font.Font(None, 50).render("Pressione R para reiniciar ou ESC para sair", True, (255, 255, 255))

    while True:
        screen.fill((0, 0, 0))
        screen.blit(win_text, (SCREEN_WIDTH // 2 - 300, SCREEN_HEIGHT // 2 - 50))
        screen.blit(restart_text, (SCREEN_WIDTH // 2 - 300, SCREEN_HEIGHT // 2 + 50))
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                exit()
            if event.type == KEYDOWN:
                if event.key == K_r:
                    return True  # Indica que o jogo deve reiniciar
                if event.key == K_ESCAPE:
                    return False  # Indica que o jogo deve fechar



def main():
    pygame.init()

    show_menu()  # Mostra o menu antes de iniciar

    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), DOUBLEBUF | OPENGL)
    pygame.mouse.set_visible(False)
    pygame.event.set_grab(True)
    clock = pygame.time.Clock()

    pygame.mixer.init()
    step_sound = pygame.mixer.Sound("step.wav")
    portal_sound = pygame.mixer.Sound("win.wav")

    setup_opengl()
    maze = Maze(MAZE_SIZE)
    camera = Camera(maze)

    floor_texture = load_texture("chao.jpg")
    wall_texture = load_texture("parede.jpg")
    portal_texture = load_texture("portal.jpg")

    running = True
    while running:
        running = handle_events(camera)

        keys = pygame.key.get_pressed()
        if keys[K_w]:
            camera.move(PLAYER_SPEED * np.cos(np.radians(camera.angle_yaw)),
                        PLAYER_SPEED * np.sin(np.radians(camera.angle_yaw)))
            step_sound.play()
        if keys[K_s]:
            camera.move(-PLAYER_SPEED * np.cos(np.radians(camera.angle_yaw)),
                        -PLAYER_SPEED * np.sin(np.radians(camera.angle_yaw)))
            step_sound.play()
        if keys[K_a]:
            camera.move(PLAYER_SPEED * np.sin(np.radians(camera.angle_yaw)),
                        -PLAYER_SPEED * np.cos(np.radians(camera.angle_yaw)))
            step_sound.play()
        if keys[K_d]:
            camera.move(-PLAYER_SPEED * np.sin(np.radians(camera.angle_yaw)),
                        PLAYER_SPEED * np.cos(np.radians(camera.angle_yaw)))
            step_sound.play()

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        camera.apply()
        draw_floor(floor_texture)
        maze.draw(wall_texture)
        maze.draw_portal(portal_texture)

        # Verifica colisão com o portal
        if camera.check_portal_collision(maze.portal_pos):
            portal_sound.play()
            if show_win_screen():  # Agora retorna True se o jogador quiser reiniciar
                return main()  # Reinicia o jogo
            else:
                running = False  # Sai do jogo

        pygame.display.flip()
        clock.tick(60)
        pygame.mouse.set_pos((SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))

    pygame.quit()


if __name__ == "__main__":
    main()