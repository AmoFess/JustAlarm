import sys
import os
import time
import json
from datetime import datetime, timedelta
import threading
import keyboard
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import pygame
import tkinter as tk
from tkinter import font

# === Определяем путь к приложению ===
if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
else:
    application_path = os.path.dirname(os.path.abspath(__file__))
os.chdir(application_path)

# === Инициализация pygame для воспроизведения звука ===
pygame.mixer.init()
print("[ ] pygame.mixer инициализирован")

# === Глобальные переменные ===
current_alarms = []
exit_flag = False
alarm_playing = False

# === Цветовая схема интерфейса ===
COLORS = {
    "bg": "#f5f7fa",
    "fg": "#2d3436",
    "title": "#1e90ff",
    "notify": "#e67e22",
    "btn": "#7460ee",
    "btn_hover": "#5a4ac7",
    "border": "#dfe6e9"
}

# === Загрузка конфигурации ===
def load_config():
    global current_alarms
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
        current_alarms = config.get("alarms", [])
        print("[+] Конфиг загружен")
    except Exception as e:
        print(f"[!] Ошибка при чтении config.json: {e}")

# === Обработчик изменений файла ===
class ConfigFileHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith("config.json"):
            print("[ ] Обнаружено изменение config.json")
            load_config()
            restart_alarms()

# === Перезапуск будильников ===
def restart_alarms():
    global alarm_threads
    for t in alarm_threads:
        pass
    alarm_threads.clear()
    start_alarms()

# === Логика будильника ===
def alarm_worker(alarm_data):
    alarm_time = alarm_data["time"]
    sound_file = alarm_data["sound"]
    repeat = alarm_data["repeat"]

    alarm_hour, alarm_minute = map(int, alarm_time.split(":"))

    while not exit_flag:
        now = datetime.now()
        alarm_datetime = now.replace(hour=alarm_hour, minute=alarm_minute, second=0, microsecond=0)

        if now >= alarm_datetime:
            if repeat:
                alarm_datetime += timedelta(days=1)
            else:
                print(f"[ ] Будильник '{alarm_time}' завершён (одноразовый)")
                return

        wait_seconds = (alarm_datetime - now).total_seconds()
        print(f"[+] Будильник '{alarm_time}' запланирован на {alarm_datetime.strftime('%Y-%m-%d %H:%M')}")
        time.sleep(wait_seconds - 1)

        while True:
            now = datetime.now()
            if now >= alarm_datetime:
                global alarm_playing
                alarm_playing = True
                print(f"[!] Сработал будильник: {alarm_time}")
                JustAlarmGUI.update_gui_on_alarm()

                try:
                    # Проверка наличия файла
                    if not os.path.exists(sound_file):
                        print(f"[!] Файл не найден: {sound_file}")
                        alarm_playing = False
                        JustAlarmGUI.hide_gui_notification()
                        break

                    pygame.mixer.music.load(sound_file)
                    pygame.mixer.music.play()

                    while pygame.mixer.music.get_busy() and alarm_playing:
                        time.sleep(0.1)
                except Exception as e:
                    print(f"[!] Ошибка воспроизведения: {e}")
                finally:
                    alarm_playing = False
                    JustAlarmGUI.hide_gui_notification()
                    print("[+] Звук остановлен.")
                break
            time.sleep(0.1)

        if not repeat:
            return

# === Запуск будильников ===
def start_alarms():
    global alarm_threads
    alarm_threads = []
    for alarm in current_alarms:
        thread = threading.Thread(target=alarm_worker, args=(alarm,), daemon=True)
        thread.start()
        alarm_threads.append(thread)

# === Отключение будильника по клавише Пробел ===
def wait_for_key():
    global alarm_playing
    print("[ ] Ожидание нажатия Пробела для остановки будильника...")
    keyboard.wait("space")
    print("[!] Будильник остановлен вручную.")
    alarm_playing = False
    pygame.mixer.music.stop()
    JustAlarmGUI.hide_gui_notification()

# === GUI с логотипом и кнопкой остановки звука ===
class JustAlarmGUI:
    root_window = None
    alarm_notification = None
    stop_button = None

    @staticmethod
    def show_logo_window():
        JustAlarmGUI.root_window = tk.Tk()
        JustAlarmGUI.root_window.title("JustAlarm")
        JustAlarmGUI.root_window.geometry("400x300")
        JustAlarmGUI.root_window.resizable(False, False)
        JustAlarmGUI.root_window.configure(bg=COLORS["bg"])

        # Установка иконки, если есть
        icon_path = os.path.join(application_path, "icon.ico")
        if os.path.exists(icon_path):
            JustAlarmGUI.root_window.iconbitmap(icon_path)

        # Шрифты
        title_font = font.Font(family="Segoe UI", size=20, weight="bold")
        text_font = font.Font(family="Segoe UI", size=10)
        notify_font = font.Font(family="Segoe UI", size=12, weight="bold")

        # Логотип
        logo_path = os.path.join(application_path, "logo.png")
        if os.path.exists(logo_path):
            logo = tk.PhotoImage(file=logo_path)
            logo_label = tk.Label(
                JustAlarmGUI.root_window,
                image=logo,
                bg=COLORS["border"],
                bd=2,
                relief="solid"
            )
            logo_label.image = logo
            logo_label.pack(pady=(10, 5))

        # Заголовок
        title = tk.Label(
            JustAlarmGUI.root_window,
            text="JustAlarm",
            font=title_font,
            fg=COLORS["title"],
            bg=COLORS["bg"]
        )
        title.pack()

        # Статус
        status = tk.Label(
            JustAlarmGUI.root_window,
            text="Будильник запущен...\nНажмите Пробел, чтобы остановить звук.",
            font=text_font,
            fg=COLORS["fg"],
            bg=COLORS["bg"],
            justify="center"
        )
        status.pack(pady=10)

        # Уведомление о сработавшем будильнике
        JustAlarmGUI.alarm_notification = tk.Label(
            JustAlarmGUI.root_window,
            text="⚠ Будильник активен!",
            font=notify_font,
            fg=COLORS["notify"],
            bg=COLORS["bg"],
            anchor="center"
        )
        JustAlarmGUI.alarm_notification.pack(pady=5)
        JustAlarmGUI.alarm_notification.pack_forget()

        # Кнопка остановки звука
        def stop_sound():
            global alarm_playing
            if alarm_playing:
                pygame.mixer.music.stop()
                alarm_playing = False
                JustAlarmGUI.hide_gui_notification()
                print("[+] Звук остановлен через кнопку.")

        JustAlarmGUI.stop_button = tk.Button(
            JustAlarmGUI.root_window,
            text="Остановить звук",
            font=text_font,
            bg=COLORS["btn"],
            fg="white",
            activebackground=COLORS["btn_hover"],
            relief="flat",
            bd=0,
            padx=10,
            pady=5,
            command=stop_sound
        )
        JustAlarmGUI.stop_button.pack(pady=5)
        JustAlarmGUI.stop_button.pack_forget()

        # Подсветка кнопки при наведении
        def on_enter(e):
            if alarm_playing:
                JustAlarmGUI.stop_button['bg'] = COLORS["btn_hover"]

        def on_leave(e):
            if alarm_playing:
                JustAlarmGUI.stop_button['bg'] = COLORS["btn"]

        JustAlarmGUI.stop_button.bind("<Enter>", on_enter)
        JustAlarmGUI.stop_button.bind("<Leave>", on_leave)

        # === ПРОВЕРКА: не завершает GUI при ошибках ===
        try:
            JustAlarmGUI.root_window.mainloop()
        except Exception as e:
            print(f"[!] GUI завершился с ошибкой: {e}")

    @staticmethod
    def update_gui_on_alarm():
        if JustAlarmGUI.alarm_notification and JustAlarmGUI.stop_button:
            JustAlarmGUI.alarm_notification.pack()
            JustAlarmGUI.animate_notification(JustAlarmGUI.alarm_notification)
            JustAlarmGUI.stop_button.pack()
            JustAlarmGUI.stop_button.configure(bg=COLORS["btn"])

    @staticmethod
    def animate_notification(widget, alpha=0.2, step=0.05):
        try:
            if alpha <= 1.0:
                r, g, b = 230, 126, 34  # Оранжевый
                color = "#%02x%02x%02x" % tuple(min(255, int(c * alpha)) for c in (r, g, b))
                widget.configure(fg=color)
                JustAlarmGUI.root_window.after(80, JustAlarmGUI.animate_notification, widget, alpha + step)
        except Exception as e:
            print(f"[!] Ошибка анимации: {e}")

    @staticmethod
    def hide_gui_notification():
        if JustAlarmGUI.alarm_notification and JustAlarmGUI.stop_button:
            JustAlarmGUI.alarm_notification.pack_forget()
            JustAlarmGUI.stop_button.pack_forget()
            JustAlarmGUI.stop_button.configure(bg=COLORS["btn"])

# === Основной запуск программы ===
print("[+] JustAlarm запущен")

# Загружаем начальный конфиг
load_config()

# Проверяем, есть ли будильники
if not current_alarms:
    print("[!] Нет будильников в config.json")
    input("Нажмите Enter, чтобы выйти...")
    sys.exit(0)

# Проверяем наличие звуковых файлов
sound_missing = False
for alarm in current_alarms:
    sound_path = alarm["sound"]
    if not os.path.exists(sound_path):
        print(f"[!] Файл не найден: {sound_path}")
        sound_missing = True
if sound_missing:
    input("Нажмите Enter, чтобы выйти...")
    sys.exit(1)

# Поток для GUI
gui_thread = threading.Thread(target=JustAlarmGUI.show_logo_window, daemon=True)
gui_thread.start()

# Поток для отключения по клавише
keyboard_thread = threading.Thread(target=wait_for_key, daemon=True)
keyboard_thread.start()

# Поток для будильников
start_alarms()

# Поток для наблюдателя за файлом
event_handler = ConfigFileHandler()
observer = Observer()
observer.schedule(event_handler, path=".", recursive=False)
observer.start()

# Основной цикл
try:
    while not exit_flag:
        time.sleep(1)
except KeyboardInterrupt:
    exit_flag = True
    print("\n[ ] Программа остановлена вручную.")

# === Убедимся, что программа не завершится, пока GUI работает ===
while gui_thread.is_alive():
    time.sleep(1)

print("[ ] Программа завершена.")