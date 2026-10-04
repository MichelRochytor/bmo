import pygame
import sys
import random
import pickle
import os
import math
import ranking

# Inicializa o Pygame
pygame.init()

# Cores (Paleta BMO)
BMO_BG = (156, 206, 168)
BMO_PLAYER = (45, 90, 50)
BMO_ENEMY = (200, 50, 50)
BMO_ENEMY_ELITE = (28, 55, 125)
BMO_TEXT = (20, 40, 20)
BMO_OVERLAY = (156, 206, 168)
BMO_BULLET = (20, 40, 20)
BMO_BOSS_BULLET = (245, 95, 65)
BMO_BOSS_HEAVY = (255, 220, 70)
BMO_POWERUP_DOUBLE = (50, 100, 200)
BMO_POWERUP_RAPID = (200, 150, 50)
BMO_POWERUP_LIFE = (200, 100, 150)
WHITE = (255, 255, 255)

# Configurações de Tela
import config

WIDTH, HEIGHT = config.LARGURA, config.ALTURA
PLAY_MARGIN = max(24, round(WIDTH * 0.045))
PLAY_LEFT = PLAY_MARGIN
PLAY_RIGHT = WIDTH - PLAY_MARGIN
PLAY_AREA = pygame.Rect(PLAY_LEFT, 0, PLAY_RIGHT - PLAY_LEFT, HEIGHT)
FPS = config.FPS

screen = pygame.display.set_mode((WIDTH, HEIGHT), config.display_flags(pygame))
pygame.display.set_caption("BMO - Space Invaders Fluido")
clock = pygame.time.Clock()
font = pygame.font.SysFont("Courier", 36, bold=True)
font_small = pygame.font.SysFont("Courier", 24, bold=True)
font_large = pygame.font.SysFont("Courier", 52, bold=True)
font_powerup = pygame.font.SysFont("Courier", 32, bold=True)

STARS = [
    [random.randint(PLAY_LEFT + 8, PLAY_RIGHT - 8), random.randint(0, HEIGHT), random.randint(2, 7)]
    for _ in range(110)
]

class Player:
    BASE_COOLDOWN = 15
    RAPID_COOLDOWN = 7
    RAPID_FIRE_SECONDS = 6

    def __init__(self):
        self.width = 64
        self.height = 48
        self.x = WIDTH // 2
        self.y = HEIGHT - 92
        self.speed = config.SPACE_PLAYER_SPEED
        self.rect = pygame.Rect(self.x - self.width//2, self.y - self.height//2, self.width, self.height)
        
        self.lives = 3
        self.invulnerable = 0
        
        self.cooldown = 0
        self.cooldown_max = self.BASE_COOLDOWN
        self.double_shot = False
        self.rapid_fire_timer = 0

    def move(self, dir):
        self.x += dir * self.speed
        if self.x < PLAY_LEFT + self.width // 2: self.x = PLAY_LEFT + self.width // 2
        if self.x > PLAY_RIGHT - self.width // 2: self.x = PLAY_RIGHT - self.width // 2
        self.rect.centerx = int(self.x)

    def update(self):
        if self.cooldown > 0:
            self.cooldown -= 1
        if self.invulnerable > 0:
            self.invulnerable -= 1
        if self.rapid_fire_timer > 0:
            self.rapid_fire_timer -= 1
            if self.rapid_fire_timer == 0:
                self.cooldown_max = self.BASE_COOLDOWN

    def activate_rapid_fire(self):
        self.cooldown_max = self.RAPID_COOLDOWN
        self.rapid_fire_timer = self.RAPID_FIRE_SECONDS * FPS

    def lose_upgrades(self):
        # O tiro duplo conserva o comportamento antigo: dura até o jogador sofrer dano.
        self.double_shot = False
        self.rapid_fire_timer = 0
        self.cooldown_max = self.BASE_COOLDOWN

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
    def __init__(self, x, y, is_player=True, velocity=None, size=None, color=None,
                 heavy=False, damage=1):
        width, height = size or (10, 28)
        self.rect = pygame.Rect(x - width // 2, y - height // 2, width, height)
        self.x = float(self.rect.x)
        self.y = float(self.rect.y)
        self.is_player = is_player
        self.color = color or BMO_BULLET
        self.heavy = heavy
        self.damage = max(1, int(damage))
        default_velocity = (0.0, -14.0 if is_player else 6.5)
        self.vx, self.vy = velocity or default_velocity
        # Mantido para compatibilidade com qualquer código externo antigo.
        self.speed = self.vy
        self.active = True

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.rect.topleft = (round(self.x), round(self.y))
        if (
            self.rect.bottom < 0 or self.rect.top > HEIGHT
            or self.rect.right < PLAY_LEFT or self.rect.left > PLAY_RIGHT
        ):
            self.active = False

    def draw(self, surface):
        if self.heavy:
            pygame.draw.ellipse(surface, self.color, self.rect)
            pygame.draw.ellipse(surface, WHITE, self.rect, 5)
        else:
            pygame.draw.rect(surface, self.color, self.rect, border_radius=4)

class WaveDirector:
    """Gera ondas infinitas com dificuldade progressiva e composição aleatória."""
    def __init__(self):
        self.wave = 1

    @property
    def speed_multiplier(self):
        # Crescimento mais forte e levemente curvo para as ondas avançadas.
        completed_waves = self.wave - 1
        return 1.0 + completed_waves * 0.20 + completed_waves * completed_waves * 0.012

    @property
    def spawn_rate(self):
        return max(24, config.SPACE_SPAWN_FRAMES - (self.wave - 1) * 9)

    @property
    def kills_to_boss(self):
        return min(70, 30 + (self.wave - 1) * 5)

    def choose_enemy_kind(self):
        if self.wave == 1:
            kinds = ("scout", "zigzag", "armored")
            weights = (50, 35, 15)
        else:
            elite_weight = min(45, 14 + (self.wave - 2) * 5)
            armored_weight = min(30, 18 + (self.wave - 2) * 2)
            kinds = ("scout", "zigzag", "armored", "elite")
            weights = (38, 28, armored_weight, elite_weight)
        return random.choices(kinds, weights=weights)[0]

    def next_wave(self):
        self.wave += 1


class Enemy:
    def __init__(self, director):
        self.kind = director.choose_enemy_kind()
        is_heavy = self.kind in ("armored", "elite")
        self.width = 68 if is_heavy else 52
        self.height = 52 if is_heavy else 42
        self.x = random.randint(PLAY_LEFT + self.width // 2, PLAY_RIGHT - self.width // 2)
        self.y = -self.height
        self.rect = pygame.Rect(self.x - self.width // 2, self.y - self.height // 2, self.width, self.height)
        velocidade_base = random.uniform(3.2, 6.0) if not is_heavy else 2.6
        self.speed = velocidade_base * config.SPACE_ENEMY_SPEED_FACTOR * director.speed_multiplier
        self.max_hp = 3 if self.kind == "elite" else (2 if self.kind == "armored" else 1)
        self.hp = self.max_hp
        # Inimigos mais resistentes também são mais perigosos.
        self.damage = self.max_hp
        self.value = 45 if self.kind == "elite" else (25 if self.kind == "armored" else 10)
        self.phase = random.uniform(0, 6.28)
        # O zigue-zague continua brincalhão, mas avança lateralmente com calma.
        self.drift = random.uniform(2.2, 4.8) if self.kind == "zigzag" else random.uniform(-1.0, 1.0)
        self.shoot_cooldown = random.randint(110, 220)
        self.shoot_delay_factor = max(0.52, 1.0 - (director.wave - 1) * 0.07)
        self.shoot_cooldown = round(self.shoot_cooldown * self.shoot_delay_factor)
        self.shoot_ready = False
        self.active = True

    def update(self):
        self.y += self.speed
        self.phase += 0.06
        if self.kind == "zigzag":
            self.x += math.sin(self.phase) * self.drift
        else:
            self.x += self.drift
        if self.x < PLAY_LEFT + self.width // 2 or self.x > PLAY_RIGHT - self.width // 2:
            self.drift *= -1
            self.x = max(PLAY_LEFT + self.width // 2, min(PLAY_RIGHT - self.width // 2, self.x))
        self.rect.center = (int(self.x), int(self.y))

        self.shoot_ready = False
        self.shoot_cooldown -= 1
        if self.y > 120 and self.shoot_cooldown <= 0:
            self.shoot_ready = True
            self.shoot_cooldown = round(random.randint(140, 260) * self.shoot_delay_factor)

        if self.rect.top > HEIGHT:
            self.active = False
            return True
        return False

    def fire(self):
        return Bullet(
            self.rect.centerx,
            self.rect.bottom,
            is_player=False,
            damage=self.damage,
        )

    def draw(self, surface):
        if self.kind == "elite":
            color = BMO_ENEMY_ELITE
        elif self.kind == "armored":
            color = (150, 35, 45)
        else:
            color = BMO_ENEMY
        pygame.draw.rect(surface, color, self.rect, border_radius=8)
        if self.max_hp > 1:
            pygame.draw.rect(surface, WHITE, self.rect, 4, border_radius=8)
            pip_radius = 4
            total_width = self.max_hp * 12
            start_x = self.rect.centerx - total_width // 2 + 6
            for index in range(self.max_hp):
                pip_color = WHITE if index < self.hp else BMO_BG
                pygame.draw.circle(surface, pip_color, (start_x + index * 12, self.rect.centery), pip_radius)
        
class PowerUp:
    def __init__(self, x, y):
        self.radius = max(22, round(min(WIDTH, HEIGHT) * 0.022))
        self.x = x
        self.y = y
        self.rect = pygame.Rect(x - self.radius, y - self.radius, self.radius*2, self.radius*2)
        self.speed = 1.8
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
        pygame.draw.circle(surface, WHITE, self.rect.center, self.radius, 3)
        text = font_powerup.render(self.label, True, WHITE)
        surface.blit(text, (self.rect.centerx - text.get_width()//2, self.rect.centery - text.get_height()//2))

class Mothership:
    def __init__(self, wave):
        self.wave = wave
        play_width = PLAY_RIGHT - PLAY_LEFT
        self.width = min(440, int(260 + (wave - 1) * 18), int(play_width * 0.72))
        self.height = min(190, 110 + (wave - 1) * 8)
        self.x = WIDTH // 2
        self.y = 100 + self.height // 2
        self.rect = pygame.Rect(self.x - self.width//2, self.y - self.height//2, self.width, self.height)
        # O primeiro chefe já é resistente; cada onda acrescenta bastante vida.
        self.max_hp = 35 + (wave - 1) * 24
        self.hp = self.max_hp
        self.speed = config.SPACE_MOTHERSHIP_SPEED * (1.25 + (wave - 1) * 0.11)
        self.direction = 1
        self.active = True

        # Ciclo: três rajadas completas, duas sequências diagonais e tiro pesado.
        self.attack_phase = 1
        self.phase_shots = 0
        self.diagonal_burst = 0
        self.attack_timer = self._frames(24)

    def _frames(self, base_frames):
        attack_speed = min(2.0, 1.0 + (self.wave - 1) * 0.10)
        return max(6, round(base_frames / attack_speed))

    def update(self):
        self.x += self.speed * self.direction
        self.rect.centerx = round(self.x)
        if self.rect.right > PLAY_RIGHT or self.rect.left < PLAY_LEFT:
            self.direction *= -1
            self.rect.right = min(self.rect.right, PLAY_RIGHT)
            self.rect.left = max(self.rect.left, PLAY_LEFT)
            self.x = self.rect.centerx

    def fire_three_direction(self):
        """Um tiro reto e dois diagonais."""
        vertical_speed = 7.6
        diagonal_speed = 4.2
        origin_y = self.rect.bottom
        return [
            Bullet(self.rect.centerx, origin_y, is_player=False,
                   velocity=(0.0, vertical_speed), color=BMO_BOSS_BULLET),
            Bullet(self.rect.centerx - self.width // 4, origin_y, is_player=False,
                   velocity=(-diagonal_speed, 6.8), color=BMO_BOSS_BULLET),
            Bullet(self.rect.centerx + self.width // 4, origin_y, is_player=False,
                   velocity=(diagonal_speed, 6.8), color=BMO_BOSS_BULLET),
        ]

    # Mantém compatibilidade com chamadas antigas do jogo.
    def fire_volley(self):
        return self.fire_three_direction()

    def fire_five_direction(self):
        """Leque de cinco direções, incluindo vertical e meias-diagonais."""
        origin_y = self.rect.bottom
        outer_vx = 4.2
        outer_vy = 6.8
        outer_angle = math.atan2(outer_vx, outer_vy)
        shot_speed = math.hypot(outer_vx, outer_vy)
        middle_vx = math.sin(outer_angle / 2) * shot_speed
        middle_vy = math.cos(outer_angle / 2) * shot_speed
        return [
            Bullet(self.rect.centerx - self.width // 3, origin_y, is_player=False,
                   velocity=(-outer_vx, outer_vy), color=BMO_BOSS_BULLET),
            Bullet(self.rect.centerx - self.width // 6, origin_y, is_player=False,
                   velocity=(-middle_vx, middle_vy), color=BMO_BOSS_BULLET),
            Bullet(self.rect.centerx, origin_y, is_player=False,
                   velocity=(0.0, 7.6), color=BMO_BOSS_BULLET),
            Bullet(self.rect.centerx + self.width // 6, origin_y, is_player=False,
                   velocity=(middle_vx, middle_vy), color=BMO_BOSS_BULLET),
            Bullet(self.rect.centerx + self.width // 3, origin_y, is_player=False,
                   velocity=(outer_vx, outer_vy), color=BMO_BOSS_BULLET),
        ]

    # Mantém compatibilidade com possíveis chamadas antigas.
    def fire_diagonals(self):
        return self.fire_five_direction()

    def fire_heavy(self):
        """Projétil central enorme, que ainda deixa espaço para desviar."""
        shot_width = min(150, 88 + (self.wave - 1) * 6)
        shot_height = min(220, 132 + (self.wave - 1) * 8)
        return [Bullet(
            self.rect.centerx,
            self.rect.bottom + shot_height // 2,
            is_player=False,
            velocity=(0.0, 5.8),
            size=(shot_width, shot_height),
            color=BMO_BOSS_HEAVY,
            heavy=True,
        )]

    def update_attack(self):
        """Avança uma etapa do padrão e devolve os tiros do quadro atual."""
        self.attack_timer -= 1
        if self.attack_timer > 0:
            return []

        if self.attack_phase == 1:
            shots = self.fire_three_direction()
            self.phase_shots += 1
            if self.phase_shots >= 3:
                self.attack_phase = 2
                self.phase_shots = 0
                self.attack_timer = self._frames(48)
            else:
                self.attack_timer = self._frames(30)
            return shots

        if self.attack_phase == 2:
            shots = self.fire_five_direction()
            self.phase_shots += 1
            if self.phase_shots >= 3:
                self.phase_shots = 0
                if self.diagonal_burst == 0:
                    self.diagonal_burst = 1
                    self.attack_timer = self._frames(44)
                else:
                    self.diagonal_burst = 0
                    self.attack_phase = 3
                    self.attack_timer = self._frames(54)
            else:
                self.attack_timer = self._frames(10)
            return shots

        shots = self.fire_heavy()
        self.attack_phase = 1
        self.phase_shots = 0
        self.attack_timer = self._frames(78)
        return shots

    def draw(self, surface):
        pygame.draw.rect(surface, BMO_ENEMY, self.rect, border_radius=24)
        pygame.draw.rect(surface, BMO_BG, self.rect, 7, border_radius=24)
        turret = pygame.Rect(0, 0, max(54, self.width // 4), max(24, self.height // 4))
        turret.center = (self.rect.centerx, self.rect.bottom - 8)
        pygame.draw.rect(surface, BMO_ENEMY_ELITE, turret, border_radius=10)
        
        hp_width = int((self.hp / self.max_hp) * self.width)
        if hp_width > 0:
            hp_rect = pygame.Rect(self.rect.left, self.rect.top - 20, hp_width, 11)
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
    director = WaveDirector()
    game_over = False
    
    enemy_spawn_timer = 0

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
                if b.active and not b.is_player and b.rect.colliderect(player.rect):
                    b.active = False
                    if player.invulnerable == 0:
                        player.lives -= b.damage
                        player.invulnerable = 60
                        player.lose_upgrades()
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
                        player.activate_rapid_fire()
                    elif p.type == 2:
                        if player.lives < 5: # Limite de 5 vidas para nao ficar infinito
                            player.lives += 1
            powerups = [p for p in powerups if p.active]

            # Boss Fight
            if mothership:
                mothership.update()
                bullets.extend(mothership.update_attack())
                
                for b in bullets:
                    if mothership.active and b.is_player and b.rect.colliderect(mothership.rect):
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
                    kills = 0
                    director.next_wave()
            else:
                enemy_spawn_timer += 1
                if enemy_spawn_timer >= director.spawn_rate:
                    enemies.append(Enemy(director))
                    enemy_spawn_timer = 0

                for e in enemies:
                    if e.update(): # Passou direto
                        if player.invulnerable == 0:
                            player.lives -= e.damage
                            player.invulnerable = 60
                            player.lose_upgrades()
                            if player.lives <= 0:
                                game_over = True

                    if e.active and e.shoot_ready:
                        bullets.append(e.fire())
                    
                    if e.active and e.rect.colliderect(player.rect):
                        e.active = False
                        if player.invulnerable == 0:
                            player.lives -= e.damage
                            player.invulnerable = 60
                            player.lose_upgrades()
                            if player.lives <= 0:
                                game_over = True

                for e in enemies:
                    if not e.active: continue
                    for b in bullets:
                        if b.active and b.is_player and b.rect.colliderect(e.rect):
                            b.active = False
                            e.hp -= 1
                            if e.hp <= 0:
                                e.active = False
                                score += e.value
                                kills += 1
                                if random.random() < 0.1: # 10% de chance de powerup
                                    powerups.append(PowerUp(e.rect.centerx, e.rect.centery))
                            break

                enemies = [e for e in enemies if e.active]

                if kills >= director.kills_to_boss and mothership is None:
                    mothership = Mothership(director.wave)
                    enemies.clear()
                    # Não carrega tiros inimigos da onda normal para a arena do chefe.
                    bullets = [b for b in bullets if b.is_player]

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
            powerups = []
            score = 0
            kills = 0
            director = WaveDirector()
            game_over = False
            mothership = None
            enemy_spawn_timer = 0
            
        else:
            score_text = font.render(f"Pontos: {score}", True, BMO_TEXT)
            screen.blit(score_text, (10, 10))
            
            lives_text = font.render(f"Vidas: {player.lives}", True, BMO_TEXT)
            screen.blit(lives_text, (WIDTH - lives_text.get_width() - 10, 40))

            wave_text = font_small.render(f"Onda: {director.wave}", True, BMO_TEXT)
            screen.blit(wave_text, (WIDTH - wave_text.get_width() - 10, 10))
            
            if not mothership:
                remaining = max(0, director.kills_to_boss - kills)
                kills_text = font.render(f"Para Boss: {remaining}", True, BMO_TEXT)
                screen.blit(kills_text, (10, 40))



        pygame.display.flip()
        clock.tick(FPS)

if __name__ == "__main__":
    main()
