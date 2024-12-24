import random
import time
import datetime
import asyncio

from telebot.types import Message, ReplyKeyboardMarkup as rkm, ReplyKeyboardRemove as rkr, InlineKeyboardMarkup as ikm, \
    InlineKeyboardButton as ikb, CallbackQuery as cbq
from database import *

from config import TOKEN
import telebot

bot = telebot.TeleBot(TOKEN)
temp = {}
clear = rkr()


class Enemy:
    enemies_1 = {
        "ogre": (100, 25, 20),
        "taskar": (120, 25, 25)
    }

    enemies_2 = {
        "muha": (130, 35, 40),
        "ilya": (150, 40, 50)
    }

    def __init__(self, hero_lvl):
        self.lvl = hero_lvl
        if self.lvl < 5:
            self.name = random.choice(list(self.enemies_1))
            self.hp = self.enemies_1[self.name][0]
            self.dmg = self.enemies_1[self.name][1]
            self.exp = self.enemies_1[self.name][2]
        elif self.lvl in range(5, 11):
            self.name = random.choice(list(self.enemies_2))
            self.hp = self.enemies_2[self.name][0]
            self.dmg = self.enemies_2[self.name][1]
            self.exp = self.enemies_2[self.name][2]


@bot.message_handler(commands=["start"])
def start(m: Message):
    if is_new_player(m):
        temp[m.chat.id] = {}
        register(m)
    else:
        menu(m)


@bot.message_handler(["menu"])
def menu(m: Message):
    try:
        print(temp[m.chat.id])
    except KeyError:
        temp[m.chat.id] = {}
    txt = "Что будешь делать?\n/square - идём на главную площадь\n/home - путь домой\n/stats - статистика"
    bot.send_message(m.chat.id, txt, reply_markup=clear)


@bot.message_handler(["home"])
def home(m: Message):
    kb = rkm(True, True)
    kb.row("Пополнить ХП", "Передохнуть")
    bot.send_message(m.chat.id, "Ты дома, выбирай, чем хочешь заняться)", reply_markup=kb)
    bot.register_next_step_handler(m, reg3)


@bot.message_handler(["stats"])
def stats(m: Message):
    player = db.read("user_id", m.chat.id)
    txt = f"имя:{player[1]} раса:{player[2]}\nхп:{player[3]} урон:{player[4]}\nлвл:{player[5]} опыт:{player[6]}"
    bot.send_message(m.chat.id, txt)
    asyncio.run(asyncio.sleep(3))
    menu(m)
    return


@bot.message_handler(["square"])
def square(m: Message):
    kb = rkm(True, True)
    kb.row("тренировка", "испытание ловкости", "пойти в бой")
    bot.send_message(m.chat.id, "Ты на площади, выбирай, чем хочешь заняться)", reply_markup=kb)
    bot.register_next_step_handler(m, reg4)


@bot.message_handler(["add_heal"])
def add_heal(m: Message):
    id, food = heal.read("user_id", m.chat.id)
    food["торт"] = [2, 20]
    heal.write([id, food])
    bot.send_message(m.chat.id, "Еда выдана)")


@bot.callback_query_handler(func=lambda call: True)
def callback(call: cbq):
    print(call.data)
    if call.data.startswith("food_"):
        a = call.data.split("_")
        eating(call.message, a[1], a[2])
        player = db.read("user_id", call.message.chat.id)
        bot.answer_callback_query(call.id, f"ты пополнил здоровье!\nтеперь у тебя {player[3]}❤", show_alert=True)
        kb = ikm()
        id, food = heal.read("user_id", call.message.chat.id)
        if food == {}:
            bot.send_message(call.message.chat.id,
                             "Еды нет, воспользуйся командой /add_heal что бы восстановить здоровье",
                             reply_markup=clear)
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)
            menu(call.message)
            return
        for key in food:
            kb.row(ikb(f"{key} - {food[key][0]}шт. {food[key][1]}❤", callback_data=f"food_{key}_{food[key][1]}"))
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=kb)
    if call.data.startswith("sleep_"):
        a = call.data.split("_")
        t = int(a[1]) / 4
        bot.send_message(call.message.chat.id, f"ты лег спать на {t} секунд")
        asyncio.run(asyncio.sleep(t))
        sleeping(call.message, a[1])
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, "ты выспался и восстановил хп")
        menu(call.message)
        return
    if call.data == "menu":
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)
        menu(call.message)
        return
    if call.data == "workout":
        player = db.read("user_id", call.message.chat.id)
        player[4] += player[5] / 10
        player[4] = round(player[4], 1)
        db.write(player)
        bot.answer_callback_query(call.id, f"ты тренируешься, теперь твой урон {player[4]}", True)


def eat(m: Message):
    kb = ikm()
    id, food = heal.read("user_id", m.chat.id)
    if food == {}:
        bot.send_message(m.chat.id, "Еды нет, воспользуйся командой /add_heal что бы восстановить здоровье",
                         reply_markup=clear)
        menu(m)
        return
    for key in food:
        if food[key][0] > 0:
            kb.row(ikb(f"{key} - {food[key][0]}шт. {food[key][1]}❤", callback_data=f"food_{key}_{food[key][1]}"))
    bot.send_message(m.chat.id, "выбирай что хочешь поесть", reply_markup=kb)


def eating(m: Message, food_type, hp):
    id, food = heal.read("user_id", m.chat.id)
    player = db.read("user_id", m.chat.id)
    if food[food_type][0] == 1:
        del food[food_type]
    else:
        food[food_type][0] -= 1
    heal.write([id, food])
    player[3] += int(hp)
    db.write(player)
    print("игрок поел")


def sleep(m: Message):
    player = db.read("user_id", m.chat.id)
    low = int(races[player[2]][0] + 20 * (player[5] - 1)) // 2 - player[3]
    high = int(races[player[2]][0] + 20 * (player[5] - 1)) - player[3]
    kb = ikm()
    if low > 0:
        kb.row(ikb(f"вздремнуть +{low}хп", callback_data=f"sleep_{low}"))
    if high > 0:
        kb.row(ikb(f"поспать +{high}хп", callback_data=f"sleep_{high}"))
    if len(kb.keyboard) == 0:
        kb.row(ikb("Спать не хочется", callback_data="menu"))
    bot.send_message(m.chat.id, text="сколько хочешь спать?", reply_markup=kb)


def sleeping(m: Message, hp):
    player = db.read("user_id", m.chat.id)
    player[3] += int(hp)
    db.write(player)
    print("игрок поспал")


def workout(m: Message):
    kb = ikm()
    kb.row(ikb("тренироваться", callback_data="workout"))
    kb.row(ikb("назад", callback_data="menu"))
    bot.send_message(m.chat.id, text="жми тренироваться", reply_markup=kb)


def block(m: Message):
    try:
        print(temp[m.chat.id])
    except KeyError:
        temp[m.chat.id] = {}
    try:
        print(temp[m.chat.id]["win"])
    except KeyError:
        temp[m.chat.id]["win"] = 0
    bot.send_message(m.chat.id, "приготовься к атаке!", reply_markup=clear)
    asyncio.run(asyncio.sleep(2))
    sides = ["слева", "справа", "сверху", "снизу"]
    random.shuffle(sides)
    kb = rkm(resize_keyboard=True, one_time_keyboard=True)
    kb.row(sides[0], sides[1])
    kb.row(sides[2], sides[3])
    side = random.choice(sides)
    bot.send_message(m.chat.id, f"защищайся удар {side}", reply_markup=kb)
    temp[m.chat.id]["start"] = datetime.datetime.now().timestamp()
    bot.register_next_step_handler(m, block_handler, side)


def block_handler(m: Message, side):
    temp[m.chat.id]["finish"] = datetime.datetime.now().timestamp()
    if temp[m.chat.id]["finish"] - temp[m.chat.id]["start"] > 3:
        temp[m.chat.id]["win"] = 0
        bot.send_message(m.chat.id, "ты не успел! начинай заново", reply_markup=clear)
        asyncio.run(asyncio.sleep(2))
        menu(m)
        return
    else:
        if side != m.text:
            temp[m.chat.id]["win"] = 0
            bot.send_message(m.chat.id, "ты неправильно отразил атаку! начинай заново", reply_markup=clear)
            asyncio.run(asyncio.sleep(2))
            menu(m)
            return
        else:
            temp[m.chat.id]["win"] += 1
            if temp[m.chat.id]["win"] < 5:
                bot.send_message(m.chat.id, "ты справился! продолжай!", reply_markup=clear)
                asyncio.run(asyncio.sleep(2))
                block(m)
                return
            else:
                temp[m.chat.id]["win"] = 0
                player = db.read("user_id", m.chat.id)
                player[6] += 50
                db.write(player)
                bot.send_message(m.chat.id, "Молодец!!! ты прошел испытание")
                bot.send_message(m.chat.id, "+50 exp")
                exp_check(m)
                menu(m)
                return


def exp_check(m: Message):
    player = db.read("user_id", m.chat.id)
    exp = player[6]
    max_exp = 100 + ((player[5] - 1) * 100 * 0.1)
    if exp >= max_exp:
        player[6] -= max_exp
        player[3] = (races[player[2]][0] + ((player[5] - 1) * races[player[2]][0] * 0.1)) + races[player[2]][0] * 0.1
        player[4] += 5
        player[5] += 1
        db.write(player)
        bot.send_message(m.chat.id, f"Поздравляю! Ты повысил уровень, теперь у тебя уровень {player[5]}")
    return


def fight(m: Message):
    bot.send_message(m.chat.id, "Ты отправляешься на арену")
    asyncio.run(asyncio.sleep(2))
    new_Enemy(m)


def new_Enemy(m: Message):
    player = db.read("user_id", m.chat.id)
    enemy = Enemy(player[5])
    kb = rkm(resize_keyboard=True, one_time_keyboard=True)
    kb.row("Сражаться", "Сбежать")
    bot.send_message(m.chat.id, f"твой враг {enemy.name}, hp:{enemy.hp} dmg:{enemy.dmg}. Готовы сразиться?",
                     reply_markup=kb)
    bot.register_next_step_handler(m, fight_handler, enemy, kb)


def fight_handler(m: Message, enemy: Enemy, kb):
    if m.text == "Сражаться":
        attack(m, enemy)
    elif m.text == "Сбежать":
        home(m)
    else:
        bot.send_message(m.chat.id, "Нажми на кнопку!", reply_markup=kb)
        bot.register_next_step_handler(m, fight_handler, enemy, kb)


def attack(m: Message, enemy: Enemy):
    asyncio.run(asyncio.sleep(2))
    if hero_attack(m, enemy):
        if enemy_attack(m, enemy):
            attack(m, enemy)
    else:
        exp_check(m)
        enemy = None
        new_Enemy(m)


def hero_attack(m: Message, enemy: Enemy):
    player = db.read("user_id", m.chat.id)
    enemy.hp -= player[4]
    if enemy.hp <= 0:
        bot.send_message(m.chat.id, "Ты победил!")
        player[-1] += enemy.exp
        db.write(player)
        return False
    else:
        bot.send_message(m.chat.id, f"У врага осталось {enemy.hp} хп")
        return True


def enemy_attack(m: Message, enemy: Enemy):
    player = db.read("user_id", m.chat.id)
    player[3] -= enemy.dmg
    if player[3] <= 0:
        player[3] = 1
        db.write(player)
        bot.send_message(m.chat.id, "Ты проиграл, восстанови хп и иди снова в бой!")
        menu(m)
        return
    else:
        db.write(player)
        bot.send_message(m.chat.id, f"У тебя осталось {player[3]} хп")
        return True


def is_new_player(m: Message):
    player = db.read_all()
    for play in player:
        if play[0] == m.chat.id:
            return False
    return True


def register(m: Message):
    bot.send_message(m.chat.id, "Добро пожаловать в игру! Введите свое имя ")
    bot.register_next_step_handler(m, reg1)


def reg1(m: Message):
    temp[m.chat.id]["name"] = m.text
    kb = rkm(resize_keyboard=True, one_time_keyboard=True)
    for key in races:
        kb.row(key)
    bot.send_message(m.chat.id, text="Окей, теперь выбери расу", reply_markup=kb)
    bot.register_next_step_handler(m, reg2)


def reg2(m: Message):
    temp[m.chat.id]["race"] = m.text
    hp, damage = races[m.text]
    db.write([m.chat.id, temp[m.chat.id]["name"], temp[m.chat.id]["race"], hp, damage, 1, 0])
    heal.write([m.chat.id, {}])
    print("пользователь добавлен в db")
    time.sleep(2)
    menu(m)


def reg3(m: Message):
    if m.text == "Пополнить ХП":
        eat(m)
    elif m.text == "Передохнуть":
        sleep(m)
    else:
        bot.send_message(m.chat.id, "надо было нажимать на кнопки", reply_markup=clear)
        menu(m)
        return


def reg4(m: Message):
    if m.text == "тренировка":
        workout(m)
    elif m.text == "испытание ловкости":
        block(m)
    elif m.text == "пойти в бой":
        fight(m)
    else:
        bot.send_message(m.chat.id, "надо было нажимать на кнопки", reply_markup=clear)
        menu(m)
        return


bot.infinity_polling()
