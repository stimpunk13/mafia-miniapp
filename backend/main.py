from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Dict, List, Optional
import copy
from dataclasses import dataclass, field, asdict
from enum import Enum
import json

app = FastAPI()

# CORS для работы с Telegram Mini App
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================
# РОЛИ (из вашего бота)
# ==========================
ROLE_BOSS = "Босс мафии"
ROLE_MAFIA = "Мафия"
ROLE_DOCTOR = "Доктор"
ROLE_COURTESAN = "Куртизанка"
ROLE_MANIAC = "Маньяк"
ROLE_IMMORTAL = "Бессмертный"
ROLE_AVENGER = "Мститель"
ROLE_CIVIL = "Мирный житель"
ROLE_COMMISSIONER = "Комиссар"
ROLE_DUKE = "Герцог"
ROLE_BANSHEE = "Банши"
ROLE_MONK = "Монах"
ROLE_SEER = "Гадалка"
ROLE_RAT = "Крыса"
ROLE_RAT_MAFIA = "мафия(крыса)"

ALL_ROLES_ORDER = [
    ROLE_BOSS, ROLE_DOCTOR, ROLE_COURTESAN, ROLE_MAFIA,
    ROLE_AVENGER, ROLE_IMMORTAL, ROLE_RAT, ROLE_COMMISSIONER,
    ROLE_DUKE, ROLE_BANSHEE, ROLE_MANIAC, ROLE_MONK,
    ROLE_SEER, ROLE_CIVIL,
]

ROLE_SHORT = {
    ROLE_BOSS: "Босс",
    ROLE_DOCTOR: "Доктор",
    ROLE_COURTESAN: "Куртиз",
    ROLE_MAFIA: "Мафия",
    ROLE_AVENGER: "Мститель",
    ROLE_IMMORTAL: "Бессмерт",
    ROLE_RAT: "Крыса",
    ROLE_COMMISSIONER: "Комисс",
    ROLE_DUKE: "Герцог",
    ROLE_BANSHEE: "Банши",
    ROLE_MANIAC: "Маньяк",
    ROLE_MONK: "Монах",
    ROLE_SEER: "Гадал",
    ROLE_CIVIL: "Мирный",
    ROLE_RAT_MAFIA: "Мафия(Крыса)",
}

def is_mafia_role(role: Optional[str]) -> bool:
    return role in {ROLE_BOSS, ROLE_MAFIA, ROLE_RAT_MAFIA}

def is_peace_role(role: Optional[str]) -> bool:
    return role is not None and (not is_mafia_role(role)) and role != ROLE_MANIAC

# ==========================
# STAGES
# ==========================
class Stage(str, Enum):
    LOBBY = "LOBBY"
    ADD_PLAYERS = "ADD_PLAYERS"
    EDIT_ROLES = "EDIT_ROLES"
    GAME_STARTED = "GAME_STARTED"
    DAY = "DAY"
    NIGHT = "NIGHT"
    END = "END"

# ==========================
# MODELS
# ==========================
@dataclass
class Player:
    name: str
    role: Optional[str] = None
    alive: bool = True
    is_mayor: bool = False

@dataclass
class Game:
    game_id: str
    host_id: int
    stage: Stage = Stage.LOBBY
    players: Dict[str, Player] = field(default_factory=dict)
    role_counts: Dict[str, int] = field(default_factory=dict)
    day: int = 0
    night: int = 0
    log_lines: List[str] = field(default_factory=list)

    def alive_names(self) -> List[str]:
        return [n for n, p in self.players.items() if p.alive]

    def mafia_alive_names(self) -> List[str]:
        return [n for n, p in self.players.items() if p.alive and is_mafia_role(p.role)]

    def peace_alive_names(self) -> List[str]:
        return [n for n, p in self.players.items() if p.alive and is_peace_role(p.role)]

# Хранилище игр (в реальном проекте используйте БД)
GAMES: Dict[str, Game] = {}

# ==========================
# PYDANTIC MODELS
# ==========================
class CreateGameRequest(BaseModel):
    host_id: int

class AddPlayerRequest(BaseModel):
    player_name: str

class SetRoleCountRequest(BaseModel):
    role: str
    count: int

class VoteRequest(BaseModel):
    target: str

# ==========================
# API ENDPOINTS
# ==========================
@app.get("/")
def read_root():
    return {"message": "Mafia Mini App API"}

@app.post("/api/game/create")
def create_game(req: CreateGameRequest):
    """Создать новую игру"""
    import uuid
    game_id = str(uuid.uuid4())
    
    g = Game(
        game_id=game_id,
        host_id=req.host_id,
        stage=Stage.LOBBY
    )
    
    # Дефолтные роли
    g.role_counts = {
        ROLE_BOSS: 1,
        ROLE_MAFIA: 2,
        ROLE_DOCTOR: 1,
        ROLE_COURTESAN: 1,
        ROLE_COMMISSIONER: 1,
        ROLE_CIVIL: 4,
    }
    
    GAMES[game_id] = g
    return {"game_id": game_id, "message": "Игра создана"}

@app.get("/api/game/{game_id}")
def get_game(game_id: str):
    """Получить состояние игры"""
    if game_id not in GAMES:
        raise HTTPException(status_code=404, detail="Игра не найдена")
    
    g = GAMES[game_id]
    
    return {
        "game_id": g.game_id,
        "stage": g.stage,
        "day": g.day,
        "night": g.night,
        "players": [
            {
                "name": p.name,
                "role": p.role,
                "alive": p.alive,
                "is_mayor": p.is_mayor
            }
            for p in g.players.values()
        ],
        "role_counts": g.role_counts,
        "log_lines": g.log_lines[-10:]  # Последние 10 записей
    }

@app.post("/api/game/{game_id}/add_player")
def add_player(game_id: str, req: AddPlayerRequest):
    """Добавить игрока"""
    if game_id not in GAMES:
        raise HTTPException(status_code=404, detail="Игра не найдена")
    
    g = GAMES[game_id]
    
    if g.stage != Stage.LOBBY and g.stage != Stage.ADD_PLAYERS:
        raise HTTPException(status_code=400, detail="Нельзя добавить игрока на этом этапе")
    
    if req.player_name in g.players:
        raise HTTPException(status_code=400, detail="Игрок уже существует")
    
    g.players[req.player_name] = Player(name=req.player_name)
    g.stage = Stage.ADD_PLAYERS
    
    return {"message": f"Игрок {req.player_name} добавлен"}

@app.post("/api/game/{game_id}/set_role_count")
def set_role_count(game_id: str, req: SetRoleCountRequest):
    """Установить количество ролей"""
    if game_id not in GAMES:
        raise HTTPException(status_code=404, detail="Игра не найдена")
    
    g = GAMES[game_id]
    
    if req.count < 0:
        raise HTTPException(status_code=400, detail="Количество не может быть отрицательным")
    
    if req.count == 0:
        g.role_counts.pop(req.role, None)
    else:
        g.role_counts[req.role] = req.count
    
    return {"message": f"Роль {req.role}: {req.count}"}

@app.post("/api/game/{game_id}/start")
def start_game(game_id: str):
    """Начать игру"""
    if game_id not in GAMES:
        raise HTTPException(status_code=404, detail="Игра не найдена")
    
    g = GAMES[game_id]
    
    total_roles = sum(g.role_counts.values())
    total_players = len(g.players)
    
    if total_roles != total_players:
        raise HTTPException(
            status_code=400, 
            detail=f"Количество ролей ({total_roles}) не совпадает с количеством игроков ({total_players})"
        )
    
    # Распределяем роли
    import random
    player_names = list(g.players.keys())
    random.shuffle(player_names)
    
    role_pool = []
    for role, count in g.role_counts.items():
        role_pool.extend([role] * count)
    
    for i, name in enumerate(player_names):
        g.players[name].role = role_pool[i]
    
    g.stage = Stage.GAME_STARTED
    g.day = 1
    g.log_lines.append("Игра началась! Роли распределены.")
    
    return {"message": "Игра началась!", "stage": g.stage}

@app.post("/api/game/{game_id}/vote")
def vote_player(game_id: str, req: VoteRequest):
    """Голосовать за изгнание игрока"""
    if game_id not in GAMES:
        raise HTTPException(status_code=404, detail="Игра не найдена")
    
    g = GAMES[game_id]
    
    if req.target not in g.players:
        raise HTTPException(status_code=400, detail="Игрок не найден")
    
    if not g.players[req.target].alive:
        raise HTTPException(status_code=400, detail="Игрок уже мёртв")
    
    g.players[req.target].alive = False
    role = g.players[req.target].role or "неизвестно"
    g.log_lines.append(f"День {g.day}: {req.target} ({role}) изгнан голосованием")
    
    # Проверка победы
    result = check_end(g)
    if result:
        g.stage = Stage.END
        g.log_lines.append(f"Игра окончена: {result}")
        return {"message": result, "game_ended": True}
    
    return {"message": f"{req.target} изгнан", "game_ended": False}

@app.post("/api/game/{game_id}/next_phase")
def next_phase(game_id: str):
    """Перейти к следующей фазе (день/ночь)"""
    if game_id not in GAMES:
        raise HTTPException(status_code=404, detail="Игра не найдена")
    
    g = GAMES[game_id]
    
    if g.stage == Stage.GAME_STARTED:
        g.stage = Stage.DAY
        return {"message": f"День {g.day}", "stage": g.stage}
    elif g.stage == Stage.DAY:
        g.stage = Stage.NIGHT
        g.night += 1
        return {"message": f"Ночь {g.night}", "stage": g.stage}
    elif g.stage == Stage.NIGHT:
        g.stage = Stage.DAY
        g.day += 1
        return {"message": f"День {g.day}", "stage": g.stage}
    
    return {"message": "Невозможно перейти к следующей фазе"}

@app.delete("/api/game/{game_id}")
def delete_game(game_id: str):
    """Удалить игру"""
    if game_id in GAMES:
        del GAMES[game_id]
        return {"message": "Игра удалена"}
    raise HTTPException(status_code=404, detail="Игра не найдена")

def check_end(g: Game) -> Optional[str]:
    """Проверка условий окончания игры"""
    mafia = g.mafia_alive_names()
    peace = g.peace_alive_names()
    
    if not mafia:
        return "Победа мирных! Вся мафия повержена."
    if len(mafia) >= len(peace):
        return "Победа мафии! Мафия захватила город."
    
    return None

# Монтируем статические файлы (frontend)
app.mount("/static", StaticFiles(directory="../frontend"), name="static")
