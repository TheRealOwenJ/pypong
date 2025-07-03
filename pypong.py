import socket
import time
import os
import random
import json
import shutil
import getch  # extern, gebruik getch.getch()

# --- Kleuren fallback ---
try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    RESET = Style.RESET_ALL
    RED = Fore.RED
    GREEN = Fore.GREEN
    YELLOW = Fore.YELLOW
    CYAN = Fore.CYAN
    MAGENTA = Fore.MAGENTA
    WHITE = Fore.WHITE
except ImportError:
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
    os.system("cls" if os.name == "nt" else "clear")

class UserData:
    def __init__(self):
        self.data = self.load()

    def load(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE) as f:
                    return json.load(f)
            except:
                return default_data.copy()
        return default_data.copy()

    def save(self):
        with open(DATA_FILE, "w") as f:
            f.write(json.dumps(self.data, indent=2))

    def get_username(self):
        return self.data.get("username", "Player")

    def set_username(self, name):
        name = name.strip()
        if 0 < len(name) <= 12:  # Username limiet
            self.data["username"] = name
            self.save()
            return True
        return False

    def record_result(self, mode, won):
        key = {"single": "vs_ai", "local": "vs_local", "online_host": "vs_online", "online_client": "vs_online"}.get(mode)
        if not key: return
        if won:
            self.data["stats"][key]["wins"] += 1
        else:
            self.data["stats"][key]["losses"] += 1
        self.save()

    def get_stats_str(self):
        s = self.data["stats"]
        out = [
            f"{CYAN}Username:{RESET} {self.get_username()}",
            f"{MAGENTA}{'='*30}{RESET}",
            f"{YELLOW}Game Mode       Wins   Losses{RESET}",
        ]
        for mode, vals in s.items():
            mode_name = {
                "vs_ai": "Singleplayer",
                "vs_local": "Local Multiplayer",
                "vs_online": "Online Multiplayer"
            }.get(mode, mode)
            out.append(f"{mode_name:<15} {vals['wins']:<6} {vals['losses']:<6}")
        out.append(f"{MAGENTA}{'='*30}{RESET}")
        return "\n".join(out)

class PongGame:
    WIN_SCORE = 5
    PADDLE_SIZE = 4
    BALL_SPEED = 0.08

    def __init__(self, mode="single", user_data=None, online_server=None, online_client=None, fit_terminal=False):
        self.user_data = user_data
        self.username = user_data.get_username() if user_data else "Player"
        self.opponent_username = "Opponent"
        self.opponent_wins = 0

        self.mode = mode
        self.server = online_server
        self.client = online_client

        if fit_terminal:
            size = shutil.get_terminal_size()
            self.WIDTH = max(30, size.columns - 10)
            self.HEIGHT = max(10, size.lines - 10)
        else:
            self.WIDTH = 60
            self.HEIGHT = 20

        self.paddle_size = self.PADDLE_SIZE
        self.ball_speed = self.BALL_SPEED
        self.win_score = self.WIN_SCORE

        self.p1_y = self.p2_y = (self.HEIGHT - self.paddle_size) // 2
        self.ball_x = self.WIDTH // 2
        self.ball_y = self.HEIGHT // 2
        self.ball_vx = random.choice([-1,1])
        self.ball_vy = random.choice([-1,1])
        self.score1 = 0
        self.score2 = 0
        self.last_move = time.time()
        self.game_over = False

        self.controls_p1_up = "w"
        self.controls_p1_down = "s"
        self.controls_p2_up = "\x1b[A"
        self.controls_p2_down = "\x1b[B"

    def draw(self):
        clear()
        if self.mode.startswith("online"):
            score_line = (f"{CYAN}{self.username}: {self.score1}{RESET}  |  "
                          f"{YELLOW}{self.opponent_username}: {self.score2} (Wins: {self.opponent_wins}){RESET}")
        else:
            score_line = f"{CYAN}{self.username}: {self.score1}{RESET}  |  {YELLOW}{self.opponent_username}: {self.score2}{RESET}"
        print("="*self.WIDTH)
        print(score_line.center(self.WIDTH))
        print("="*self.WIDTH)
        for y in range(self.HEIGHT):
            line = ""
            for x in range(self.WIDTH):
                if x == 1 and self.p1_y <= y < self.p1_y + self.paddle_size:
                    line += GREEN + "|" + RESET
                elif x == self.WIDTH - 2 and self.p2_y <= y < self.p2_y + self.paddle_size:
                    line += YELLOW + "|" + RESET
                elif x == self.ball_x and y == self.ball_y:
                    line += RED + "O" + RESET
                else:
                    line += " "
            print(line)
        print("="*self.WIDTH)
        print("Controls: Player 1 = W/S | Player 2 = Arrow Up/Down (Local) | 'q' to quit".center(self.WIDTH))

    def reset_ball(self):
        self.ball_x = self.WIDTH // 2
        self.ball_y = self.HEIGHT // 2
        self.ball_vx = random.choice([-1, 1])
        self.ball_vy = random.choice([-1, 1])

    def move_ball(self):
        if time.time() - self.last_move < self.ball_speed:
            return
        self.last_move = time.time()

        self.ball_x += self.ball_vx
        self.ball_y += self.ball_vy

        if self.ball_y <= 0 or self.ball_y >= self.HEIGHT - 1:
            self.ball_vy *= -1

        if self.ball_x == 2:
            if self.p1_y <= self.ball_y < self.p1_y + self.paddle_size:
                self.ball_vx *= -1
            else:
                self.score2 += 1
                self.reset_ball()

        elif self.ball_x == self.WIDTH - 3:
            if self.p2_y <= self.ball_y < self.p2_y + self.paddle_size:
                self.ball_vx *= -1
            else:
                self.score1 += 1
                self.reset_ball()

    def process_input(self):
        ch = getch.getch()
        if ch == "q":
            self.game_over = True
        if ch == self.controls_p1_up and self.p1_y > 0:
            self.p1_y -= 1
        elif ch == self.controls_p1_down and self.p1_y < self.HEIGHT - self.paddle_size:
            self.p1_y += 1
        if self.mode == "local":
            if ch == self.controls_p2_up and self.p2_y > 0:
                self.p2_y -= 1
            elif ch == self.controls_p2_down and self.p2_y < self.HEIGHT - self.paddle_size:
                self.p2_y += 1

    def ai_move(self):
        # Slimme AI: volg de bal maar met een beetje vertraging (voor uitdaging)
        if self.ball_y < self.p2_y + self.paddle_size // 2 and self.p2_y > 0:
            self.p2_y -= 1
        elif self.ball_y > self.p2_y + self.paddle_size // 2 and self.p2_y < self.HEIGHT - self.paddle_size:
            self.p2_y += 1

    def update_online(self):
        try:
            if self.mode == "online_host":
                data_out = f"{self.p1_y},{self.ball_x},{self.ball_y},{self.ball_vx},{self.ball_vy},{self.score1},{self.score2},{self.user_data.data['stats']['vs_online']['wins']}\n"
                self.server.sendall(data_out.encode())

                data_in = self.server.recv(64).decode().strip().split(",")
                self.p2_y = int(data_in[0])
                self.opponent_wins = int(data_in[7]) if len(data_in) > 7 else 0

            elif self.mode == "online_client":
                data_out = f"{self.p2_y},{self.user_data.data['stats']['vs_online']['wins']}\n"
                self.client.sendall(data_out.encode())

                data_in = self.client.recv(64).decode().strip().split(",")
                self.p1_y, self.ball_x, self.ball_y = int(data_in[0]), int(data_in[1]), int(data_in[2])
                self.ball_vx, self.ball_vy = int(data_in[3]), int(data_in[4])
                self.score1, self.score2 = int(data_in[5]), int(data_in[6])
                self.opponent_wins = int(data_in[7]) if len(data_in) > 7 else 0

        except Exception:
            self.game_over = True

    def run(self):
        while not self.game_over:
            self.draw()
            self.process_input()
            if self.mode == "single":
                self.ai_move()
            self.move_ball()
            if self.mode.startswith("online"):
                self.update_online()

            if self.score1 >= self.win_score or self.score2 >= self.win_score:
                self.game_over = True

            time.sleep(0.03)

        clear()
        won = self.score1 > self.score2
        if won:
            print(f"{GREEN}{' YOU WIN! ':=^{self.WIDTH}}{RESET}")
        else:
            print(f"{RED}{' YOU LOSE! ':=^{self.WIDTH}}{RESET}")
        print(f"Final Score: {self.username} {self.score1} - {self.opponent_username} {self.score2}".center(self.WIDTH))
        print("="*self.WIDTH)
        if self.user_data:
            self.user_data.record_result(self.mode, won)
        input("Press Enter to return to menu...")

def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip

def settings_menu(settings, user):
    while True:
        clear()
        print(f"{MAGENTA}{' Settings ':=^40}{RESET}")
        print(f"1. Toggle Fit to Terminal: [{'ON' if settings['fit_terminal'] else 'OFF'}]")
        print(f"2. Change Username (max 12 chars): {CYAN}{user.get_username()}{RESET}")
        print("3. Back")
        choice = input("Choose: ").strip()
        if choice == "1":
            settings["fit_terminal"] = not settings["fit_terminal"]
            print("Fit to terminal is now", "ON" if settings["fit_terminal"] else "OFF")
            time.sleep(1)
        elif choice == "2":
            newname = input("Enter new username: ").strip()
            if not user.set_username(newname):
                print(RED + "Invalid username! Must be 1-12 characters." + RESET)
                time.sleep(1.5)
        elif choice == "3":
            break
        else:
            print(RED + "Invalid option!" + RESET)
            time.sleep(1)

def main_menu():
    user = UserData()
    settings = {"fit_terminal": False}

    while True:
        clear()
        print(f"{MAGENTA}{' PyPong Main Menu ':=^60}{RESET}")
        print(f"1. Singleplayer")
        print(f"2. Local Multiplayer")
        print(f"3. Online Host")
        print(f"4. Online Join")
        print(f"5. Settings")
        print(f"6. Stats")
        print(f"7. Quit")
        opt = input("> ").strip()

        if opt == "1":
            game = PongGame(mode="single", user_data=user, fit_terminal=settings["fit_terminal"])
            game.run()
        elif opt == "2":
            game = PongGame(mode="local", user_data=user, fit_terminal=settings["fit_terminal"])
            game.run()
        elif opt == "3":
            print(f"Your IP: {get_ip()}")
            s = socket.socket()
            s.bind(("", 12345))
            s.listen(1)
            print("Waiting for client to connect...")
            conn, addr = s.accept()
            opponent_name = conn.recv(32).decode().strip()[:12]
            conn.sendall((user.get_username()[:12] + "\n").encode())
            game = PongGame(mode="online_host", user_data=user, online_server=conn, fit_terminal=settings["fit_terminal"])
            game.opponent_username = opponent_name
            game.run()
            conn.close()
            s.close()
        elif opt == "4":
            host = input("Host IP: ").strip()
            conn = socket.socket()
            try:
                conn.connect((host, 12345))
            except Exception as e:
                print(RED + f"Failed to connect: {e}" + RESET)
                time.sleep(2)
                continue
            conn.sendall((user.get_username()[:12] + "\n").encode())
            opponent_name = conn.recv(32).decode().strip()[:12]
            game = PongGame(mode="online_client", user_data=user, online_client=conn, fit_terminal=settings["fit_terminal"])
            game.opponent_username = opponent_name
            game.run()
            conn.close()
        elif opt == "5":
            settings_menu(settings, user)
        elif opt == "6":
            clear()
            print(user.get_stats_str())
            input("Press Enter to return to menu...")
        elif opt == "7":
            print(GREEN + "Bye! Thanks for playing PyPong." + RESET)
            break
        else:
            print(RED + "Invalid option." + RESET)
            time.sleep(1)

if __name__ == "__main__":
    main_menu()
