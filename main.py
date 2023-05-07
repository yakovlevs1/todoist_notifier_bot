import os
import datetime
import time
import telebot
from dotenv import load_dotenv
from todoist_api_python.api import TodoistAPI
from todoist_api_python.models import Task

load_dotenv()

TODOIST_TOKEN = os.getenv("todoist_token")
TELEGRAM_TOKEN = os.getenv("telegram_token")
MY_TELEGRAM_ID = int(os.getenv("my_telegram_id"))

api = TodoistAPI(TODOIST_TOKEN)
bot = telebot.TeleBot(TELEGRAM_TOKEN)


project_ids = dict()
personal_ids = dict()

def init_ids():
    global project_ids, personal_ids
    for prj in api.get_projects():
        project_ids[prj.name] = prj.id
        
        if prj.is_inbox_project:
            # Make sure that you have at least one task in "Inbox" project
            try:
                personal_ids['Me'] = api.get_tasks(project_id=project_ids[prj.name])[0].creator_id
            except IndexError:
                print("You don't have any task in " + prj.name)
                raise
    print(project_ids)
    print(personal_ids)

print("initialized")


def get_current_time() -> str:
    # I'm at UTC+3 so timedelta==3 hours
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3)))
    return now.strftime("%Y-%m-%dT%H:%M:%S")


def get_all_my_tasks():
    all_my_tasks = list()
    for project in project_ids:
        if project == "Inbox":
            all_my_tasks += api.get_tasks(project_id=project_ids[project])
        else:
            all_my_tasks += [task for task in api.get_tasks(project_id=project_ids[project]) if task.assignee_id == personal_ids['Me']]
    return all_my_tasks


def filter_tasks(list_of_tasks: list[Task], mode: str) -> list[Task]:
    if mode == "dated":
        return [task for task in list_of_tasks if task.due and not task.due.datetime]
    elif mode == "datetimed":
        return [task for task in list_of_tasks if task.due and task.due.datetime]
    elif mode == "today":
        result = []
        for task in list_of_tasks:
            if task.due:
                if task.due.date == datetime.date.today().strftime("%Y-%m-%d"):
                    result.append(task)
        return result


def get_time_to_task(task):
    task_time = datetime.datetime.fromisoformat(task.due.datetime)
    now = datetime.datetime.fromisoformat(get_current_time())
    return task_time - now


def get_time_to_task_in_minutes(task):
    return int(get_time_to_task(task).total_seconds() / 60)


@bot.message_handler(
    func=lambda msg: msg.from_user.id == MY_TELEGRAM_ID and msg.text == "1"
)
def tell_that_bot_is_alive(message):
    bot.reply_to(message, "Да")


update_idd = 0

if __name__ == "__main__":
    init_ids()
    while True:
        print("iteration")
        updates = bot.get_updates(update_idd + 1, long_polling_timeout=2)
        if len(updates) > 0:
            update_idd = updates[-1].update_id
            bot.process_new_updates(updates)
        tasks = get_all_my_tasks()
        for task in filter_tasks(tasks, mode="datetimed"):
            print(task.content, get_time_to_task_in_minutes(task))
        for task in filter_tasks(tasks, mode="datetimed"):
            if get_time_to_task_in_minutes(task) == 10:
                bot.send_message(MY_TELEGRAM_ID, task.content)
        print("sleeps")
        time.sleep(60)