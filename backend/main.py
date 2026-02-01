from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional, Set, Tuple
import copy
from dataclasses import dataclass, field, asdict
from enum import Enum
import uuid
import re

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
# ROLES
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

BIND_ROLES_ORDER = [
    ROLE_BOSS, ROLE_MAFIA, ROLE_DOCTOR, ROLE_COURTESAN,
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

# Role descriptions for UI
ROLE_DESCRIPTIONS = {
    ROLE_BOSS: "Глава мафии. Может запугать игрока (защита от голосования на день).",
    ROLE_MAFIA: "Член мафии. Убивает ночью вместе с боссом.",
    ROLE_DOCTOR: "Лечит одного игрока за ночь. Не может лечить одного дважды подряд.",
    ROLE_COURTESAN: "Защищает клиента ночью. Если её убьют — клиент тоже умрёт.",
    ROLE_MANIAC: "Нейтрал. Убивает ночью. Побеждает если остаётся последним.",
    ROLE_IMMORTAL: "Не может умереть ночью.",
    ROLE_AVENGER: "При смерти днём может забрать кого-то с собой.",
    ROLE_CIVIL: "Обычный мирный житель.",
    ROLE_COMMISSIONER: "Проверяет игроков на принадлежность к мафии.",
    ROLE_DUKE: "При смерти ночью — следующий день без голосования (траур).",
    ROLE_BANSHEE: "При смерти днём — ночь не наступает.",
    ROLE_MONK: "Перенаправляет убийство с одного игрока на другого.",
    ROLE_SEER: "Выбирает игрока для гадания (таро в реале).",
    ROLE_RAT: "Может стать мафией если обе стороны согласны.",
    ROLE_RAT_MAFIA: "Бывшая крыса, ставшая мафией.",
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
    PRESTART = "PRESTART"
    EDIT_PARTICIPANTS = "EDIT_PARTICIPANTS"
    REMOVE_PLAYER = "REMOVE_PLAYER"

    NIGHT0_BIND_ROLE = "NIGHT0_BIND_ROLE"
    NIGHT0_BIND_PLAYER = "NIGHT0_BIND_PLAYER"

    MAYOR_SELECT = "MAYOR_SELECT"
    SUCCESSOR_SELECT = "SUCCESSOR_SELECT"

    DAY_MENU = "DAY_MENU"
    DAY_VOTE_PICK = "DAY_VOTE_PICK"
    AVENGER_REVENGE_PICK = "AVENGER_REVENGE_PICK"

    NIGHT_MENU = "NIGHT_MENU"
    NIGHT_PICK = "NIGHT_PICK"

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
    is_successor: bool = False


@dataclass
class NightChoices:
    mafia_target: Optional[str] = None
    boss_intimidate: Optional[str] = None
    maniac_target: Optional[str] = None
    commissioner_target: Optional[str] = None
    monk_first: Optional[str] = None
    monk_second: Optional[str] = None
    doctor_target: Optional[str] = None
    courtesan_client: Optional[str] = None
    seer_target: Optional[str] = None
    rat_wants: Optional[bool] = None
    mafia_wants_rat: Optional[bool] = None


@dataclass
class GameSnapshot:
    """Snapshot for undo functionality"""
    players: Dict[str, dict]
    stage: Stage
    day: int
    night: int
    mayor_name: Optional[str]
    successor_name: Optional[str]
    protected_from_vote_day: Dict[str, int]
    skip_vote_day: Optional[int]
    night_choices: dict
    night_steps: List[str]
    night_step_index: int
    pending_step: Optional[str]
    last_boss_intimidate: Optional[str]
    last_doctor: Optional[str]
    last_courtesan: Optional[str]
    last_seer: Optional[str]
    last_monk_first: Optional[str]
    last_commissioner: Optional[str]
    avenger_pending: Optional[str]
    log_lines: List[str]


@dataclass
class Game:
    game_id: str
    host_id: int

    stage: Stage = Stage.LOBBY
    players: Dict[str, Player] = field(default_factory=dict)
    role_counts: Dict[str, int] = field(default_factory=dict)

    day: int = 0
    night: int = 0

    # night0 bind
    bind_remaining: Dict[str, int] = field(default_factory=dict)
    bind_available_players: List[str] = field(default_factory=list)
    bind_stack: List[Tuple[str, str]] = field(default_factory=list)
    bind_selected_role: Optional[str] = None

    # mayor / successor
    mayor_name: Optional[str] = None
    successor_name: Optional[str] = None
    protected_from_vote_day: Dict[str, int] = field(default_factory=dict)

    # duke mourning
    skip_vote_day: Optional[int] = None

    # undo
    undo_stack: List[GameSnapshot] = field(default_factory=list)

    # night flow
    night_choices: NightChoices = field(default_factory=NightChoices)
    night_steps: List[str] = field(default_factory=list)
    night_step_index: int = 0
    pending_step: Optional[str] = None

    # last targets restrictions
    last_boss_intimidate: Optional[str] = None
    last_doctor: Optional[str] = None
    last_courtesan: Optional[str] = None
    last_seer: Optional[str] = None
    last_monk_first: Optional[str] = None
    last_commissioner: Optional[str] = None

    # avenger
    avenger_pending: Optional[str] = None

    # log
    log_lines: List[str] = field(default_factory=list)

    def alive_names(self) -> List[str]:
        return [n for n, p in self.players.items() if p.alive]

    def mafia_alive_names(self) -> List[str]:
        return [p.name for p in self.players.values() if p.alive and is_mafia_role(p.role)]

    def peace_alive_names(self) -> List[str]:
        return [p.name for p in self.players.values() if p.alive and is_peace_role(p.role)]

    def maniac_alive(self) -> bool:
        return any(p.alive and p.role == ROLE_MANIAC for p in self.players.values())

    def role_alive_exists(self, role: str) -> bool:
        return any(p.alive and p.role == role for p in self.players.values())

    def get_role_owner(self, role: str) -> Optional[str]:
        for p in self.players.values():
            if p.alive and p.role == role:
                return p.name
        return None

    def push_undo(self):
        snap = GameSnapshot(
            players={n: {"name": p.name, "role": p.role, "alive": p.alive,
                        "is_mayor": p.is_mayor, "is_successor": p.is_successor}
                    for n, p in self.players.items()},
            stage=self.stage,
            day=self.day,
            night=self.night,
            mayor_name=self.mayor_name,
            successor_name=self.successor_name,
            protected_from_vote_day=copy.deepcopy(self.protected_from_vote_day),
            skip_vote_day=self.skip_vote_day,
            night_choices={
                "mafia_target": self.night_choices.mafia_target,
                "boss_intimidate": self.night_choices.boss_intimidate,
                "maniac_target": self.night_choices.maniac_target,
                "commissioner_target": self.night_choices.commissioner_target,
                "monk_first": self.night_choices.monk_first,
                "monk_second": self.night_choices.monk_second,
                "doctor_target": self.night_choices.doctor_target,
                "courtesan_client": self.night_choices.courtesan_client,
                "seer_target": self.night_choices.seer_target,
                "rat_wants": self.night_choices.rat_wants,
                "mafia_wants_rat": self.night_choices.mafia_wants_rat,
            },
            night_steps=self.night_steps[:],
            night_step_index=self.night_step_index,
            pending_step=self.pending_step,
            last_boss_intimidate=self.last_boss_intimidate,
            last_doctor=self.last_doctor,
            last_courtesan=self.last_courtesan,
            last_seer=self.last_seer,
            last_monk_first=self.last_monk_first,
            last_commissioner=self.last_commissioner,
            avenger_pending=self.avenger_pending,
            log_lines=self.log_lines[:],
        )
        self.undo_stack.append(snap)

    def pop_undo(self) -> bool:
        if not self.undo_stack:
            return False
        snap = self.undo_stack.pop()

        self.players = {n: Player(**p) for n, p in snap.players.items()}
        self.stage = snap.stage
        self.day = snap.day
        self.night = snap.night
        self.mayor_name = snap.mayor_name
        self.successor_name = snap.successor_name
        self.protected_from_vote_day = snap.protected_from_vote_day
        self.skip_vote_day = snap.skip_vote_day
        self.night_choices = NightChoices(**snap.night_choices)
        self.night_steps = snap.night_steps
        self.night_step_index = snap.night_step_index
        self.pending_step = snap.pending_step
        self.last_boss_intimidate = snap.last_boss_intimidate
        self.last_doctor = snap.last_doctor
        self.last_courtesan = snap.last_courtesan
        self.last_seer = snap.last_seer
        self.last_monk_first = snap.last_monk_first
        self.last_commissioner = snap.last_commissioner
        self.avenger_pending = snap.avenger_pending
        self.log_lines = snap.log_lines
        return True


# ==========================
# STORAGE
# ==========================
GAMES: Dict[str, Game] = {}


def init_default_roles(g: Game):
    g.role_counts = {
        ROLE_BOSS: 1,
        ROLE_DOCTOR: 1,
        ROLE_COURTESAN: 1,
        ROLE_MAFIA: 1,
        ROLE_AVENGER: 0,
        ROLE_IMMORTAL: 0,
        ROLE_RAT: 0,
        ROLE_COMMISSIONER: 0,
        ROLE_DUKE: 0,
        ROLE_BANSHEE: 0,
        ROLE_MANIAC: 0,
        ROLE_MONK: 0,
        ROLE_SEER: 0,
        ROLE_CIVIL: 0,
    }


def get_game(game_id: str) -> Game:
    if game_id not in GAMES:
        raise HTTPException(status_code=404, detail="Игра не найдена")
    return GAMES[game_id]


# ==========================
# HELPER FUNCTIONS
# ==========================
def roles_sum(g: Game) -> int:
    return sum(g.role_counts.values())


def role_constraints_ok(g: Game) -> Tuple[bool, str]:
    if g.role_counts.get(ROLE_BOSS, 0) != 1:
        return False, "Босс мафии должен быть ровно 1."
    if g.role_counts.get(ROLE_DOCTOR, 0) != 1:
        return False, "Доктор должен быть ровно 1."
    if g.role_counts.get(ROLE_COURTESAN, 0) != 1:
        return False, "Куртизанка должна быть ровно 1."
    if g.role_counts.get(ROLE_MAFIA, 0) < 1:
        return False, "Мафия должна быть минимум 1."
    for r in [ROLE_AVENGER, ROLE_IMMORTAL, ROLE_RAT, ROLE_COMMISSIONER, ROLE_DUKE,
              ROLE_BANSHEE, ROLE_MANIAC, ROLE_MONK, ROLE_SEER]:
        if g.role_counts.get(r, 0) not in (0, 1):
            return False, f"Роль {r} может быть только 0 или 1."
    if len(g.players) <= 0:
        return False, "Добавьте игроков."
    if roles_sum(g) != len(g.players):
        return False, f"Сумма ролей ({roles_sum(g)}) должна равняться числу игроков ({len(g.players)})."
    return True, "OK"


def special_threshold_blocks(g: Game) -> bool:
    """Check if special abilities are blocked due to threshold"""
    mafia = len(g.mafia_alive_names())
    peace = len(g.peace_alive_names())
    return (peace == 2 and mafia == 1) or (peace == 3 and mafia == 2)


def check_end(g: Game) -> Optional[str]:
    """Check game end conditions"""
    mafia = len(g.mafia_alive_names())
    peace = len(g.peace_alive_names())
    maniac = 1 if g.maniac_alive() else 0
    total = len(g.alive_names())

    if total == 3 and mafia == 1 and peace == 1 and maniac == 1:
        return "Ничья (1 мирный, 1 мафия, 1 маньяк)"

    if mafia == 0:
        return "Победа мирных (вся мафия уничтожена)"

    if mafia > 0 and mafia >= peace:
        return "Победа мафии (мафия >= мирные)"

    return None


def boss_intimidation_allowed(g: Game) -> bool:
    """Check if boss can use intimidation"""
    mafia = len(g.mafia_alive_names())
    peace = len(g.peace_alive_names())
    if g.role_alive_exists(ROLE_BOSS) and mafia == 1 and peace == 3:
        return False
    return g.role_alive_exists(ROLE_BOSS)


def build_night_steps(g: Game) -> List[str]:
    """Build list of night action steps"""
    steps: List[str] = []
    if len(g.mafia_alive_names()) > 0:
        steps.append("mafia_kill")
    if boss_intimidation_allowed(g):
        steps.append("boss_intimidate")
    if g.role_alive_exists(ROLE_MANIAC):
        steps.append("maniac_kill")
    if g.role_alive_exists(ROLE_COMMISSIONER):
        steps.append("commissioner_check")
    if g.role_alive_exists(ROLE_MONK):
        steps.append("monk_first")
        steps.append("monk_second")
    if g.role_alive_exists(ROLE_DOCTOR):
        steps.append("doctor_heal")
    if g.role_alive_exists(ROLE_COURTESAN):
        steps.append("courtesan_visit")
    if g.role_alive_exists(ROLE_SEER):
        steps.append("seer_divine")
    if len(g.mafia_alive_names()) == 1 and g.role_alive_exists(ROLE_RAT):
        steps.append("rat_wants")
        steps.append("mafia_wants_rat")
    return steps


def get_step_title(step: str) -> str:
    """Get human-readable title for night step"""
    titles = {
        "mafia_kill": "Мафия убивает",
        "boss_intimidate": "Босс мафии запугивает",
        "maniac_kill": "Маньяк убивает",
        "commissioner_check": "Комиссар проверяет",
        "monk_first": "Монах (1-е указание)",
        "monk_second": "Монах (2-е указание)",
        "doctor_heal": "Доктор лечит",
        "courtesan_visit": "Куртизанка идёт к",
        "seer_divine": "Гадалка гадает",
        "rat_wants": "Крыса хочет стать мафией?",
        "mafia_wants_rat": "Мафия хочет крысу?",
    }
    return titles.get(step, step)


def get_step_targets(g: Game, step: str) -> List[str]:
    """Get available targets for a night step"""
    alive = g.alive_names()

    if step == "mafia_kill":
        return [n for n in alive if not is_mafia_role(g.players[n].role)]

    elif step == "boss_intimidate":
        targets = alive[:]
        if g.last_boss_intimidate:
            targets = [n for n in targets if n != g.last_boss_intimidate]
        return targets

    elif step == "maniac_kill":
        maniac_name = g.get_role_owner(ROLE_MANIAC)
        return [n for n in alive if n != maniac_name]

    elif step == "commissioner_check":
        comm = g.get_role_owner(ROLE_COMMISSIONER)
        targets = [n for n in alive if n != comm]
        if g.last_commissioner:
            targets = [n for n in targets if n != g.last_commissioner]
        return targets

    elif step == "monk_first":
        targets = alive[:]
        if g.last_monk_first:
            targets = [n for n in targets if n != g.last_monk_first]
        return targets

    elif step == "monk_second":
        monk = g.get_role_owner(ROLE_MONK)
        return [n for n in alive if n != monk and n != g.night_choices.monk_first]

    elif step == "doctor_heal":
        targets = alive[:]
        if g.last_doctor:
            targets = [n for n in targets if n != g.last_doctor]
        return targets

    elif step == "courtesan_visit":
        courtesan = g.get_role_owner(ROLE_COURTESAN)
        targets = [n for n in alive if n != courtesan]
        if g.last_courtesan:
            targets = [n for n in targets if n != g.last_courtesan]
        return targets

    elif step == "seer_divine":
        targets = alive[:]
        if g.last_seer:
            targets = [n for n in targets if n != g.last_seer]
        return targets

    return []


def commissioner_answer_for(g: Game, target: str) -> str:
    """Get commissioner check result"""
    role = g.players[target].role if target in g.players else None
    if role in {ROLE_RAT, ROLE_RAT_MAFIA}:
        return "НЕТ, не мафия"
    return "ДА, мафия" if is_mafia_role(role) else "НЕТ, не мафия"


def apply_night_and_get_deaths(g: Game) -> Tuple[List[str], List[str]]:
    """Apply night actions and return (deaths, summary)"""
    c = g.night_choices
    deaths: Set[str] = set()
    summary: List[str] = []

    def alive(name: Optional[str]) -> bool:
        return bool(name) and name in g.players and g.players[name].alive

    def role_of(name: str) -> Optional[str]:
        return g.players[name].role if name in g.players else None

    def is_immortal(name: str) -> bool:
        return alive(name) and role_of(name) == ROLE_IMMORTAL

    # defenders
    courtesan_alive = g.role_alive_exists(ROLE_COURTESAN)
    courtesan_name = g.get_role_owner(ROLE_COURTESAN) if courtesan_alive else None
    client = c.courtesan_client if courtesan_alive and alive(c.courtesan_client) else None
    doctor_target = c.doctor_target if g.role_alive_exists(ROLE_DOCTOR) and alive(c.doctor_target) else None

    mafia_intended = c.mafia_target if alive(c.mafia_target) else None
    maniac_intended = c.maniac_target if g.role_alive_exists(ROLE_MANIAC) and alive(c.maniac_target) else None

    # monk redirect
    monk_active = g.role_alive_exists(ROLE_MONK) and alive(c.monk_first) and alive(c.monk_second)
    mafia_actual = mafia_intended
    maniac_actual = maniac_intended

    if monk_active:
        if mafia_intended and c.monk_first == mafia_intended:
            mafia_actual = c.monk_second
        if maniac_intended and c.monk_first == maniac_intended:
            maniac_actual = c.monk_second

    def saved_by_doctor(t: str) -> bool:
        return doctor_target == t

    def saved_by_courtesan(t: str) -> bool:
        return client == t

    def kill_logic(target: Optional[str]):
        if not target or not alive(target):
            return
        if is_immortal(target):
            return
        if saved_by_courtesan(target):
            return
        if courtesan_alive and courtesan_name == target:
            if saved_by_doctor(target):
                return
            deaths.add(target)
            if client and alive(client) and not is_immortal(client):
                deaths.add(client)
            return
        if saved_by_doctor(target):
            return
        deaths.add(target)

    if mafia_actual:
        kill_logic(mafia_actual)
    if maniac_actual:
        kill_logic(maniac_actual)

    # Build summary
    def outcome(killer_label: str, intended: Optional[str], actual: Optional[str]) -> Optional[str]:
        if not intended:
            return None
        if not actual:
            return f"{killer_label}: не выбрано"
        if actual in deaths:
            result = f"{killer_label}: {intended}"
            if actual != intended:
                result += f" → {actual}"
            return result + " — УБИТ"
        if is_immortal(actual):
            reason = "бессмертный"
        elif saved_by_courtesan(actual):
            reason = "спасла куртизанка"
        elif saved_by_doctor(actual):
            reason = "спас доктор"
        else:
            reason = "выжил"
        result = f"{killer_label}: {intended}"
        if actual != intended:
            result += f" → {actual}"
        return result + f" — ВЫЖИЛ ({reason})"

    if mafia_intended:
        s = outcome("Мафия стреляла", mafia_intended, mafia_actual)
        if s:
            summary.append(s)

    if boss_intimidation_allowed(g) and alive(c.boss_intimidate):
        summary.append(f"Босс мафии запугал {c.boss_intimidate}")

    if maniac_intended:
        s = outcome("Маньяк выбрал", maniac_intended, maniac_actual)
        if s:
            summary.append(s)

    if alive(c.commissioner_target) and g.role_alive_exists(ROLE_COMMISSIONER):
        summary.append(f"Комиссар проверил {c.commissioner_target}: {commissioner_answer_for(g, c.commissioner_target)}")

    if monk_active:
        summary.append(f"Монах: 1-е {c.monk_first}, 2-е {c.monk_second}")

    if doctor_target:
        summary.append(f"Доктор лечил {doctor_target}")

    if client:
        summary.append(f"Куртизанка была с {client}")

    if alive(c.seer_target) and g.role_alive_exists(ROLE_SEER):
        summary.append(f"Гадалка выбрала {c.seer_target}")

    if len(g.mafia_alive_names()) == 1 and g.role_alive_exists(ROLE_RAT):
        if c.rat_wants is not None and c.mafia_wants_rat is not None:
            summary.append(f"Крыса хочет стать мафией: {'ДА' if c.rat_wants else 'НЕТ'}")
            summary.append(f"Мафия хочет крысу: {'ДА' if c.mafia_wants_rat else 'НЕТ'}")

    return sorted(deaths), summary


def handle_mayor_death(g: Game, died: str):
    """Handle mayor death and succession"""
    if died != g.mayor_name:
        return
    succ = g.successor_name
    if succ and succ in g.players and g.players[succ].alive:
        g.players[succ].is_successor = False
        g.players[succ].is_mayor = True
        g.mayor_name = succ
        g.successor_name = None
        g.protected_from_vote_day[succ] = g.day


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


class BindRoleRequest(BaseModel):
    role: str


class BindPlayerRequest(BaseModel):
    player_name: str


class SelectMayorRequest(BaseModel):
    player_name: str


class SelectSuccessorRequest(BaseModel):
    player_name: str


class VoteRequest(BaseModel):
    target: str


class RevengeRequest(BaseModel):
    target: str


class NightActionRequest(BaseModel):
    target: Optional[str] = None
    choice: Optional[bool] = None  # For yes/no choices (rat, mafia_wants_rat)


# ==========================
# API ENDPOINTS
# ==========================
@app.get("/")
def read_root():
    return {"message": "Mafia Mini App API v2"}


@app.get("/api/roles")
def get_roles():
    """Get all available roles with descriptions"""
    return {
        "roles": [
            {
                "id": role,
                "name": role,
                "short": ROLE_SHORT.get(role, role),
                "description": ROLE_DESCRIPTIONS.get(role, ""),
            }
            for role in ALL_ROLES_ORDER
        ],
        "bind_order": BIND_ROLES_ORDER,
    }


@app.post("/api/game/create")
def create_game(req: CreateGameRequest):
    """Create a new game"""
    game_id = str(uuid.uuid4())
    g = Game(game_id=game_id, host_id=req.host_id, stage=Stage.LOBBY)
    init_default_roles(g)
    GAMES[game_id] = g
    return {"game_id": game_id, "message": "Игра создана"}


@app.get("/api/game/{game_id}")
def get_game_state(game_id: str):
    """Get full game state"""
    g = get_game(game_id)

    # Get current night step info
    current_step = None
    current_step_title = None
    current_step_targets = []
    current_step_is_yesno = False

    if g.stage == Stage.NIGHT_MENU and g.night_step_index < len(g.night_steps):
        current_step = g.night_steps[g.night_step_index]
        current_step_title = get_step_title(current_step)
        if current_step in ["rat_wants", "mafia_wants_rat"]:
            current_step_is_yesno = True
        else:
            current_step_targets = get_step_targets(g, current_step)

    # Get protected players for today
    protected_today = [name for name, d in g.protected_from_vote_day.items() if d == g.day]

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
                "is_mayor": p.is_mayor,
                "is_successor": p.is_successor,
            }
            for p in g.players.values()
        ],
        "role_counts": g.role_counts,
        "roles_sum": roles_sum(g),
        "players_count": len(g.players),

        # Bind state (for NIGHT0)
        "bind_remaining": g.bind_remaining,
        "bind_available_players": g.bind_available_players,
        "bind_selected_role": g.bind_selected_role,
        "bind_stack": g.bind_stack,

        # Mayor/successor
        "mayor_name": g.mayor_name,
        "successor_name": g.successor_name,
        "protected_today": protected_today,

        # Night state
        "night_steps": g.night_steps,
        "night_step_index": g.night_step_index,
        "current_step": current_step,
        "current_step_title": current_step_title,
        "current_step_targets": current_step_targets,
        "current_step_is_yesno": current_step_is_yesno,
        "night_choices": {
            "mafia_target": g.night_choices.mafia_target,
            "boss_intimidate": g.night_choices.boss_intimidate,
            "maniac_target": g.night_choices.maniac_target,
            "commissioner_target": g.night_choices.commissioner_target,
            "commissioner_result": commissioner_answer_for(g, g.night_choices.commissioner_target) if g.night_choices.commissioner_target else None,
            "monk_first": g.night_choices.monk_first,
            "monk_second": g.night_choices.monk_second,
            "doctor_target": g.night_choices.doctor_target,
            "courtesan_client": g.night_choices.courtesan_client,
            "seer_target": g.night_choices.seer_target,
            "rat_wants": g.night_choices.rat_wants,
            "mafia_wants_rat": g.night_choices.mafia_wants_rat,
        },

        # Avenger
        "avenger_pending": g.avenger_pending,

        # Skip vote (duke mourning)
        "skip_vote_day": g.skip_vote_day,
        "is_mourning_day": g.skip_vote_day == g.day,

        # Undo
        "can_undo": len(g.undo_stack) > 0,

        # Log
        "log_lines": g.log_lines[-20:],
        "full_log": g.log_lines,
    }


@app.post("/api/game/{game_id}/add_player")
def add_player(game_id: str, req: AddPlayerRequest):
    """Add a player to the game"""
    g = get_game(game_id)

    if g.stage not in [Stage.LOBBY, Stage.ADD_PLAYERS, Stage.EDIT_PARTICIPANTS]:
        raise HTTPException(status_code=400, detail="Нельзя добавить игрока на этом этапе")

    name = req.player_name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Имя не может быть пустым")

    if name in g.players:
        raise HTTPException(status_code=400, detail="Игрок уже существует")

    g.players[name] = Player(name=name)
    g.stage = Stage.ADD_PLAYERS

    return {"message": f"Игрок {name} добавлен", "players_count": len(g.players)}


@app.delete("/api/game/{game_id}/player/{player_name}")
def remove_player(game_id: str, player_name: str):
    """Remove a player from the game"""
    g = get_game(game_id)

    if g.stage not in [Stage.LOBBY, Stage.ADD_PLAYERS, Stage.EDIT_PARTICIPANTS, Stage.REMOVE_PLAYER, Stage.PRESTART]:
        raise HTTPException(status_code=400, detail="Нельзя удалить игрока на этом этапе")

    if player_name not in g.players:
        raise HTTPException(status_code=404, detail="Игрок не найден")

    del g.players[player_name]

    return {"message": f"Игрок {player_name} удалён", "players_count": len(g.players)}


@app.post("/api/game/{game_id}/set_role_count")
def set_role_count(game_id: str, req: SetRoleCountRequest):
    """Set role count"""
    g = get_game(game_id)

    if req.count < 0:
        raise HTTPException(status_code=400, detail="Количество не может быть отрицательным")

    # Validate fixed roles
    fixed = {ROLE_BOSS, ROLE_DOCTOR, ROLE_COURTESAN}
    if req.role in fixed and req.count != 1:
        raise HTTPException(status_code=400, detail=f"Роль {req.role} должна быть ровно 1")

    # Validate optional max1 roles
    optional_max1 = {ROLE_AVENGER, ROLE_IMMORTAL, ROLE_RAT, ROLE_COMMISSIONER, ROLE_DUKE,
                     ROLE_BANSHEE, ROLE_MANIAC, ROLE_MONK, ROLE_SEER}
    if req.role in optional_max1 and req.count > 1:
        raise HTTPException(status_code=400, detail=f"Роль {req.role} может быть только 0 или 1")

    # Validate mafia minimum
    if req.role == ROLE_MAFIA and req.count < 1:
        raise HTTPException(status_code=400, detail="Мафия должна быть минимум 1")

    if req.count == 0:
        g.role_counts.pop(req.role, None)
    else:
        g.role_counts[req.role] = req.count

    g.stage = Stage.EDIT_ROLES

    return {"message": f"Роль {req.role}: {req.count}", "roles_sum": roles_sum(g)}


@app.post("/api/game/{game_id}/set_stage")
def set_stage(game_id: str, stage: str):
    """Set game stage (for navigation)"""
    g = get_game(game_id)

    try:
        new_stage = Stage(stage)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Неизвестный этап: {stage}")

    g.stage = new_stage
    return {"message": f"Этап: {new_stage}", "stage": new_stage}


@app.post("/api/game/{game_id}/validate_start")
def validate_start(game_id: str):
    """Validate if game can start"""
    g = get_game(game_id)
    ok, msg = role_constraints_ok(g)
    return {"valid": ok, "message": msg}


@app.post("/api/game/{game_id}/start")
def start_game(game_id: str):
    """Start the game (begin Night 0 - role binding)"""
    g = get_game(game_id)

    ok, msg = role_constraints_ok(g)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)

    # Reset runtime state
    g.day = 0
    g.night = 0
    g.skip_vote_day = None
    g.undo_stack = []

    g.night_choices = NightChoices()
    g.night_steps = []
    g.night_step_index = 0
    g.pending_step = None

    g.last_boss_intimidate = None
    g.last_doctor = None
    g.last_courtesan = None
    g.last_seer = None
    g.last_monk_first = None
    g.last_commissioner = None

    g.avenger_pending = None
    g.mayor_name = None
    g.successor_name = None
    g.protected_from_vote_day = {}
    g.log_lines = ["Ночь 0: привязка ролей началась."]

    for p in g.players.values():
        p.alive = True
        p.role = None
        p.is_mayor = False
        p.is_successor = False

    # Setup binding
    g.bind_remaining = copy.deepcopy(g.role_counts)
    g.bind_available_players = sorted(list(g.players.keys()))
    g.bind_stack = []
    g.bind_selected_role = None

    g.stage = Stage.NIGHT0_BIND_ROLE

    return {"message": "Ночь 0 началась", "stage": g.stage}


@app.post("/api/game/{game_id}/bind_role")
def bind_role(game_id: str, req: BindRoleRequest):
    """Select a role to bind (Night 0)"""
    g = get_game(game_id)

    if g.stage != Stage.NIGHT0_BIND_ROLE:
        raise HTTPException(status_code=400, detail="Неверный этап")

    if g.bind_remaining.get(req.role, 0) <= 0:
        raise HTTPException(status_code=400, detail="Эта роль уже занята")

    g.bind_selected_role = req.role
    g.stage = Stage.NIGHT0_BIND_PLAYER

    return {"message": f"Выбрана роль: {req.role}", "stage": g.stage}


@app.post("/api/game/{game_id}/bind_player")
def bind_player(game_id: str, req: BindPlayerRequest):
    """Bind selected role to a player (Night 0)"""
    g = get_game(game_id)

    if g.stage != Stage.NIGHT0_BIND_PLAYER:
        raise HTTPException(status_code=400, detail="Неверный этап")

    role = g.bind_selected_role
    name = req.player_name

    if not role or name not in g.bind_available_players:
        raise HTTPException(status_code=400, detail="Недоступно")

    g.players[name].role = role
    g.bind_available_players.remove(name)
    g.bind_remaining[role] -= 1
    g.bind_stack.append((name, role))
    g.log_lines.append(f"Ночь 0: {name} → {role}")
    g.bind_selected_role = None

    # Check if binding is complete
    if sum(g.bind_remaining.values()) == 0 and len(g.bind_available_players) == 0:
        g.stage = Stage.MAYOR_SELECT
        g.log_lines.append("Ночь 0: привязка завершена.")
        return {"message": "Привязка завершена. Выберите мэра.", "stage": g.stage, "binding_complete": True}

    g.stage = Stage.NIGHT0_BIND_ROLE
    return {"message": f"{name} → {role}", "stage": g.stage, "binding_complete": False}


@app.post("/api/game/{game_id}/bind_undo")
def bind_undo(game_id: str):
    """Undo last role binding (Night 0)"""
    g = get_game(game_id)

    if g.stage not in [Stage.NIGHT0_BIND_ROLE, Stage.NIGHT0_BIND_PLAYER]:
        raise HTTPException(status_code=400, detail="Неверный этап")

    if not g.bind_stack:
        raise HTTPException(status_code=400, detail="Нечего отменять")

    name, role = g.bind_stack.pop()
    g.players[name].role = None
    g.bind_available_players.append(name)
    g.bind_available_players.sort()
    g.bind_remaining[role] += 1
    g.bind_selected_role = None
    g.stage = Stage.NIGHT0_BIND_ROLE
    g.log_lines.append(f"Ночь 0: ОТМЕНА {name} → {role}")

    return {"message": "Отменено", "stage": g.stage}


@app.post("/api/game/{game_id}/select_mayor")
def select_mayor(game_id: str, req: SelectMayorRequest):
    """Select the mayor"""
    g = get_game(game_id)

    if g.stage != Stage.MAYOR_SELECT:
        raise HTTPException(status_code=400, detail="Неверный этап")

    name = req.player_name
    if name not in g.players or not g.players[name].alive:
        raise HTTPException(status_code=400, detail="Недоступно")

    g.mayor_name = name
    g.players[name].is_mayor = True
    g.day = 1
    g.protected_from_vote_day[name] = 1
    g.log_lines.append(f"Ночь 0: мэр → {name} (защита от голосования День 1)")

    g.stage = Stage.SUCCESSOR_SELECT

    return {"message": f"Мэр: {name}", "stage": g.stage}


@app.post("/api/game/{game_id}/select_successor")
def select_successor(game_id: str, req: SelectSuccessorRequest):
    """Select the mayor's successor"""
    g = get_game(game_id)

    if g.stage != Stage.SUCCESSOR_SELECT:
        raise HTTPException(status_code=400, detail="Неверный этап")

    name = req.player_name
    if name == g.mayor_name or name not in g.players or not g.players[name].alive:
        raise HTTPException(status_code=400, detail="Недоступно")

    g.successor_name = name
    g.players[name].is_successor = True
    g.log_lines.append(f"Ночь 0: преемник → {name}")

    g.stage = Stage.DAY_MENU

    return {"message": f"Преемник: {name}. Игра началась!", "stage": g.stage}


@app.post("/api/game/{game_id}/day_vote_start")
def day_vote_start(game_id: str):
    """Start day voting"""
    g = get_game(game_id)

    if g.stage != Stage.DAY_MENU:
        raise HTTPException(status_code=400, detail="Неверный этап")

    if g.skip_vote_day == g.day:
        raise HTTPException(status_code=400, detail="Сегодня голосования нет (траур)")

    g.push_undo()
    g.stage = Stage.DAY_VOTE_PICK

    return {"message": f"День {g.day}: голосование", "stage": g.stage}


@app.post("/api/game/{game_id}/day_vote")
def day_vote(game_id: str, req: VoteRequest):
    """Vote to eliminate a player during the day"""
    g = get_game(game_id)

    if g.stage != Stage.DAY_VOTE_PICK:
        raise HTTPException(status_code=400, detail="Неверный этап")

    name = req.target
    if name not in g.players or not g.players[name].alive:
        raise HTTPException(status_code=400, detail="Недоступно")

    # Check if protected
    if g.protected_from_vote_day.get(name) == g.day:
        raise HTTPException(status_code=400, detail="Этот игрок защищён от голосования сегодня")

    g.players[name].alive = False
    role = g.players[name].role or "неизвестно"
    g.log_lines.append(f"День {g.day}: голосованием убит {name} ({role})")

    handle_mayor_death(g, name)

    # Check for Banshee (cancels night)
    if role == ROLE_BANSHEE and not special_threshold_blocks(g):
        g.day += 1
        g.stage = Stage.DAY_MENU

        result = check_end(g)
        if result:
            g.stage = Stage.END
            g.log_lines.append(f"Итог: {result}")
            return {
                "message": f"{name} убит ({role}). Банши: ночь отменена.",
                "stage": g.stage,
                "game_ended": True,
                "end_result": result,
                "special": "banshee_no_night",
            }

        return {
            "message": f"{name} убит ({role}). Банши: ночь отменена. День {g.day}",
            "stage": g.stage,
            "game_ended": False,
            "special": "banshee_no_night",
        }

    # Check for Avenger (revenge)
    if role == ROLE_AVENGER:
        g.avenger_pending = name
        g.stage = Stage.AVENGER_REVENGE_PICK
        return {
            "message": f"{name} убит ({role}). Мститель выбирает цель.",
            "stage": g.stage,
            "game_ended": False,
            "special": "avenger_revenge",
        }

    # Check game end
    result = check_end(g)
    if result:
        g.stage = Stage.END
        g.log_lines.append(f"Итог: {result}")
        return {
            "message": f"{name} убит ({role})",
            "stage": g.stage,
            "game_ended": True,
            "end_result": result,
        }

    # Check final threshold (2 peaceful + 1 mafia = no night)
    mafia = len(g.mafia_alive_names())
    peace = len(g.peace_alive_names())
    total = len(g.alive_names())

    if total == 3 and mafia == 1 and peace == 2:
        g.log_lines.append(f"День {g.day}: осталось 3 (2 мирных + 1 мафия) — ночь отменена.")
        g.day += 1
        g.stage = Stage.DAY_MENU

        result2 = check_end(g)
        if result2:
            g.stage = Stage.END
            g.log_lines.append(f"Итог: {result2}")
            return {
                "message": f"{name} убит ({role}). Финал: ночь отменена.",
                "stage": g.stage,
                "game_ended": True,
                "end_result": result2,
                "special": "final_threshold",
            }

        return {
            "message": f"{name} убит ({role}). Финал: ночь отменена. День {g.day}",
            "stage": g.stage,
            "game_ended": False,
            "special": "final_threshold",
        }

    # Transition to night
    return begin_night_internal(g, f"{name} убит ({role})")


@app.post("/api/game/{game_id}/avenger_revenge")
def avenger_revenge(game_id: str, req: RevengeRequest):
    """Avenger selects revenge target"""
    g = get_game(game_id)

    if g.stage != Stage.AVENGER_REVENGE_PICK:
        raise HTTPException(status_code=400, detail="Неверный этап")

    target = req.target
    if target not in g.players or not g.players[target].alive:
        raise HTTPException(status_code=400, detail="Недоступно")

    if target == g.avenger_pending:
        raise HTTPException(status_code=400, detail="Нельзя выбрать себя")

    g.players[target].alive = False
    role_t = g.players[target].role or "неизвестно"
    g.log_lines.append(f"День {g.day}: месть — убит {target} ({role_t})")

    handle_mayor_death(g, target)
    g.avenger_pending = None

    # Check game end
    result = check_end(g)
    if result:
        g.stage = Stage.END
        g.log_lines.append(f"Итог: {result}")
        return {
            "message": f"Месть: {target} убит ({role_t})",
            "stage": g.stage,
            "game_ended": True,
            "end_result": result,
        }

    # Transition to night
    return begin_night_internal(g, f"Месть: {target} убит ({role_t})")


def begin_night_internal(g: Game, prefix: str = "") -> dict:
    """Internal function to begin night phase"""
    g.night += 1
    g.stage = Stage.NIGHT_MENU
    g.undo_stack = []
    g.push_undo()

    g.night_choices = NightChoices()
    g.night_steps = build_night_steps(g)
    g.night_step_index = 0
    g.pending_step = None

    return {
        "message": f"{prefix} Наступает ночь {g.night}.",
        "stage": g.stage,
        "game_ended": False,
        "night": g.night,
    }


@app.post("/api/game/{game_id}/skip_to_night")
def skip_to_night(game_id: str):
    """Skip day voting (mourning) and go to night"""
    g = get_game(game_id)

    if g.stage != Stage.DAY_MENU:
        raise HTTPException(status_code=400, detail="Неверный этап")

    if g.skip_vote_day != g.day:
        raise HTTPException(status_code=400, detail="Сегодня голосование есть")

    return begin_night_internal(g, "Траур: голосования нет.")


@app.post("/api/game/{game_id}/night_action")
def night_action(game_id: str, req: NightActionRequest):
    """Perform a night action"""
    g = get_game(game_id)

    if g.stage != Stage.NIGHT_MENU:
        raise HTTPException(status_code=400, detail="Неверный этап")

    if g.night_step_index >= len(g.night_steps):
        raise HTTPException(status_code=400, detail="Все шаги выполнены")

    step = g.night_steps[g.night_step_index]
    g.push_undo()

    result_message = ""

    if step == "mafia_kill":
        if not req.target:
            raise HTTPException(status_code=400, detail="Выберите цель")
        g.night_choices.mafia_target = req.target
        result_message = f"Мафия выбрала: {req.target}"

    elif step == "boss_intimidate":
        if not req.target:
            raise HTTPException(status_code=400, detail="Выберите цель")
        g.night_choices.boss_intimidate = req.target
        # Apply intimidation immediately
        g.protected_from_vote_day[req.target] = g.day + 1
        result_message = f"Босс запугал: {req.target}"

    elif step == "maniac_kill":
        if not req.target:
            raise HTTPException(status_code=400, detail="Выберите цель")
        g.night_choices.maniac_target = req.target
        result_message = f"Маньяк выбрал: {req.target}"

    elif step == "commissioner_check":
        if not req.target:
            raise HTTPException(status_code=400, detail="Выберите цель")
        g.night_choices.commissioner_target = req.target
        answer = commissioner_answer_for(g, req.target)
        g.last_commissioner = req.target
        result_message = f"Комиссар проверил {req.target}: {answer}"

    elif step == "monk_first":
        if not req.target:
            raise HTTPException(status_code=400, detail="Выберите цель")
        g.night_choices.monk_first = req.target
        g.last_monk_first = req.target
        result_message = f"Монах (1-е): {req.target}"

    elif step == "monk_second":
        if not req.target:
            raise HTTPException(status_code=400, detail="Выберите цель")
        g.night_choices.monk_second = req.target
        result_message = f"Монах (2-е): {req.target}"

    elif step == "doctor_heal":
        if not req.target:
            raise HTTPException(status_code=400, detail="Выберите цель")
        g.night_choices.doctor_target = req.target
        g.last_doctor = req.target
        result_message = f"Доктор лечит: {req.target}"

    elif step == "courtesan_visit":
        if not req.target:
            raise HTTPException(status_code=400, detail="Выберите цель")
        g.night_choices.courtesan_client = req.target
        g.last_courtesan = req.target
        result_message = f"Куртизанка идёт к: {req.target}"

    elif step == "seer_divine":
        if not req.target:
            raise HTTPException(status_code=400, detail="Выберите цель")
        g.night_choices.seer_target = req.target
        g.last_seer = req.target
        result_message = f"Гадалка выбрала: {req.target}"

    elif step == "rat_wants":
        if req.choice is None:
            raise HTTPException(status_code=400, detail="Сделайте выбор")
        g.night_choices.rat_wants = req.choice
        result_message = f"Крыса хочет стать мафией: {'ДА' if req.choice else 'НЕТ'}"

    elif step == "mafia_wants_rat":
        if req.choice is None:
            raise HTTPException(status_code=400, detail="Сделайте выбор")
        g.night_choices.mafia_wants_rat = req.choice
        result_message = f"Мафия хочет крысу: {'ДА' if req.choice else 'НЕТ'}"

    else:
        raise HTTPException(status_code=400, detail=f"Неизвестный шаг: {step}")

    # Advance to next step
    g.night_step_index += 1

    return {
        "message": result_message,
        "stage": g.stage,
        "step_completed": step,
        "steps_remaining": len(g.night_steps) - g.night_step_index,
    }


@app.post("/api/game/{game_id}/finish_night")
def finish_night(game_id: str):
    """Finish the night and apply all actions"""
    g = get_game(game_id)

    if g.stage != Stage.NIGHT_MENU:
        raise HTTPException(status_code=400, detail="Неверный этап")

    if g.night_step_index < len(g.night_steps):
        raise HTTPException(status_code=400, detail="Сначала выполните все ночные шаги")

    c = g.night_choices

    # Handle rat transformation
    if len(g.mafia_alive_names()) == 1 and g.role_alive_exists(ROLE_RAT):
        if c.rat_wants is not None and c.mafia_wants_rat is not None:
            if c.rat_wants and c.mafia_wants_rat:
                rat_name = g.get_role_owner(ROLE_RAT)
                if rat_name:
                    g.players[rat_name].role = ROLE_RAT_MAFIA
                    g.log_lines.append(f"Ночь {g.night}: крыса {rat_name} стала {ROLE_RAT_MAFIA}")
            else:
                g.log_lines.append(f"Ночь {g.night}: крыса не стала мафией")

    # Apply night actions
    deaths, summary = apply_night_and_get_deaths(g)

    # Log night actions
    for s in summary:
        g.log_lines.append(f"Ночь {g.night}: {s}")

    # Process deaths
    killed_names = []
    for name in deaths:
        if name in g.players and g.players[name].alive:
            g.players[name].alive = False
            role = g.players[name].role or "неизвестно"
            killed_names.append(f"{name} ({role})")
            g.log_lines.append(f"Ночь {g.night}: убит {name} ({role})")
            handle_mayor_death(g, name)

    # Check for Duke (mourning next day)
    if not special_threshold_blocks(g):
        for name in deaths:
            if name in g.players and g.players[name].role == ROLE_DUKE:
                g.skip_vote_day = g.day + 1
                g.log_lines.append(f"Ночь {g.night}: Герцог убит — траур в день {g.skip_vote_day}")
                break

    # Check game end
    result = check_end(g)
    killed_text = ", ".join(killed_names) if killed_names else "никто не умер"

    if result:
        g.stage = Stage.END
        g.log_lines.append(f"Итог: {result}")
        return {
            "message": f"Ночь {g.night}: {killed_text}",
            "stage": g.stage,
            "game_ended": True,
            "end_result": result,
            "deaths": killed_names,
            "summary": summary,
        }

    # Transition to day
    g.day += 1
    g.stage = Stage.DAY_MENU

    return {
        "message": f"Ночь {g.night}: {killed_text}. Наступает день {g.day}",
        "stage": g.stage,
        "game_ended": False,
        "deaths": killed_names,
        "summary": summary,
        "is_mourning": g.skip_vote_day == g.day,
    }


@app.post("/api/game/{game_id}/undo")
def undo_action(game_id: str):
    """Undo last action"""
    g = get_game(game_id)

    if not g.pop_undo():
        raise HTTPException(status_code=400, detail="Нечего отменять")

    return {"message": "Отменено", "stage": g.stage}


@app.post("/api/game/{game_id}/reset")
def reset_game(game_id: str):
    """Reset game to lobby"""
    g = get_game(game_id)

    # Keep game_id and host_id
    host_id = g.host_id

    # Create new game state
    new_g = Game(game_id=game_id, host_id=host_id, stage=Stage.LOBBY)
    init_default_roles(new_g)

    GAMES[game_id] = new_g

    return {"message": "Игра сброшена", "stage": Stage.LOBBY}


@app.delete("/api/game/{game_id}")
def delete_game(game_id: str):
    """Delete a game"""
    if game_id in GAMES:
        del GAMES[game_id]
        return {"message": "Игра удалена"}
    raise HTTPException(status_code=404, detail="Игра не найдена")
