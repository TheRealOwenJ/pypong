import socket, threading, time, sys, os, random, json

# Cross-platform getch()
if os.name == 'nt':
    import msvcrt
    def getch(timeout=0.05):
        start = time.time()
        while True:
            if msvcrt.kbhit():
                ch = msvcrt.getch()
                if ch in (b'\xe0', b'\x00'):
                    ch2 = msvcrt.getch()
                    return (ch + ch2).decode(errors="ignore")
                return ch.decode(errors="ignore")
            if time.time() - start > timeout:
                return None
else:
    import tty, termios, select
    def getch(timeout=0.05):
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            r, _, _ = select.select([fd], [], [], timeout)
            if r:
                ch = sys.stdin.read(1)
                if ch == '\x1b':  # mogelijk pijltjestoets
                    r2, _, _ = select.select([fd], [], [], 0.01)
                    if r2:
                        ch += sys.stdin.read(2)
                return ch
            return None
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)

# Kleuren met fallback
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
            json.dump(self.data, f, indent=2)

    def get_username(self):
        return self.data.get("username", "Player")

    def set_username(self, name):
        name = name.strip()
        if name:
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
        out = [f"Username: {self.get_username()}", "Stats:"]
        for k, v in s.items():
            out.append(f"  {k}: Wins: {v['wins']}  Losses: {v['losses']}")
        return "\n".join(out)

class PongGame:
    WIDTH, HEIGHT = 60, 20
    def __init__(self, win_score, paddle_size, ball_speed, mode="single", user_data=None, online_server=None, online_client=None):
        self.win_score = win_score
        self.paddle_size = paddle_size
        self.ball_speed = ball_speed
        self.mode = mode
        self.user_data = user_data
        self.username = user_data.get_username() if user_data else "Player"
        self.opponent_username = "Opponent"
        self.server = online_server
        self.client = online_client

        self.p1_y = (self.HEIGHT - paddle_size) // 2
        self.p2_y = (self.HEIGHT - paddle_size) // 2
        self.ball_x = self.WIDTH // 2
        self.ball_y = self.HEIGHT // 2
        self.ball_vx = random.choice([-1, 1])
        self.ball_vy = random.choice([-1, 1])
        self.score1 = 0
        self.score2 = 0
        self.last_move = time.time()
        self.game_over = False

        # Controls: P1 = WASD; P2 = pijltjestoetsen
        self.controls_p1_up = "w"
        self.controls_p1_down = "s"
        self.controls_p2_up = "\x1b[A"  # pijl omhoog
        self.controls_p2_down = "\x1b[B"  # pijl omlaag

    def draw(self):
        clear()
        print(CYAN + f"{self.username}: {self.score1}" + RESET + " " * 15 + CYAN + f"{self.opponent_username}: {self.score2}" + RESET)
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
        if time.time() - self.last_move < self.ball_speed:
            return
        self.last_move = time.time()

        self.ball_x += self.ball_vx
        self.ball_y += self.ball_vy

        # Botsen tegen boven/onderkant
        if self.ball_y <= 0:
            self.ball_y = 0
            self.ball_vy *= -1
        elif self.ball_y >= self.HEIGHT - 1:
            self.ball_y = self.HEIGHT - 1
            self.ball_vy *= -1

        # Links paddle (p1)
        if self.ball_x == 2:
            if self.p1_y <= self.ball_y < self.p1_y + self.paddle_size:
                self.ball_vx *= -1
            else:
                self.score2 += 1
                self.reset_ball()

        # Rechts paddle (p2)
        elif self.ball_x == self.WIDTH - 3:
            if self.p2_y <= self.ball_y < self.p2_y + self.paddle_size:
                self.ball_vx *= -1
            else:
                self.score1 += 1
                self.reset_ball()

    def process_input(self):
        ch = getch()
        if ch is None:
            return

        if ch == "q":
            self.game_over = True
            return

        # P1 besturing altijd:
        if ch == self.controls_p1_up and self.p1_y > 0:
            self.p1_y -= 1
        elif ch == self.controls_p1_down and self.p1_y < self.HEIGHT - self.paddle_size:
            self.p1_y += 1

        # P2 besturing voor local en online client
        if self.mode == "local" or self.mode == "online_client":
            if ch == self.controls_p2_up and self.p2_y > 0:
                self.p2_y -= 1
            elif ch == self.controls_p2_down and self.p2_y < self.HEIGHT - self.paddle_size:
                self.p2_y += 1

    def ai_move(self):
        # AI volgt bal langzaam
        if self.ball_y < self.p2_y:
            self.p2_y = max(0, self.p2_y - 1)
        elif self.ball_y > self.p2_y + self.paddle_size - 1:
            self.p2_y = min(self.HEIGHT - self.paddle_size, self.p2_y + 1)

    def update_online(self):
        try:
            if self.mode == "online_host":
                # Host stuurt paddle1 + bal + score naar client
                send_str = f"{self.p1_y},{self.ball_x},{self.ball_y},{self.ball_vx},{self.ball_vy},{self.score1},{self.score2}\n"
                self.server.sendall(send_str.encode())

                # Ontvang paddle2 van client
                data = self.server.recv(32)
                if not data:
                    self.game_over = True
                    return
                self.p2_y = int(data.decode().strip())

            elif self.mode == "online_client":
                # Client stuurt paddle2 naar host
                self.client.sendall(f"{self.p2_y}\n".encode())

                # Ontvang paddle1 + bal + score van host
                data = self.client.recv(64)
                if not data:
                    self.game_over = True
                    return
                parts = data.decode().strip().split(",")
                if len(parts) == 7:
                    self.p1_y = int(parts[0])
                    self.ball_x = int(parts[1])
                    self.ball_y = int(parts[2])
                    self.ball_vx = int(parts[3])
                    self.ball_vy = int(parts[4])
                    self.score1 = int(parts[5])
                    self.score2 = int(parts[6])
        except:
            self.game_over = True

    def run(self):
        while not self.game_over:
            self.draw()
            self.process_input()

            if self.mode == "single":
                self.ai_move()

            # Bal alleen verplaatsen op host of single
            if self.mode in ("single", "local", "online_host"):
                self.move_ball()

            # Online sync
            if self.mode.startswith("online"):
                self.update_online()

            # Check of iemand heeft gewonnen
            if self.score1 >= self.win_score or self.score2 >= self.win_score:
                self.game_over = True

            time.sleep(0.03)

        clear()
        winner = None
        if self.score1 > self.score2:
            winner = self.username
        elif self.score2 > self.score1:
            winner = self.opponent_username
        else:
            winner = "No one"

        print(GREEN + f"Game Over! Winner: {winner}" + RESET)
        if self.user_data:
            won = (winner == self.username)
            self.user_data.record_result(self.mode, won)
        input("Press Enter to continue...")

def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

def main_menu():
    user = UserData()
    settings = {"win_score": 5, "paddle_size": 4, "ball_speed": 0.08}
    while True:
        clear()
        print("1. Singleplayer\n2. Local Multiplayer\n3. Online Host\n4. Online Join\n5. Change Username\n6. Stats\n7. Quit")
        opt = input("> ").strip()
        if opt == "1":
            game = PongGame(**settings, mode="single", user_data=user)
            game.run()
        elif opt == "2":
            game = PongGame(**settings, mode="local", user_data=user)
            game.run()
        elif opt == "3":
            print(f"Your IP: {get_ip()}")
            print("Waiting for opponent to connect...")
            s = socket.socket()
            s.bind(("", 12345))
            s.listen(1)
            conn, addr = s.accept()
            # Receive opponent username
            opponent_name = conn.recv(32).decode().strip()
            # Send own username
            conn.sendall((user.get_username() + "\n").encode())
            game = PongGame(**settings, mode="online_host", user_data=user, online_server=conn)
            game.opponent_username = opponent_name
            game.run()
            conn.close()
            s.close()
        elif opt == "4":
            host = input("Host IP: ")
            conn = socket.socket()
            try:
                conn.connect((host, 12345))
            except Exception as e:
                print(f"Failed to connect: {e}")
                input("Press Enter to continue...")
                continue
            # Send own username
            conn.sendall((user.get_username() + "\n").encode())
            # Receive opponent username
            opponent_name = conn.recv(32).decode().strip()
            game = PongGame(**settings, mode="online_client", user_data=user, online_client=conn)
            game.opponent_username = opponent_name
            game.run()
            conn.close()
        elif opt == "5":
            newname = input("New Username: ")
            user.set_username(newname)
        elif opt == "6":
            clear()
            print(user.get_stats_str())
            input("Press Enter to return")
        elif opt == "7":
            break

if __name__ == "__main__":
    main_menu()
