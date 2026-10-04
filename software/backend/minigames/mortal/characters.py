from dataclasses import dataclass


@dataclass(frozen=True)
class FighterSpec:
    key: str
    name: str
    area: str
    folder: str
    color: tuple[int, int, int]
    accent: tuple[int, int, int]
    life: int
    power: int
    speed: int
    defense: int
    technique: int
    specials: tuple[str, str, str]


ROSTER = (
    FighterSpec("caecomp", "CAECOMP", "Engenharia da Computação", "caecomp", (25, 151, 231), (109, 220, 255), 80, 73, 88, 70, 95, ("Código Fatal", "Overclock", "Dados Destrutivos")),
    FighterSpec("caetx", "CAETX", "Engenharia Têxtil", "caetx", (151, 61, 163), (242, 130, 255), 84, 74, 78, 79, 83, ("Trama Secreta", "Fibra Imparável", "Tecido Protetor")),
    FighterSpec("caec", "CAEC", "Engenharia Civil", "caec", (216, 137, 16), (255, 203, 69), 97, 89, 61, 95, 70, ("Fundação Inabalável", "Construção Perfeita", "Estrutura Suprema")),
    FighterSpec("caliq", "CALIQ", "Licenciatura em Química", "caliq", (36, 165, 92), (125, 242, 150), 78, 68, 80, 72, 96, ("Reação em Cadeia", "Solução Tóxica", "Transformação Química")),
    FighterSpec("roboap", "ROBOAP", "Automação e Programação", "roboap", (204, 128, 17), (255, 190, 50), 90, 85, 67, 88, 84, ("Protocolo Alfa", "Sistema Robótico", "Upgrade Total")),
    FighterSpec("pantherion", "PANTHERION", "Luta por Estilo", "pantherion", (205, 47, 114), (255, 126, 187), 82, 77, 91, 71, 87, ("Garra Afiada", "Elegância Letal", "Conforto Dominante")),
    FighterSpec("caeq", "CAEQ", "Engenharia Química", "caeq", (55, 103, 207), (145, 187, 255), 86, 76, 76, 84, 94, ("Síntese Precisa", "Reação Controlada", "Elemento Surpresa")),
    FighterSpec("codificadoras", "CODIFICADORAS", "Código. Mulheres. Futuro.", "codificadoras", (224, 24, 155), (255, 113, 213), 78, 70, 96, 72, 99, ("Ataque de Código", "Firewall Rosa", "Quebra de Sistema")),
    FighterSpec("cael", "CAEL", "Engenharia Elétrica", "cael", (235, 145, 22), (255, 213, 71), 86, 85, 84, 74, 89, ("Choque Elétrico", "Circuito Sobrecarga", "Campo Eletromagnético")),
    FighterSpec("cadem", "CADEM", "Design de Moda", "cadem", (169, 44, 195), (250, 104, 255), 80, 75, 89, 73, 93, ("Corte Preciso", "Costura Letal", "Estilo Único")),
)

FIGHTERS = {fighter.key: fighter for fighter in ROSTER}
