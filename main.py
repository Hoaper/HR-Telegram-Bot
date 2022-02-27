from aiogram import types, executor, Dispatcher, Bot
from dotenv import load_dotenv
from colorama import Fore, Style
import os, json
import sqlite3
from config import *

# PATHS
path_env = os.path.join(os.path.dirname(__file__), ".env")
path_langs = os.path.join(os.path.dirname(__file__), "db", "langs.db")
path_data = os.path.join(os.path.dirname(__file__), "db", "data.db")
path_locales = os.path.join(os.path.dirname(__file__), "locales.json")
path_questions = os.path.join(os.path.dirname(__file__), "questions.json")

supported_langs = {
    "🇷🇺 Русский 🇷🇺": "ru",
    # "🇺🇸 English 🇺🇸": "eng",
    "🇺🇿 Узбекский 🇺🇿": "uzb"
}

output_lang_id = "uzb"

# Load env
if os.path.exists(path_env):
    load_dotenv(path_env)

# DB inits
db_data = sqlite3.connect(path_data)
db_langs = sqlite3.connect(path_langs)

# Cursors
cur_data = db_data.cursor()
cur_langs = db_langs.cursor()

# Tables creating
cur_data.execute("""CREATE TABLE IF NOT EXISTS data(
    id INTEGER PRIMARY KEY,
    chat_id INTEGER,
    answers TEXT,
    company TEXT,
    status VARCHAR
);""")
cur_langs.execute("""CREATE TABLE IF NOT EXISTS language(
    id INTEGER PRIMARY KEY,
    chat_id INTEGER,
    lang_id VARCHAR
);""")
db_data.commit()
db_langs.commit()

# Exception
class NoLanguage(Exception):
    pass

# Locales
def getLocale(lang_id: str) -> dict:

    with open(path_locales, "r") as f:
        return json.load(f)[lang_id]

def getLangID(msg: types.Message) -> str:

    cur_langs.execute("SELECT lang_id FROM language WHERE chat_id=?", (msg.chat.id, ))
    try:
        data = cur_langs.fetchone()[0]
        return data
    except:
        raise NoLanguage()

# Statuses
def checkStatus(msg: types.Message, status: str) -> bool:
    
    try:
        return getStatus(msg) == status
    
    except:
        return False

def setStatus(msg: types.Message, status: str) -> bool:

    cur_data.execute("SELECT * FROM data WHERE chat_id=?", (msg.chat.id, ))
    
    if cur_data.fetchone():

        cur_data.execute("UPDATE data SET status=? WHERE chat_id=?", (status, msg.chat.id))
    else:
        cur_data.execute("INSERT INTO data(chat_id, status) VALUES(?, ?)", (msg.chat.id, status))

    db_data.commit()

def getStatus(msg: types.Message):
    try:
        cur_data.execute("SELECT status FROM data WHERE chat_id=?", (msg.chat.id, ))
        return cur_data.fetchone()[0]
    except:
        return

# no comms
def getLocaledQuestions(lang_id: str, company="Basic") -> list:

    with open(path_questions, "r") as f:
        return json.load(f)[company][lang_id]

def getAnswers(msg: types.Message) -> dict:
    try:
        cur_data.execute("SELECT answers FROM data where chat_id=?", (msg.chat.id, ))
        fetched = cur_data.fetchone()[0]
        return json.loads(fetched)

    except Exception as e:
        return {}

def addAnswers(answers, msg: types.Message, _type, index) -> dict:
    try:
            answers[_type][index-1] = msg.text
    except Exception as e:
        try:
            answers[_type].append(msg.text)
        except Exception as e:
            answers[_type] = []
            answers[_type].append(msg.text)

    return answers

def getQuestions() -> dict:
    with open(path_questions, "r") as f:
        return json.load(f)

# DB Manipulating
def removeFromData(msg: types.Message):
    cur_data.execute("DELETE FROM data WHERE chat_id=?", (msg.chat.id, ))
    db_data.commit()

# Checks
def checkLocaleSelected(msg: types.Message) -> bool:

    return msg.text in supported_langs.keys()

def checkSettingsLocale(msg: types.Message) -> bool:
    try:
        locale = getLocale(getLangID(msg))
        return locale['keyboards']['settings'] == msg.text
    except:
        return False

def checkBackLocale(msg: types.Message) -> bool:
    
    try:
        locale = getLocale(getLangID(msg))
        return msg.text == locale['keyboards']['back']

    except:
        return False

def checkNextLocale(msg: types.Message) -> bool:
    try:
        locale = getLocale(getLangID(msg))
        return locale['keyboards']['next'] == msg.text
    except:
        return False

def checkResumeLocale(msg: types.Message) -> bool:
    try:
        locale = getLocale(getLangID(msg))
        return locale['keyboards']['start'] == msg.text
    except:
        return False

def checkStartPoll(msg: types.Message) -> bool:
    try:
        locale = getLocale(getLangID(msg))
        kb = locale['keyboards']['start_poll']
        return msg.text == kb
    except:
        return False

def checkPollingStatus(msg: types.Message) -> bool:
    try:
        status = getStatus(msg)
        return "polling" in status
    except:
        return False

def checkAnswerProcessor(msg: types.Message):
    return checkPollingStatus(msg) and not checkBackLocale(msg)

# Bot init
bot = Bot(os.getenv("TOKEN"))
dp = Dispatcher(bot)

# Handlers
@dp.message_handler(commands=['start', 'lang', 'language'])
async def select_language(msg: types.Message):
    removeFromData(msg)
    kb = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    for lang in supported_langs.keys():

        kb.insert(
            types.KeyboardButton(lang)
        )

    await msg.answer("Пожалуйста, выберите язык", reply_markup=kb)

@dp.message_handler(checkLocaleSelected)
async def save_lang_id(msg: types.Message):
    cur_langs.execute("SELECT id FROM language WHERE chat_id=?", (msg.chat.id, ))
    lang_id=supported_langs[msg.text]
    try:
        fetched = cur_langs.fetchone()[0]
        cur_langs.execute(
            "UPDATE language SET lang_id=? WHERE id=?", 
            (lang_id, fetched)
        )
    except:
        cur_langs.execute(
            "INSERT INTO language(chat_id, lang_id) VALUES(?, ?)",
            (msg.chat.id, lang_id)
            )
    finally:
        db_langs.commit()

        await show_menu(msg)
        return

@dp.message_handler(commands=['menu'])
async def show_menu(msg: types.Message):
    removeFromData(msg)
    try:
        locale = getLocale(getLangID(msg))
        
        kb = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        kb.row(
            types.KeyboardButton(locale['keyboards']['settings']),
            types.KeyboardButton(locale['keyboards']['start'])
        )

        await msg.answer(text=locale['welcome'], reply_markup=kb)

    except NoLanguage:

        await select_language(msg)

@dp.message_handler(checkSettingsLocale)
async def settings_panel(msg: types.Message):
    locale = getLocale(getLangID(msg))

    kb = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    kb.insert(
        types.KeyboardButton("/lang")
    )
    kb.insert(
        types.KeyboardButton(locale['keyboards']['back'])
    )

    setStatus(msg, "show_menu")

    await msg.answer(text=locale['settings'], reply_markup=kb)

# BACKS PROCESSOR !debugged
@dp.message_handler(checkBackLocale)
async def back(msg: types.Message):
    if checkStatus(msg, "show_menu"):
        await show_menu(msg)
        return
    elif checkStatus(msg, "show_companies"):
        await resume_start(msg)
        return
    status = getStatus(msg).split("_")
    if checkPollingStatus(msg):
        if int(status[-1]) -1 == 0:
            if status[1] == "Basic":
                removeFromData(msg)
                await resume_start(msg)
                return
            else:
                lang_id = getLangID(msg)
                locale = getLocale(lang_id)
                questions = getQuestions()
                kb = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
                kb.row(
                    types.KeyboardButton(locale['keyboards']['back'])
                )
                new_index = len(questions['Basic'][lang_id])
                setStatus(msg, f"polling_Basic_{new_index}")
                await msg.answer(questions["Basic"][lang_id][new_index-1], reply_markup=kb)
        else:
            lang_id = getLangID(msg)
            locale = getLocale(lang_id)
            questions = getQuestions()
            kb = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
            kb.row(
                types.KeyboardButton(locale['keyboards']['back'])
            )
            next_index = int(status[2]) - 2
            if next_index < 0:
                next_index = 1
            setStatus(msg, f"polling_{status[1]}_{next_index+1}")
            await msg.answer(questions[status[1]][lang_id][next_index], reply_markup=kb)
            return
    else:
        await msg.answer("!ERROR! Contact admin")
        await show_menu(msg)
        return

@dp.message_handler(checkResumeLocale)
async def resume_start(msg: types.Message):
    try:
        locale = getLocale(getLangID(msg))
    except NoLanguage:
        await select_language(msg)
        return

    setStatus(msg, "show_menu")
    kb = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    for company in getQuestions().keys():
        if company == "Basic":
            continue
        else:
            kb.insert(
                types.KeyboardButton(company)
            )
    kb.row(
        types.KeyboardButton(locale['keyboards']['back'])
    )

    await msg.answer(locale['keyboards']['companies'], reply_markup=kb)

# Handling companies and remove Basic keyword from keys
@dp.message_handler(lambda x: x.text in getQuestions().keys() and x.text != "Basic")
async def add_company(msg: types.Message):
    try:
        locale = getLocale(getLangID(msg))
        kb = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        setStatus(msg, "show_companies")
        kb.row(
            types.KeyboardButton(locale['keyboards']['back']),
            types.KeyboardButton(locale['keyboards']['start_poll'])
        )
        cur_data.execute("UPDATE data SET company=? WHERE chat_id=?", (msg.text, msg.chat.id))
        db_data.commit()

        await msg.answer(
            text=locale['keyboards']['selected'].format(company=msg.text),
            reply_markup=kb
        )

    except NoLanguage:

        await select_language(msg)
        return

@dp.message_handler(checkStartPoll)
async def start_poll(msg: types.Message):
    setStatus(msg, "polling_Basic_1")
    localed_kb = getLocale(getLangID(msg))['keyboards']
    basic_question = getLocaledQuestions(lang_id=getLangID(msg))[0]
    kb = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    kb.row(
        types.KeyboardButton(localed_kb['back'])
    )
    await msg.answer(
        text=basic_question,
        reply_markup=kb
    )

# тут каша - мала, черт ногу сломит, ей богу
@dp.message_handler(checkAnswerProcessor, content_types=types.ContentType.all())
async def answers_processor(msg: types.Message):
    _type, index = getStatus(msg).split("_")[1:]
    index = int(index)
    questions = getQuestions()
    lang_id=getLangID(msg)
    locale = getLocale(lang_id)
    if msg.text == locale['keyboards']['back']:
        return
    if index <= len(questions[_type][lang_id]):
        
        cur_data.execute("SELECT company FROM data WHERE chat_id=?", (msg.chat.id, ))
        company = cur_data.fetchone()[0]

        kb = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        kb.row(
            types.KeyboardButton(locale['keyboards']['back'])
        )
        answers = getAnswers(msg)
        addAnswers(answers, msg, _type, index)
        answers = json.dumps(answers)
        cur_data.execute("UPDATE data SET answers=? WHERE chat_id=?", (answers, msg.chat.id))
        db_data.commit()
        print(answers, _type)
        if _type == "Basic" and index == len(questions["Basic"][lang_id]) :
            setStatus(msg, f"polling_{company}_1")
            await msg.answer(questions[company][lang_id][0], reply_markup=kb)
        else:
            try:
                await msg.answer(questions[_type][lang_id][index], reply_markup=kb)
                setStatus(msg, f"polling_{_type}_{index + 1}")
            except:
                setStatus(msg, f"polling_{_type}_{len(questions[_type][lang_id])+1}")
                await msg.answer(locale['sent_photo'])

    else:
        if msg.photo:
            _return = getLocale(output_lang_id)['sent_to_manager_acc']
            _answer = getLocale(output_lang_id)['answer']
            answers = getAnswers(msg)
            addAnswers(answers, msg, _type, index)
            questions = getQuestions()

            for key, answs in answers.items():
                _return += f"{key}:\n"
                for _id, answer in enumerate(answs):
                    if answer == None:
                        continue
                    _return += f"{questions[key][output_lang_id][_id]}{_answer}{answer}\n\n"

            for chat_id in RESUME_CHAT_IDS[_type]:
                await bot.send_photo(chat_id=chat_id, caption=_return, photo=msg.photo[0].file_id)

            await msg.answer(locale['sent_callback'])

            await show_menu(msg)

        else:
            setStatus(msg, f"polling_{_type}_{len(questions[_type][lang_id])+1}")
            await msg.answer(locale['sent_photo'])

#== startdebug ==#

@dp.message_handler(commands=['lst'])
async def print_all_data(msg):
    cur_data.execute("SELECT * FROM data")
    await msg.answer(cur_data.fetchall())

#==  enddebug  == #

@dp.message_handler(commands=['get_id'])
async def get_id(msg: types.Message):

    await msg.answer(msg.chat.id)

# Polling
print(Fore.GREEN + "Started" + Style.RESET_ALL)
executor.start_polling(dp)


