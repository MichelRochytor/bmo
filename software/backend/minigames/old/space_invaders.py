import pygame
import sys
import random
import pickle
import os
import ranking

# Inicializa o Pygame
pygame.init()

# Cores (Paleta BMO)
BMO_BG = (156, 206, 168)
BMO_PLAYER = (45, 90, 50)
BMO_ENEMY = (200, 50, 50)
BMO_TEXT = (20, 40, 20)
BMO_OVERLAY = (156, 206, 168)
BMO_BULLET = (20, 40, 20)
BMO_POWERUP_DOUBLE = (50, 100, 200)
BMO_POWERUP_RAPID = (200, 150, 50)
BMO_POWERUP_LIFE = (200, 100, 150)

# Configurações de Tela
import config
WIDTH, HEIGHT = config.LARGURA, config.ALTURA
FPS = 60



screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN | pygame.SCALED)
pygame.display.set_caption("BMO - Space Invaders Fluido")
clock = pygame.time.Clock()
font = pygame.font.SysFont("Courier", 24, bold=True)
font_small = pygame.font.SysFont("Courier", 16, bold=True)
font_large = pygame.font.SysFont("Courier", 32, bold=True)

class Player:
    def __init__(self):
        self.width = 40
        self.height = 40
        self.x = WIDTH // 2
        self.y = HEIGHT - 60
        self.speed = 6
        self.rect = pygame.Rect(self.x - self.width//2, self.y - self.height//2, self.width, self.height)
        
        self.lives = 3
        self.invulnerable = 0
        
        self.cooldown = 0
        self.cooldown_max = 15
        self.double_shot = False

    def move(self, dir):
        self.x += dir * self.speed
        if self.x < self.width//2: self.x = self.width//2
        if self.x > WIDTH - self.width//2: self.x = WIDTH - self.width//2
        self.rect.centerx = int(self.x)

    def update(self):
        if self.cooldown > 0:
            self.cooldown -= 1
        if self.invulnerable > 0:
            self.invulnerable -= 1

    def draw(self, surface):
        # Piscar se estiver invulnerável
        if self.invulnerable > 0 and (self.invulnerable // 5) % 2 == 0:
            return
            
        pygame.draw.rect(surface, BMO_PLAYER, self.rect)
        # Detalhe do canhão
        if self.double_shot:
            pygame.draw.rect(surface, BMO_PLAYER, (self.rect.left + 5, self.rect.top - 10, 8, 10))
            pygame.draw.rect(surface, BMO_PLAYER, (self.rect.right - 13, self.rect.top - 10, 8, 10))
        else:
            pygame.draw.rect(surface, BMO_PLAYER, (self.rect.centerx - 5, self.rect.top - 10, 10, 10))

class Bullet:
    def __init__(self, x, y, is_player=True):
        self.rect = pygame.Rect(x - 4, y - 10, 8, 20)
        self.speed = -10 if is_player else 5
        self.active = True

    def update(self):
        self.rect.y += self.speed
        if self.rect.bottom < 0 or self.rect.top > HEIGHT:
            self.active = False

    def draw(self, surface):
        pygame.draw.rect(surface, BMO_BULLET, self.rect)

class Enemy:
    def __init__(self):
        self.width = 40
        self.height = 40
        self.x = random.randint(self.width//2, WIDTH - self.width//2)
        self.y = -50
        self.rect = pygame.Rect(self.x - self.width//2, self.y - self.height//2, self.width, self.height)
        self.speed = random.randint(2, 5)
        self.active = True

    def update(self):
        self.rect.y += self.speed
        if self.rect.top > HEIGHT:
            self.active = False
            return True # Passou direto
        return False

    def draw(self, surface):
        pygame.draw.rect(surface, BMO_ENEMY, self.rect)
        
class PowerUp:
    def __init__(self, x, y):
        self.radius = 12
        self.x = x
        self.y = y
        self.rect = pygame.Rect(x - self.radius, y - self.radius, self.radius*2, self.radius*2)
        self.speed = 3
        self.active = True
        
        # Tipos: 0 = Double Shot, 1 = Rapid Fire, 2 = Extra Life
        rand = random.random()
        if rand < 0.4:
            self.type = 0
            self.color = BMO_POWERUP_DOUBLE
            self.label = "D"
        elif rand < 0.8:
            self.type = 1
            self.color = BMO_POWERUP_RAPID
            self.label = "R"
        else:
            self.type = 2
            self.color = BMO_POWERUP_LIFE
            self.label = "+1"

    def update(self):
        self.y += self.speed
        self.rect.centery = int(self.y)
        if self.rect.top > HEIGHT:
            self.active = False

    def draw(self, surface):
        pygame.draw.circle(surface, self.color, self.rect.center, self.radius)
        text = font_small.render(self.label, True, (255,255,255))
        surface.blit(text, (self.rect.centerx - text.get_width()//2, self.rect.centery - text.get_height()//2))

class Mothership:
    def __init__(self):
        self.width = 150
        self.height = 60
        self.x = WIDTH // 2
        self.y = 80
        self.rect = pygame.Rect(self.x - self.width//2, self.y - self.height//2, self.width, self.height)
        self.hp = 10
        self.speed = 3
        self.direction = 1
        self.active = True
        self.shoot_cooldown = 60

    def update(self):
        self.rect.x += self.speed * self.direction
        if self.rect.right > WIDTH - 20 or self.rect.left < 20:
            self.direction *= -1

    def draw(self, surface):
        pygame.draw.rect(surface, BMO_ENEMY, self.rect)
        pygame.draw.rect(surface, BMO_BG, self.rect, 4)
        
        hp_width = int((self.hp / 10.0) * self.width)
        if hp_width > 0:
            hp_rect = pygame.Rect(self.rect.left, self.rect.top - 15, hp_width, 5)
            pygame.draw.rect(surface, BMO_ENEMY, hp_rect)

def main():
    joysticks = config.init_joystick()
    player = Player()
    bullets = []
    enemies = []
    powerups = []
    mothership = None
    
    score = 0
    kills = 0
    boss_kills = 0
    game_over = False
    
    enemy_spawn_timer = 0
    enemy_spawn_rate = 60

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
            if event.type == pygame.JOYBUTTONDOWN:
                if event.button in (6, 7): # START/SELECT
                    pygame.quit()
                    sys.exit()

        keys = pygame.key.get_pressed()
        joy_state = config.get_joystick_state(joysticks)
        if not game_over:
            if keys[pygame.K_LEFT] or keys[pygame.K_a] or joy_state['left']:
                player.move(-1)
            if keys[pygame.K_RIGHT] or keys[pygame.K_d] or joy_state['right']:
                player.move(1)
                
            if (keys[pygame.K_SPACE] or joy_state['action'] or joy_state['action2']) and player.cooldown == 0:
                if player.double_shot:
                    bullets.append(Bullet(player.rect.left + 8, player.rect.top))
                    bullets.append(Bullet(player.rect.right - 8, player.rect.top))
                else:
                    bullets.append(Bullet(player.rect.centerx, player.rect.top))
                player.cooldown = player.cooldown_max
            
            player.update()
            
            for b in bullets: b.update()
            bullets = [b for b in bullets if b.active]
            
            # Colisão de balas inimigas com o player
            for b in bullets:
                if b.active and b.speed > 0 and b.rect.colliderect(player.rect):
                    b.active = False
                    if player.invulnerable == 0:
                        player.lives -= 1
                        player.invulnerable = 60
                        player.double_shot = False
                        player.cooldown_max = 15
                        if player.lives <= 0:
                            game_over = True
                            
            for p in powerups: p.update()
            
            # Coleta de powerups
            for p in powerups:
                if p.active and p.rect.colliderect(player.rect):
                    p.active = False
                    if p.type == 0:
                        player.double_shot = True
                    elif p.type == 1:
                        player.cooldown_max = 7
                    elif p.type == 2:
                        if player.lives < 5: # Limite de 5 vidas para nao ficar infinito
                            player.lives += 1
            powerups = [p for p in powerups if p.active]

            # Boss Fight
            if mothership:
                mothership.update()
                
                if mothership.shoot_cooldown <= 0:
                    bullets.append(Bullet(mothership.rect.centerx, mothership.rect.bottom, is_player=False))
                    mothership.shoot_cooldown = 60
                else:
                    mothership.shoot_cooldown -= 1
                
                for b in bullets:
                    if mothership.active and b.speed < 0 and b.rect.colliderect(mothership.rect):
                        b.active = False
                        mothership.hp -= 1
                        if mothership.hp <= 0:
                            mothership.active = False
                
                if not mothership.active:
                    # Dropa sempre um powerup de vida ao matar o boss (bônus!)
                    bonus = PowerUp(mothership.rect.centerx, mothership.rect.centery)
                    bonus.type = 2
                    bonus.color = BMO_POWERUP_LIFE
                    bonus.label = "+1"
                    powerups.append(bonus)
                    
                    mothership = None
                    score += 500
                    boss_kills += 1
                    kills = 0
                    enemy_spawn_rate = max(20, 60 - (boss_kills * 5))
            else:
                enemy_spawn_timer += 1
                if enemy_spawn_timer >= enemy_spawn_rate:
                    enemies.append(Enemy())
                    enemy_spawn_timer = 0

                for e in enemies:
                    if e.update(): # Passou direto
                        if player.invulnerable == 0:
                            player.lives -= 1
                            player.invulnerable = 60
                            player.double_shot = False
                            player.cooldown_max = 15
                            if player.lives <= 0:
                                game_over = True
                    
                    if e.active and e.rect.colliderect(player.rect):
                        e.active = False
                        if player.invulnerable == 0:
                            player.lives -= 1
                            player.invulnerable = 60
                            player.double_shot = False
                            player.cooldown_max = 15
                            if player.lives <= 0:
                                game_over = True

                for e in enemies:
                    if not e.active: continue
                    for b in bullets:
                        if b.active and b.speed < 0 and b.rect.colliderect(e.rect):
                            b.active = False
                            e.active = False
                            score += 10
                            kills += 1
                            if random.random() < 0.1: # 10% de chance de powerup
                                powerups.append(PowerUp(e.rect.centerx, e.rect.centery))
                            break

                enemies = [e for e in enemies if e.active]

                if kills >= 30 and mothership is None:
                    mothership = Mothership()
                    enemies.clear()

        # Renderização
        screen.fill(BMO_BG)
        
        player.draw(screen)
        for b in bullets: b.draw(screen)
        for e in enemies: e.draw(screen)
        for p in powerups: p.draw(screen)
        if mothership: mothership.draw(screen)

        if game_over:
            ranking.mostrar_ranking_e_salvar(screen, clock, "space_invaders", score)
            player = Player()
            enemies = []
            bullets = []
            enemy_bullets = []
            particles = []
            powerups = []
            score = 0
            kills = 0
            wave = 1
            game_over = False
            mothership = None
            spawn_wave(wave, enemies)
            
        else:
            score_text = font.render(f"Pontos: {score}", True, BMO_TEXT)
            screen.blit(score_text, (10, 10))
            
            lives_text = font.render(f"Vidas: {player.lives}", True, BMO_TEXT)
            screen.blit(lives_text, (WIDTH - lives_text.get_width() - 10, 40))
            
            if not mothership:
                kills_text = font.render(f"Para Boss: {30 - kills}", True, BMO_TEXT)
                screen.blit(kills_text, (10, 40))



        pygame.display.flip()
        clock.tick(FPS)

if __name__ == "__main__":
    main()
