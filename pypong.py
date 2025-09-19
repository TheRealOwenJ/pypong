import time
import os
import random
import json
import shutil
import getch

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
        "vs_local": {"wins": 0, "losses": 0}
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
        if 0 < len(name) <= 12:
            self.data["username"] = name
            self.save()
            return True
        return False

    def record_result(self, mode, won):
        key = {"single": "vs_ai", "local": "vs_local"}.get(mode)
        if not key: return
        if won:
            self.data["stats"][key]["wins"] += 1
        else:
            self.data["stats"][key]["losses"] += 1
        self.save()

    def get_stats_str(self):
        s = self.data["stats"]
        out = [f"{MAGENTA}Username:{RESET} {self.get_username()}", f"{MAGENTA}Stats:{RESET}"]
        for k, v in s.items():
            out.append(f"  {CYAN}{k}{RESET}: {GREEN}Wins: {v['wins']}{RESET}  {RED}Losses: {v['losses']}{RESET}")
        return "\n".join(out)


class PongGame:
    WIN_SCORE = 5
    PADDLE_SIZE = 4
    BALL_SPEED = 0.07

    def __init__(self, mode="single", user_data=None, fit_terminal=False):
        self.user_data = user_data
        self.username = user_data.get_username() if user_data else "Player"
        self.opponent_username = "Opponent"
        self.mode = mode

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
        self.last_ball_move = time.time()
        self.game_over = False

        self.controls_p1_up = "w"
        self.controls_p1_down = "s"
        self.controls_p2_up = "\x1b[A"
        self.controls_p2_down = "\x1b[B"

    def draw(self):
        clear()
        score_line = (f"{CYAN}{self.username}: {self.score1}{RESET}  |  "
                      f"{YELLOW}{self.opponent_username}: {self.score2}{RESET}")
        print(score_line)
        print("-" * self.WIDTH)
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
        print("-" * self.WIDTH)
        print("Press 'q' to quit")

    def reset_ball(self):
        self.ball_x = self.WIDTH // 2
        self.ball_y = self.HEIGHT // 2
        self.ball_vx = random.choice([-1, 1])
        self.ball_vy = random.choice([-1, 1])

    def move_ball(self):
        if time.time() - self.last_ball_move < self.ball_speed:
            return
        self.last_ball_move = time.time()

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
        ch = getch.getch(timeout=0.03)
        if ch is None:
            return False
        if ch == "q":
            self.game_over = True
            return True
        if ch == self.controls_p1_up and self.p1_y > 0:
            self.p1_y -= 1
            return True
        elif ch == self.controls_p1_down and self.p1_y < self.HEIGHT - self.paddle_size:
            self.p1_y += 1
            return True
        if self.mode == "local":
            if ch == self.controls_p2_up and self.p2_y > 0:
                self.p2_y -= 1
                return True
            elif ch == self.controls_p2_down and self.p2_y < self.HEIGHT - self.paddle_size:
                self.p2_y += 1
                return True
        return False

    def ai_move(self):
        if self.ball_y < self.p2_y:
            self.p2_y = max(0, self.p2_y - 1)
        elif self.ball_y > self.p2_y + self.paddle_size - 1:
            self.p2_y = min(self.HEIGHT - self.paddle_size, self.p2_y + 1)

    def run(self):
        last_draw_time = 0
        draw_interval = 1/30
        won_displayed = False
        while not self.game_over:
            updated = False
            moved = self.process_input()
            if moved:
                updated = True

            if self.mode == "single":
                self.ai_move()
                updated = True

            now = time.time()
            if now - self.last_ball_move >= self.ball_speed:
                self.move_ball()
                updated = True

            if (self.score1 >= self.win_score or self.score2 >= self.win_score) and not won_displayed:
                self.draw()
                if self.score1 > self.score2:
                    print(GREEN + "\nYou win! 🎉" + RESET)
                else:
                    print(RED + "\nYou lose! 😞" + RESET)
                won_displayed = True
                time.sleep(3)
                self.game_over = True
                break

            if updated and (time.time() - last_draw_time > draw_interval):
                self.draw()
                last_draw_time = time.time()

            time.sleep(0.01)

        clear()
        if self.user_data:
            won = self.score1 > self.score2
            self.user_data.record_result(self.mode, won)
        input("Press Enter to continue...")

def settings_menu(settings, user):
    clear()
    print(f"{MAGENTA}Settings:{RESET}")
    print(f"1. Toggle Fit to Terminal (currently: {YELLOW}{'On' if settings['fit_terminal'] else 'Off'}{RESET})")
    print(f"2. Change Username (max 12 chars)")
    print(f"3. Back")
    choice = input(f"{CYAN}Choose: {RESET}").strip()
    if choice == "1":
        settings["fit_terminal"] = not settings["fit_terminal"]
        print(f"Fit to terminal is now {YELLOW}{'On' if settings['fit_terminal'] else 'Off'}{RESET}")
        time.sleep(1)
    elif choice == "2":
        newname = input(f"New Username: ").strip()
        if not user.set_username(newname):
            print(f"{RED}Invalid username (empty or longer than 12 chars).{RESET}")
            time.sleep(1.5)

def main_menu():
    user = UserData()
    settings = {"fit_terminal": False}

    while True:
        clear()
        print(f"{CYAN}=== Main Menu ==={RESET}")
        print(f"{GREEN}1.{RESET} Singleplayer")
        print(f"{GREEN}2.{RESET} Local Multiplayer")
        print(f"{GREEN}3.{RESET} Settings")
        print(f"{GREEN}4.{RESET} Stats")
        print(f"{GREEN}5.{RESET} Quit")
        opt = input(f"{YELLOW}> {RESET}").strip()

        if opt == "1":
            game = PongGame(mode="single", user_data=user, fit_terminal=settings["fit_terminal"])
            game.run()
        elif opt == "2":
            game = PongGame(mode="local", user_data=user, fit_terminal=settings["fit_terminal"])
            game.run()
        elif opt == "3":
            settings_menu(settings, user)
        elif opt == "4":
            clear()
            print(user.get_stats_str())
            input("Press Enter to return...")
        elif opt == "5":
            print(GREEN + "Bye! 👋" + RESET)
            break
        else:
            print(RED + "Invalid option." + RESET)
            time.sleep(1)

if __name__ == "__main__":
    main_menu()
