import s_taper
from s_taper.consts import *

schema = {
    "user_id": INT + KEY,
    "name": TEXT,
    "race": TEXT,
    "hp": INT,
    "dmg": INT,
    "lvl": INT,
    "exp": INT
}
db = s_taper.Taper("users", "data.db").create_table(schema)
races = {
    "human": (100, 25),
    "goblin": (80, 30),
    "elf": (120, 20)

}
schema1 = {
    "user_id": INT + KEY,
    "food": TEXT,
}
heal = s_taper.Taper("food", "data.db").create_table(schema1)
