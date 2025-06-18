import socket
import threading
import time
import sys
import os
import random
import select
import termios
import tty
import json

# ANSI kleuren
RESET = "\033[0m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
MAGENTA = "\033[35m"
WHITE = "\033[37m"

DATA_FILE = "pong_userdata.json"

default_data = {
    "username": "Player",
    "stats": {
        "vs_ai": {"wins": 0, "losses": 0},
        "vs_local": {"wins": 0, "losses": 0},
        "vs_online": {"wins": 0, "losses": 0}
    }
}

def clear():
    os.system("clear" if os.name == "posix" else "cls")

def getch(timeout=0.1):
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        rlist, _, _ = select.select([fd], [], [], timeout)
        if rlist:
            ch = sys.stdin.read(1)
        else:
            ch = None
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch

class UserData:
    def __init__(self):
        self.data = self.load()

    def load(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r") as f:
                    return json.load(f)
            except:
                return default_data.copy()
        else:
            return default_data.copy()

    def save(self):
        with open(DATA_FILE, "w") as f:
            json.dump(self.data, f, indent=2)

    def get_username(self):
        return self.data.get("username", "Player")

    def set_username(self, username):
        username = username.strip()
        if username:
            self.data["username"] = username
            self.save()
            return True
        return False

    def record_result(self, mode, won):
        # mode = "single", "local", "online"
        key_map = {
            "single": "vs_ai",
            "local": "vs_local",
            "online_host": "vs_online",
            "online_client": "vs_online",
        }
        key = key_map.get(mode)
        if not key:
            return
        if won:
            self.data["stats"][key]["wins"] += 1
        else:
            self.data["stats"][key]["losses"] += 1
        self.save()

    def get_stats_str(self):
        s = self.data["stats"]
        lines = []
        lines.append(f"Username: {self.get_username()}")
        lines.append("Stats:")
        for k, v in s.items():
            lines.append(f"  {k}: Wins: {v['wins']}  Losses: {v['losses']}")
        return "\n".join(lines)

class PongGame:
    WIDTH = 60
    HEIGHT = 20
    PADDLE_HEIGHT = 4

    def __init__(self, win_score, paddle_size, ball_speed, mode="single", online_client=None, online_server=None, user_data=None):
        self.win_score = win_score
        self.paddle_size = paddle_size
        self.ball_speed = ball_speed  # lower = faster
        self.mode = mode
        self.online_client = online_client
        self.online_server = online_server
        self.user_data = user_data

        # Paddles y-pos (top)
        self.p1_y = (self.HEIGHT - self.paddle_size) // 2
        self.p2_y = (self.HEIGHT - self.paddle_size) // 2

        # Ball pos (x,y)
        self.ball_x = self.WIDTH // 2
        self.ball_y = self.HEIGHT // 2

        # Ball velocity
        self.ball_vx = 1
        self.ball_vy = 1

        # Scores
        self.score1 = 0
        self.score2 = 0

        # Game over flag
        self.game_over = False

        # Controls
        self.controls_p1_up = "w"
        self.controls_p1_down = "s"
        self.controls_p2_up = "o"
        self.controls_p2_down = "l"

        # AI difficulty for singleplayer (1 easy - 3 hard)
        self.ai_difficulty = 2

        # For timing ball movement
        self.last_ball_move = time.time()

    def draw(self):
        clear()
        # Bovenbalk met scores
        print(CYAN + f" Player 1: {self.score1} " + RESET + " " * 20 + CYAN + f" Player 2: {self.score2} " + RESET)

        # Bovenrand
        print("-" * self.WIDTH)

        for y in range(self.HEIGHT):
            line = ""
            for x in range(self.WIDTH):
                # Links paddle
                if x == 1 and self.p1_y <= y < self.p1_y + self.paddle_size:
                    line += GREEN + "|" + RESET
                # Rechts paddle
                elif x == self.WIDTH - 2 and self.p2_y <= y < self.p2_y + self.paddle_size:
                    line += YELLOW + "|" + RESET
                # Bal
                elif x == self.ball_x and y == self.ball_y:
                    line += RED + "O" + RESET
                # Muren
                elif y == 0 or y == self.HEIGHT - 1:
                    line += "-"
                else:
                    line += " "
            print(line)

        # Onderbalk
        print("-" * self.WIDTH)

        # Modus en instructies
        mode_str = {
            "single": "Singleplayer (W/S)",
            "local": "Local Multiplayer (W/S + O/L)",
            "online_host": "Online Multiplayer (Host)",
            "online_client": "Online Multiplayer (Client)",
        }.get(self.mode, "Unknown mode")

        print(CYAN + f"Mode: {mode_str}" + RESET)
        print("Press 'q' to quit game.")

    def move_ball(self):
        now = time.time()
        if now - self.last_ball_move < self.ball_speed:
            return
        self.last_ball_move = now

        # Verplaats bal
        self.ball_x += self.ball_vx
        self.ball_y += self.ball_vy

        # Botsingen boven en onder
        if self.ball_y <= 1 or self.ball_y >= self.HEIGHT - 2:
            self.ball_vy *= -1

        # Botsing paddle links
        if self.ball_x == 2:
            if self.p1_y <= self.ball_y < self.p1_y + self.paddle_size:
                self.ball_vx *= -1
            else:
                # Punt voor speler 2
                self.score2 += 1
                self.reset_ball()

        # Botsing paddle rechts
        if self.ball_x == self.WIDTH - 3:
            if self.p2_y <= self.ball_y < self.p2_y + self.paddle_size:
                self.ball_vx *= -1
            else:
                # Punt voor speler 1
                self.score1 += 1
                self.reset_ball()

    def reset_ball(self):
        self.ball_x = self.WIDTH // 2
        self.ball_y = self.HEIGHT // 2
        self.ball_vx = random.choice([-1, 1])
        self.ball_vy = random.choice([-1, 1])

    def ai_move(self):
        # AI beweegt paddle 2 (rechts)
        if self.ball_y < self.p2_y:
            self.p2_y = max(1, self.p2_y - 1)
        elif self.ball_y > self.p2_y + self.paddle_size - 1:
            self.p2_y = min(self.HEIGHT - self.paddle_size - 1, self.p2_y + 1)

    def process_input(self):
        ch = getch(0.05)
        if not ch:
            return None
        ch = ch.lower()

        # Quit game
        if ch == "q":
            self.game_over = True

        # P1 controls
        if ch == self.controls_p1_up and self.p1_y > 1:
            self.p1_y -= 1
        elif ch == self.controls_p1_down and self.p1_y < self.HEIGHT - self.paddle_size - 1:
            self.p1_y += 1

        # P2 controls (local multiplayer only)
        if self.mode == "local":
            if ch == self.controls_p2_up and self.p2_y > 1:
                self.p2_y -= 1
            elif ch == self.controls_p2_down and self.p2_y < self.HEIGHT - self.paddle_size - 1:
                self.p2_y += 1

        return ch

    def update_online(self):
        # Voor online multiplayer, stuur/ontvang paddles en ball info

        if self.mode == "online_host" and self.online_server:
            try:
                data = f"{self.p1_y},{self.p2_y},{self.ball_x},{self.ball_y},{self.ball_vx},{self.ball_vy},{self.score1},{self.score2}\n"
                self.online_server.sendall(data.encode())
                self.online_server.settimeout(0.01)
                try:
                    recv_data = self.online_server.recv(16).decode().strip()
                    if recv_data.isdigit():
                        self.p2_y = int(recv_data)
                except:
                    pass
            except:
                self.game_over = True

        elif self.mode == "online_client" and self.online_client:
            try:
                data = f"{self.p2_y}\n"
                self.online_client.sendall(data.encode())
                self.online_client.settimeout(0.01)
                try:
                    recv_data = self.online_client.recv(64).decode().strip()
                    parts = recv_data.split(",")
                    if len(parts) == 8:
                        self.p1_y = int(parts[0])
                        self.p2_y = int(parts[1])
                        self.ball_x = int(parts[2])
                        self.ball_y = int(parts[3])
                        self.ball_vx = int(parts[4])
                        self.ball_vy = int(parts[5])
                        self.score1 = int(parts[6])
                        self.score2 = int(parts[7])
                except:
                    pass
            except:
                self.game_over = True

    def run(self):
        winner = None
        while not self.game_over:
            self.draw()

            if self.mode == "single":
                self.ai_move()
                self.move_ball()
                self.process_input()

            elif self.mode == "local":
                self.process_input()
                self.move_ball()

            elif self.mode in ("online_host", "online_client"):
                self.process_input()
                self.move_ball()
                self.update_online()

            # Check win condition
            if self.score1 >= self.win_score:
                self.game_over = True
                winner = "Player 1"
            elif self.score2 >= self.win_score:
                self.game_over = True
                winner = "Player 2"

            time.sleep(0.02)

        clear()
        if winner:
            print(GREEN + f"Game over! Winner: {winner}" + RESET)
            # Stats opslaan
            if self.user_data:
                if (winner == "Player 1" and self.mode == "single") or (winner == "Player 1" and self.mode == "local") or (winner == "Player 1" and self.mode in ("online_host", "online_client")):
                    # Speler 1 wint
                    self.user_data.record_result(self.mode, True)
                else:
                    self.user_data.record_result(self.mode, False)
        else:
            print(YELLOW + "Game over. No winner (game quit early)." + RESET)
        print("Press Enter to return to menu...")
        input()


# Settings opslaan in een simpele dict
class Settings:
    def __init__(self):
        self.win_score = 5
        self.paddle_size = 4
        self.ball_speed = 0.1

    def menu(self):
        while True:
            clear()
            print(CYAN + "Settings Menu" + RESET)
            print(f"1. Win score (single/local): {self.win_score}")
            print(f"2. Paddle size (single/local): {self.paddle_size}")
            print(f"3. Ball speed (lower = faster): {self.ball_speed:.2f}")
            print("4. Back to main menu")
            choice = input("Choose option to change: ").strip()

            if choice == "1":
                val = input("Enter win score (3-10): ").strip()
                if val.isdigit() and 3 <= int(val) <= 10:
                    self.win_score = int(val)
            elif choice == "2":
                val = input("Enter paddle size (2-8): ").strip()
                if val.isdigit() and 2 <= int(val) <= 8:
                    self.paddle_size = int(val)
            elif choice == "3":
                val = input("Enter ball speed in seconds (0.02 - 0.5): ").strip()
                try:
                    fval = float(val)
                    if 0.02 <= fval <= 0.5:
                        self.ball_speed = fval
                except:
                    pass
            elif choice == "4":
                break

def online_host_menu(settings, user_data):
    clear()
    print(CYAN + "Hosting online game. Waiting for client to connect..." + RESET)
    host = "0.0.0.0"
    port = 12345
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((host, port))
    s.listen(1)
    s.settimeout(60)
    try:
        conn, addr = s.accept()
    except socket.timeout:
        print(RED + "Timeout waiting for client." + RESET)
        input("Press Enter to continue...")
        return

    print(GREEN + f"Client connected from {addr}" + RESET)
    game = PongGame(win_score=settings.win_score, paddle_size=settings.paddle_size, ball_speed=settings.ball_speed,
                    mode="online_host", online_server=conn, user_data=user_data)
    game.run()
    conn.close()
    s.close()

def online_client_menu(settings, user_data):
    clear()
    host = input("Enter host IP to connect to: ").strip()
    port = 12345
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((host, port))
    except Exception as e:
        print(RED + f"Failed to connect: {e}" + RESET)
        input("Press Enter to continue...")
        return

    print(GREEN + f"Connected to server {host}" + RESET)
    game = PongGame(win_score=settings.win_score, paddle_size=settings.paddle_size, ball_speed=settings.ball_speed,
                    mode="online_client", online_client=s, user_data=user_data)
    game.run()
    s.close()

def main_menu():
    settings = Settings()
    user_data = UserData()

    while True:
        clear()
        print(MAGENTA + "=== Pong by @theowenj ===" + RESET)
        print("1. Play Singleplayer")
        print("2. Play Local Multiplayer")
        print("3. Play Online Multiplayer (Host)")
        print("4. Play Online Multiplayer (Join)")
        print("5. Settings")
        print("6. Change Username")
        print("7. Show Stats")
        print("8. Quit")
        choice = input("Choose option: ").strip()

        if choice == "1":
            game = PongGame(settings.win_score, settings.paddle_size, settings.ball_speed, mode="single", user_data=user_data)
            game.run()
        elif choice == "2":
            game = PongGame(settings.win_score, settings.paddle_size, settings.ball_speed, mode="local", user_data=user_data)
            game.run()
        elif choice == "3":
            online_host_menu(settings, user_data)
        elif choice == "4":
            online_client_menu(settings, user_data)
        elif choice == "5":
            settings.menu()
        elif choice == "6":
            clear()
            print(CYAN + f"Current username: {user_data.get_username()}" + RESET)
            new_name = input("Enter new username: ").strip()
            if user_data.set_username(new_name):
                print(GREEN + "Username updated!" + RESET)
            else:
                print(RED + "Invalid username." + RESET)
            time.sleep(1.5)
        elif choice == "7":
            clear()
            print(CYAN + "Player Stats" + RESET)
            print(user_data.get_stats_str())
            print("\nPress Enter to return to menu...")
            input()
        elif choice == "8":
            clear()
            print("Bye!")
            break
        else:
            print(RED + "Invalid option." + RESET)
            time.sleep(1)

if __name__ == "__main__":
    main_menu()
