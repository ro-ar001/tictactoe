import pygame
import sys
import logging
from game_client import TicTacToeClient
from game_manager import AIGameManager

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('TicTacToe-GUI')

# Colors
PINK = (255, 182, 193)
HOT_PINK = (255, 105, 180)
LAVENDER = (230, 230, 250)
PURPLE = (221, 160, 221)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 128, 0)

# Game constants
WIDTH, HEIGHT = 600, 700
LINE_WIDTH = 15
BOARD_SIZE = 3
SQUARE_SIZE = 200
CIRCLE_RADIUS = 60
CIRCLE_WIDTH = 15
X_WIDTH = 20
SPACE = 55

class PygameTicTacToeGUI:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption('Tic Tac Toe - DRL Training')
        
        self.font = pygame.font.SysFont('Arial', 40)
        self.small_font = pygame.font.SysFont('Arial', 20)
        self.medium_font = pygame.font.SysFont('Arial', 30)
        
        self.status_message = "Select game mode"
        self.can_make_move = False
        self.show_restart_button = False
        self.game_mode = None
        self.player_number = None
        self.client = None
        self.ai_manager = None
        self.show_training_button = False

    def setup_online_mode(self):
        self.game_mode = 'online'
        self.client = TicTacToeClient()
        self.client.register_callback('on_connect', self.on_connect)
        self.client.register_callback('on_waiting', self.on_waiting)
        self.client.register_callback('on_game_start', self.on_game_start)
        self.client.register_callback('on_update', self.on_update)
        self.client.register_callback('on_game_end', self.on_game_end)
        self.client.register_callback('on_error', self.on_error)
        self.client.register_callback('on_disconnect', self.on_disconnect)
        
        if not self.client.connect():
            self.status_message = "Failed to connect to server"
        else:
            self.status_message = "Connecting to server..."

    def setup_ai_mode(self):
        self.game_mode = 'ai'
        self.ai_manager = AIGameManager()
        self.ai_manager.register_callback('on_game_start', self.on_game_start)
        self.ai_manager.register_callback('on_update', self.on_update)
        self.ai_manager.register_callback('on_game_end', self.on_game_end)
        self.ai_manager.register_callback('on_game_restart', self.on_game_restart)
        self.ai_manager.start_game()
        self.status_message = "Playing against AI (Training OFF)"
        self.show_training_button = True

    def draw_mode_selection(self):
        self.screen.fill(LAVENDER)
        title_text = self.font.render("Choose Game Mode", True, PURPLE)
        title_rect = title_text.get_rect(center=(WIDTH//2, 100))
        self.screen.blit(title_text, title_rect)
        
        # Online button
        online_rect = pygame.Rect(WIDTH//2 - 150, 200, 300, 60)
        pygame.draw.rect(self.screen, PINK, online_rect, border_radius=10)
        online_text = self.medium_font.render("Play Online", True, BLACK)
        online_text_rect = online_text.get_rect(center=online_rect.center)
        self.screen.blit(online_text, online_text_rect)
        
        # AI button
        ai_rect = pygame.Rect(WIDTH//2 - 150, 300, 300, 60)
        pygame.draw.rect(self.screen, PINK, ai_rect, border_radius=10)
        ai_text = self.medium_font.render("Play Against AI", True, BLACK)
        ai_text_rect = ai_text.get_rect(center=ai_rect.center)
        self.screen.blit(ai_text, ai_text_rect)
        
        return {'online': online_rect, 'ai': ai_rect}

    def draw_lines(self):
        # Horizontal lines
        pygame.draw.line(self.screen, PURPLE, (0, SQUARE_SIZE), (WIDTH, SQUARE_SIZE), LINE_WIDTH)
        pygame.draw.line(self.screen, PURPLE, (0, 2*SQUARE_SIZE), (WIDTH, 2*SQUARE_SIZE), LINE_WIDTH)
        # Vertical lines
        pygame.draw.line(self.screen, PURPLE, (SQUARE_SIZE, 0), (SQUARE_SIZE, HEIGHT-100), LINE_WIDTH)
        pygame.draw.line(self.screen, PURPLE, (2*SQUARE_SIZE, 0), (2*SQUARE_SIZE, HEIGHT-100), LINE_WIDTH)

    def draw_board(self):
        board = None
        if self.game_mode == 'online' and self.client and self.client.game_state:
            board = self.client.game_state['board']
        elif self.game_mode == 'ai' and self.ai_manager and self.ai_manager.game_state:
            board = self.ai_manager.game_state['board']
        else:
            return
            
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                index = row * 3 + col
                if board[index] == 1:  # Player X
                    pygame.draw.line(self.screen, HOT_PINK, 
                                   (col*SQUARE_SIZE+SPACE, row*SQUARE_SIZE+SPACE),
                                   (col*SQUARE_SIZE+SQUARE_SIZE-SPACE, row*SQUARE_SIZE+SQUARE_SIZE-SPACE), X_WIDTH)
                    pygame.draw.line(self.screen, HOT_PINK,
                                   (col*SQUARE_SIZE+SPACE, row*SQUARE_SIZE+SQUARE_SIZE-SPACE),
                                   (col*SQUARE_SIZE+SQUARE_SIZE-SPACE, row*SQUARE_SIZE+SPACE), X_WIDTH)
                elif board[index] == 2:  # Player O
                    pygame.draw.circle(self.screen, PINK,
                                     (col*SQUARE_SIZE+SQUARE_SIZE//2, row*SQUARE_SIZE+SQUARE_SIZE//2),
                                     CIRCLE_RADIUS, CIRCLE_WIDTH)

    def draw_status(self):
        status_rect = pygame.Rect(0, HEIGHT-100, WIDTH, 100)
        pygame.draw.rect(self.screen, PURPLE, status_rect)
        
        text_surface = self.font.render(self.status_message, True, WHITE)
        text_rect = text_surface.get_rect(center=(WIDTH//2, HEIGHT-70))
        self.screen.blit(text_surface, text_rect)
        
        buttons = {}
        if self.show_restart_button:
            restart_rect = pygame.Rect(WIDTH//2-100, HEIGHT-40, 200, 30)
            pygame.draw.rect(self.screen, PINK, restart_rect)
            restart_text = self.small_font.render("RESTART GAME", True, BLACK)
            restart_text_rect = restart_text.get_rect(center=restart_rect.center)
            self.screen.blit(restart_text, restart_text_rect)
            buttons['restart'] = restart_rect
            
        if self.game_mode:
            back_rect = pygame.Rect(10, HEIGHT-40, 100, 30)
            pygame.draw.rect(self.screen, HOT_PINK, back_rect)
            back_text = self.small_font.render("BACK", True, WHITE)
            back_text_rect = back_text.get_rect(center=back_rect.center)
            self.screen.blit(back_text, back_text_rect)
            buttons['back'] = back_rect
            
            if self.show_training_button:
                # Training toggle button
                train_rect = pygame.Rect(WIDTH-250, HEIGHT-40, 120, 30)
                color = GREEN if self.ai_manager.training_mode else RED
                pygame.draw.rect(self.screen, color, train_rect)
                train_text = self.small_font.render("TRAIN", True, WHITE)
                train_text_rect = train_text.get_rect(center=train_rect.center)
                self.screen.blit(train_text, train_text_rect)
                buttons['train'] = train_rect
                
                # Visualization button
                if self.ai_manager.ai.reward_history:
                    viz_rect = pygame.Rect(WIDTH-120, HEIGHT-40, 110, 30)
                    pygame.draw.rect(self.screen, PURPLE, viz_rect)
                    viz_text = self.small_font.render("SHOW GRAPH", True, WHITE)
                    viz_text_rect = viz_text.get_rect(center=viz_rect.center)
                    self.screen.blit(viz_text, viz_text_rect)
                    buttons['visualize'] = viz_rect
                
        return buttons

    def check_button_click(self, pos, buttons):
        for button_name, button_rect in buttons.items():
            if button_rect and button_rect.collidepoint(pos):
                return button_name
        return None

    def check_board_click(self, pos):
        if not self.can_make_move:
            return False
            
        x, y = pos
        if y > HEIGHT-100:
            return False
            
        col = x // SQUARE_SIZE
        row = y // SQUARE_SIZE
        position = row * 3 + col
        
        if row < 0 or row >= BOARD_SIZE or col < 0 or col >= BOARD_SIZE:
            return False
            
        if self.game_mode == 'online' and self.client and self.client.game_state:
            if self.client.game_state['board'][position] == 0:
                self.client.make_move(position)
                return True
        elif self.game_mode == 'ai' and self.ai_manager and self.ai_manager.game_state:
            if self.ai_manager.game_state['board'][position] == 0:
                self.ai_manager.make_move(position)
                return True
        return False

    def reset_game(self):
        if self.game_mode == 'online' and self.client:
            self.client.disconnect()
            self.client = None
        elif self.game_mode == 'ai' and self.ai_manager:
            self.ai_manager = None
            
        self.game_mode = None
        self.can_make_move = False
        self.show_restart_button = False
        self.status_message = "Select game mode"
        self.player_number = None
        self.show_training_button = False

    # Callback methods
    def on_connect(self):
        self.status_message = "Connected to server. Waiting for opponent..."

    def on_waiting(self):
        self.status_message = "Waiting for an opponent..."

    def on_game_start(self, player_number, game_state):
        self.player_number = player_number
        self.status_message = f"You are {'X' if player_number == 1 else 'O'}"
        self.can_make_move = (game_state['current_player'] == player_number)
        self.show_restart_button = False

    def on_update(self, game_state):
        if self.game_mode == 'online':
            self.can_make_move = (game_state['current_player'] == self.player_number)
        elif self.game_mode == 'ai':
            self.can_make_move = (game_state['current_player'] == 1)

    def on_game_end(self, winner, game_state):
        if winner == 3:
            self.status_message = "It's a draw!"
        elif winner == self.player_number:
            self.status_message = "You won!"
        else:
            self.status_message = "You lost!"
        self.can_make_move = False
        self.show_restart_button = True

    def on_error(self, error_msg):
        self.status_message = f"Error: {error_msg}"

    def on_disconnect(self):
        self.status_message = "Disconnected from server"
        self.can_make_move = False
        self.show_restart_button = False

    def on_game_restart(self, game_state):
        self.status_message = "Game restarted!"
        if self.game_mode == 'online':
            self.can_make_move = (game_state['current_player'] == self.player_number)
        elif self.game_mode == 'ai':
            self.can_make_move = (game_state['current_player'] == 1)
        self.show_restart_button = False

    def run(self):
        clock = pygame.time.Clock()
        running = True
        
        while running:
            self.screen.fill(LAVENDER)
            
            if self.game_mode is None:
                mode_buttons = self.draw_mode_selection()
            else:
                self.draw_lines()
                self.draw_board()
                status_buttons = self.draw_status()
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    if self.game_mode == 'online' and self.client:
                        self.client.disconnect()
                
                if event.type == pygame.MOUSEBUTTONDOWN:
                    mouse_pos = pygame.mouse.get_pos()
                    
                    if self.game_mode is None:
                        clicked_button = self.check_button_click(mouse_pos, mode_buttons)
                        if clicked_button == 'online':
                            self.setup_online_mode()
                        elif clicked_button == 'ai':
                            self.setup_ai_mode()
                    else:
                        clicked_button = self.check_button_click(mouse_pos, status_buttons)
                        if clicked_button == 'restart':
                            if self.game_mode == 'online' and self.client:
                                self.client.request_restart()
                            elif self.game_mode == 'ai' and self.ai_manager:
                                self.ai_manager.restart_game()
                        elif clicked_button == 'back':
                            self.reset_game()
                        elif clicked_button == 'train' and self.game_mode == 'ai':
                            self.ai_manager.training_mode = not self.ai_manager.training_mode
                            status = "ON" if self.ai_manager.training_mode else "OFF"
                            self.status_message = f"Playing against AI (Training {status})"
                        elif clicked_button == 'visualize' and self.game_mode == 'ai':
                            self.ai_manager.ai.save_training_data()
                            self.ai_manager.ai.plot_training()
                        else:
                            self.check_board_click(mouse_pos)
            
            pygame.display.update()
            clock.tick(30)
        
        pygame.quit()

if __name__ == "__main__":
    gui = PygameTicTacToeGUI()
    gui.run()
