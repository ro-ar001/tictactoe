import socket
import json
import threading
import pygame
import sys
import logging
import random
import time
from typing import Dict, List, Optional, Callable

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('TicTacToe-Client')

class TicTacToeClient:
    """Client for the Tic Tac Toe game"""
    
    def __init__(self, host: str = 'localhost', port: int = 5555):
        self.host = host
        self.port = port
        self.sock = None
        self.connected = False
        self.session_id = None
        self.player_number = None
        self.game_state = None
        self.receiver_thread = None
        self.callbacks = {
            'on_connect': [],
            'on_waiting': [],
            'on_game_start': [],
            'on_update': [],
            'on_game_end': [],
            'on_error': [],
            'on_disconnect': [],
            'on_opponent_disconnect': [],
            'on_game_restart': []
        }
        
    def connect(self):
        """Connect to the server"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(10)  # 10 second timeout for connection
            self.sock.connect((self.host, self.port))
            self.sock.settimeout(None)  # Reset timeout after connection
            self.connected = True
            logger.info(f"Connected to server at {self.host}:{self.port}")
            
            # Start the message receiver thread
            self.receiver_thread = threading.Thread(target=self.receive_messages)
            self.receiver_thread.daemon = True
            self.receiver_thread.start()
            
            return True
        except socket.timeout:
            logger.error("Connection attempt timed out")
            return False
        except ConnectionRefusedError:
            logger.error("Connection refused. Is the server running?")
            return False
        except Exception as e:
            logger.error(f"Connection error: {e}")
            return False
            
    def disconnect(self):
        """Disconnect from the server"""
        if self.connected:
            self.connected = False
            if self.sock:
                try:
                    self.sock.shutdown(socket.SHUT_RDWR)
                    self.sock.close()
                except:
                    pass
            logger.info("Disconnected from server")
            
    def send_message(self, message: Dict):
        """Send a message to the server"""
        if not self.connected:
            logger.error("Not connected to server")
            return False
            
        try:
            self.sock.sendall((json.dumps(message) + '\n').encode('utf-8'))
            return True
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            self.connected = False
            self._trigger_callback('on_disconnect')
            return False
            
    def receive_messages(self):
        """Continuously receive messages from the server"""
        buffer = ""
        
        while self.connected:
            try:
                data = self.sock.recv(1024).decode('utf-8')
                if not data:
                    logger.info("Server closed the connection")
                    self.connected = False
                    self._trigger_callback('on_disconnect')
                    break
                    
                buffer += data
                
                # Handle messages that may be split or combined
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line:
                        try:
                            message = json.loads(line)
                            self.process_message(message)
                        except json.JSONDecodeError:
                            logger.error(f"Invalid JSON received: {line}")
                            
            except ConnectionResetError:
                logger.error("Connection reset by server")
                self.connected = False
                self._trigger_callback('on_disconnect')
                break
            except Exception as e:
                logger.error(f"Error receiving messages: {e}")
                self.connected = False
                self._trigger_callback('on_disconnect')
                break
                
    def process_message(self, message: Dict):
        """Process a message from the server"""
        message_type = message.get('type')
        
        if message_type == 'welcome':
            logger.info(f"Welcome message: {message.get('message')}")
            self._trigger_callback('on_connect')
            
        elif message_type == 'waiting':
            logger.info("Waiting for an opponent")
            self._trigger_callback('on_waiting')
            
        elif message_type == 'game_start':
            self.session_id = message.get('session_id')
            self.player_number = message.get('player')
            self.game_state = message.get('game_state')
            logger.info(f"Game started. You are player {self.player_number}")
            self._trigger_callback('on_game_start', self.player_number, self.game_state)
            
        elif message_type == 'update':
            self.game_state = message.get('game_state')
            logger.info(f"Game state updated: {self.game_state}")
            self._trigger_callback('on_update', self.game_state)
            
        elif message_type == 'game_end':
            winner = message.get('winner')
            self.game_state = message.get('game_state')
            logger.info(f"Game ended. Winner: {winner}")
            self._trigger_callback('on_game_end', winner, self.game_state)
            
        elif message_type == 'error':
            error_msg = message.get('message')
            logger.error(f"Error from server: {error_msg}")
            self._trigger_callback('on_error', error_msg)
            
        elif message_type == 'opponent_disconnected':
            logger.info("Opponent disconnected")
            self._trigger_callback('on_opponent_disconnect')
            
        elif message_type == 'game_restart':
            self.game_state = message.get('game_state')
            logger.info("Game restarted")
            self._trigger_callback('on_game_restart', self.game_state)
            
    def make_move(self, position: int):
        """Make a move at the specified position"""
        if not self.connected or not self.session_id:
            return False
            
        return self.send_message({
            'type': 'move',
            'session_id': self.session_id,
            'player': self.player_number,
            'position': position
        })
        
    def request_restart(self):
        """Request to restart the game"""
        if not self.connected or not self.session_id:
            return False
            
        return self.send_message({
            'type': 'restart',
            'session_id': self.session_id
        })
        
    def register_callback(self, event_type: str, callback: Callable):
        """Register a callback for an event"""
        if event_type in self.callbacks:
            self.callbacks[event_type].append(callback)
            return True
        return False
        
    def _trigger_callback(self, event_type: str, *args):
        """Trigger all callbacks for an event"""
        if event_type in self.callbacks:
            for callback in self.callbacks[event_type]:
                try:
                    callback(*args)
                except Exception as e:
                    logger.error(f"Error in callback {event_type}: {e}")


class TicTacToeAI:
    """AI opponent for Tic Tac Toe"""
    
    def __init__(self, difficulty='medium'):
        self.difficulty = difficulty  # 'easy', 'medium', or 'hard'
    
    def make_move(self, board: List[int], player_number: int) -> int:
        """Make a move based on the current board state"""
        empty_positions = [i for i, value in enumerate(board) if value == 0]
        
        if not empty_positions:
            return -1  # No valid moves
            
        # Easy: Random move
        if self.difficulty == 'easy':
            return random.choice(empty_positions)
            
        opponent = 1 if player_number == 2 else 2
        
        # Hard: Use minimax
        if self.difficulty == 'hard':
            best_score = float('-inf')
            best_move = -1
            
            for pos in empty_positions:
                # Try this move
                board[pos] = player_number
                score = self._minimax(board, 0, False, player_number, opponent)
                # Undo the move
                board[pos] = 0
                
                if score > best_score:
                    best_score = score
                    best_move = pos
                    
            return best_move
            
        # Medium: Mix of strategies
        # 80% chance to block or win, 20% chance random
        if random.random() < 0.2:
            return random.choice(empty_positions)
            
        # Check for winning move
        for pos in empty_positions:
            board[pos] = player_number
            if self._check_winner(board) == player_number:
                board[pos] = 0
                return pos
            board[pos] = 0
            
        # Check for blocking move
        for pos in empty_positions:
            board[pos] = opponent
            if self._check_winner(board) == opponent:
                board[pos] = 0
                return pos
            board[pos] = 0
            
        # Center is a good strategic position
        if 4 in empty_positions:
            return 4
            
        # Choose a corner
        corners = [pos for pos in [0, 2, 6, 8] if pos in empty_positions]
        if corners:
            return random.choice(corners)
            
        # Choose a side
        sides = [pos for pos in [1, 3, 5, 7] if pos in empty_positions]
        if sides:
            return random.choice(sides)
            
        return random.choice(empty_positions)
        
    def _minimax(self, board: List[int], depth: int, is_maximizing: bool, 
                player: int, opponent: int) -> int:
        """Minimax algorithm for finding the best move"""
        winner = self._check_winner(board)
        
        # Terminal states
        if winner == player:
            return 10 - depth
        elif winner == opponent:
            return depth - 10
        elif 0 not in board:  # Draw
            return 0
            
        if is_maximizing:
            best_score = float('-inf')
            for i in range(9):
                if board[i] == 0:
                    board[i] = player
                    score = self._minimax(board, depth + 1, False, player, opponent)
                    board[i] = 0
                    best_score = max(score, best_score)
            return best_score
        else:
            best_score = float('inf')
            for i in range(9):
                if board[i] == 0:
                    board[i] = opponent
                    score = self._minimax(board, depth + 1, True, player, opponent)
                    board[i] = 0
                    best_score = min(score, best_score)
            return best_score
            
    def _check_winner(self, board: List[int]) -> int:
        """Check if there's a winner on the board"""
        # Check rows
        for i in range(0, 9, 3):
            if board[i] != 0 and board[i] == board[i+1] == board[i+2]:
                return board[i]
                
        # Check columns
        for i in range(3):
            if board[i] != 0 and board[i] == board[i+3] == board[i+6]:
                return board[i]
                
        # Check diagonals
        if board[0] != 0 and board[0] == board[4] == board[8]:
            return board[0]
        if board[2] != 0 and board[2] == board[4] == board[6]:
            return board[2]
            
        return 0  # No winner


class AIGameManager:
    """Manages a local game against AI"""
    
    def __init__(self, difficulty='medium'):
        self.ai = TicTacToeAI(difficulty)
        self.game_state = None
        self.player_number = 1  # Human is always player 1 in AI games
        self.callbacks = {
            'on_game_start': [],
            'on_update': [],
            'on_game_end': [],
            'on_game_restart': []
        }
        self.ai_thinking = False
        self.ai_thread = None
        
    def start_game(self):
        """Start a new game against AI"""
        self.game_state = {
            'board': [0, 0, 0, 0, 0, 0, 0, 0, 0],
            'current_player': 1,
            'game_active': True
        }
        
        logger.info("Game started against AI")
        self._trigger_callback('on_game_start', self.player_number, self.game_state)
        
    def make_move(self, position: int) -> bool:
        """Make a player move at the specified position"""
        if (not self.game_state or 
            not self.game_state['game_active'] or 
            self.game_state['current_player'] != self.player_number or
            self.game_state['board'][position] != 0):
            return False
            
        # Update board with player's move
        self.game_state['board'][position] = self.player_number
        
        # Check for win or draw
        winner = self._check_winner()
        if winner:
            self.game_state['game_active'] = False
            self._trigger_callback('on_game_end', winner, self.game_state)
            return True
            
        # Switch to AI turn
        self.game_state['current_player'] = 2  # AI is always player 2
        self._trigger_callback('on_update', self.game_state)
        
        # Start AI thinking in a separate thread
        if not self.ai_thinking:
            self.ai_thinking = True
            self.ai_thread = threading.Thread(target=self._ai_make_move)
            self.ai_thread.daemon = True
            self.ai_thread.start()
            
        return True
        
    def _ai_make_move(self):
        """AI makes a move (in a separate thread)"""
        # Simulate thinking time for more natural gameplay
        time.sleep(random.uniform(0.5, 1.5))
        
        board_copy = self.game_state['board'].copy()
        ai_move = self.ai.make_move(board_copy, 2)
        
        if ai_move >= 0 and self.game_state['game_active']:
            # Update board with AI's move
            self.game_state['board'][ai_move] = 2
            
            # Check for win or draw
            winner = self._check_winner()
            if winner:
                self.game_state['game_active'] = False
                self._trigger_callback('on_game_end', winner, self.game_state)
            else:
                # Switch back to player turn
                self.game_state['current_player'] = 1
                self._trigger_callback('on_update', self.game_state)
                
        self.ai_thinking = False
        
    def restart_game(self):
        """Restart the game"""
        self.start_game()
        self._trigger_callback('on_game_restart', self.game_state)
        
    def _check_winner(self) -> int:
        """Check if there's a winner or draw"""
        board = self.game_state['board']
        
        # Check rows
        for i in range(0, 9, 3):
            if board[i] != 0 and board[i] == board[i+1] == board[i+2]:
                return board[i]
                
        # Check columns
        for i in range(3):
            if board[i] != 0 and board[i] == board[i+3] == board[i+6]:
                return board[i]
                
        # Check diagonals
        if board[0] != 0 and board[0] == board[4] == board[8]:
            return board[0]
        if board[2] != 0 and board[2] == board[4] == board[6]:
            return board[2]
            
        # Check for draw
        if 0 not in board:
            return 3  # Draw
            
        return 0  # No winner
        
    def register_callback(self, event_type: str, callback: Callable):
        """Register a callback for an event"""
        if event_type in self.callbacks:
            self.callbacks[event_type].append(callback)
            return True
        return False
        
    def _trigger_callback(self, event_type: str, *args):
        """Trigger all callbacks for an event"""
        if event_type in self.callbacks:
            for callback in self.callbacks[event_type]:
                try:
                    callback(*args)
                except Exception as e:
                    logger.error(f"Error in callback {event_type}: {e}")


class PygameTicTacToeGUI:
    """Pygame GUI for the Tic Tac Toe game"""
    
    def __init__(self):
        # Initialize pygame
        pygame.init()
        
        # Constants
        self.WIDTH, self.HEIGHT = 600, 700
        self.LINE_WIDTH = 15
        self.BOARD_SIZE = 3
        self.SQUARE_SIZE = 200
        self.CIRCLE_RADIUS = 60
        self.CIRCLE_WIDTH = 15
        self.X_WIDTH = 20
        self.SPACE = 55
        
        # Colors
        self.WHITE = (255, 255, 255)
        self.BLACK = (0, 0, 0)
        self.RED = (255, 0, 0)
        self.GREEN = (0, 255, 0)
        self.BLUE = (0, 0, 255)
        self.BG_COLOR = (28, 170, 156)
        self.LINE_COLOR = (23, 145, 135)
        self.CIRCLE_COLOR = (239, 231, 200)
        self.X_COLOR = (66, 66, 66)
        self.BUTTON_COLOR = (75, 175, 70)
        self.BUTTON_HOVER_COLOR = (85, 195, 80)
        
        # Set up display
        self.screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT))
        pygame.display.set_caption('Tic Tac Toe - Choose Game Mode')
        self.screen.fill(self.BG_COLOR)
        
        # Font
        self.font = pygame.font.SysFont('Arial', 40)
        self.small_font = pygame.font.SysFont('Arial', 20)
        self.medium_font = pygame.font.SysFont('Arial', 30)
        
        # Game state
        self.status_message = "Select game mode"
        self.can_make_move = False
        self.show_restart_button = False
        self.game_mode = None  # 'ai' or 'online'
        self.ai_difficulty = 'medium'  # 'easy', 'medium', or 'hard'
        self.player_number = None  # 1 or 2 (for online mode)
        
        # Client and AI manager - will be initialized when mode is selected
        self.client = None
        self.ai_manager = None
        
    def setup_online_mode(self):
        """Set up for online multiplayer mode"""
        self.game_mode = 'online'
        self.client = TicTacToeClient()
        
        # Register callbacks
        self.client.register_callback('on_connect', self.on_connect)
        self.client.register_callback('on_waiting', self.on_waiting)
        self.client.register_callback('on_game_start', self.on_game_start)
        self.client.register_callback('on_update', self.on_update)
        self.client.register_callback('on_game_end', self.on_game_end)
        self.client.register_callback('on_error', self.on_error)
        self.client.register_callback('on_disconnect', self.on_disconnect)
        self.client.register_callback('on_opponent_disconnect', self.on_opponent_disconnect)
        self.client.register_callback('on_game_restart', self.on_game_restart)
        
        # Connect to server
        if not self.client.connect():
            self.status_message = "Failed to connect to server"
        else:
            self.status_message = "Connecting to server..."
            
    def setup_ai_mode(self, difficulty='medium'):
        """Set up for playing against AI"""
        self.game_mode = 'ai'
        self.ai_difficulty = difficulty
        self.ai_manager = AIGameManager(difficulty)
        
        # Register callbacks
        self.ai_manager.register_callback('on_game_start', self.on_game_start)
        self.ai_manager.register_callback('on_update', self.on_update)
        self.ai_manager.register_callback('on_game_end', self.on_game_end)
        self.ai_manager.register_callback('on_game_restart', self.on_game_restart)
        
        # Start the game against AI
        self.ai_manager.start_game()
        self.status_message = f"Playing against AI ({difficulty})"
        
    def draw_mode_selection(self):
        """Draw the mode selection screen"""
        title_text = self.font.render("Choose Game Mode", True, self.BLACK)
        title_rect = title_text.get_rect(center=(self.WIDTH // 2, 100))
        self.screen.blit(title_text, title_rect)
        
        # Online button
        online_rect = pygame.Rect(self.WIDTH // 2 - 150, 200, 300, 60)
        pygame.draw.rect(self.screen, self.BUTTON_COLOR, online_rect, border_radius=10)
        
        online_text = self.medium_font.render("Play Online", True, self.WHITE)
        online_text_rect = online_text.get_rect(center=online_rect.center)
        self.screen.blit(online_text, online_text_rect)
        
        # AI buttons (Easy, Medium, Hard)
        ai_text = self.medium_font.render("Play Against AI:", True, self.BLACK)
        ai_text_rect = ai_text.get_rect(center=(self.WIDTH // 2, 300))
        self.screen.blit(ai_text, ai_text_rect)
        
        # Easy
        easy_rect = pygame.Rect(self.WIDTH // 2 - 150, 350, 300, 50)
        pygame.draw.rect(self.screen, self.BUTTON_COLOR, easy_rect, border_radius=10)
        
        easy_text = self.medium_font.render("Easy", True, self.WHITE)
        easy_text_rect = easy_text.get_rect(center=easy_rect.center)
        self.screen.blit(easy_text, easy_text_rect)
        
        # Medium
        medium_rect = pygame.Rect(self.WIDTH // 2 - 150, 420, 300, 50)
        pygame.draw.rect(self.screen, self.BUTTON_COLOR, medium_rect, border_radius=10)
        
        medium_text = self.medium_font.render("Medium", True, self.WHITE)
        medium_text_rect = medium_text.get_rect(center=medium_rect.center)
        self.screen.blit(medium_text, medium_text_rect)
        
        # Hard
        hard_rect = pygame.Rect(self.WIDTH // 2 - 150, 490, 300, 50)
        pygame.draw.rect(self.screen, self.BUTTON_COLOR, hard_rect, border_radius=10)
        
        hard_text = self.medium_font.render("Hard", True, self.WHITE)
        hard_text_rect = hard_text.get_rect(center=hard_rect.center)
        self.screen.blit(hard_text, hard_text_rect)
        
        return {
            'online': online_rect,
            'easy': easy_rect,
            'medium': medium_rect,
            'hard': hard_rect
        }
        
    def draw_lines(self):
        """Draw board grid lines"""
        # Horizontal lines
        pygame.draw.line(self.screen, self.LINE_COLOR, (0, self.SQUARE_SIZE), 
                        (self.WIDTH, self.SQUARE_SIZE), self.LINE_WIDTH)
        pygame.draw.line(self.screen, self.LINE_COLOR, (0, 2 * self.SQUARE_SIZE), 
                        (self.WIDTH, 2 * self.SQUARE_SIZE), self.LINE_WIDTH)
        
        # Vertical lines
        pygame.draw.line(self.screen, self.LINE_COLOR, (self.SQUARE_SIZE, 0), 
                        (self.SQUARE_SIZE, self.HEIGHT - 100), self.LINE_WIDTH)
        pygame.draw.line(self.screen, self.LINE_COLOR, (2 * self.SQUARE_SIZE, 0), 
                        (2 * self.SQUARE_SIZE, self.HEIGHT - 100), self.LINE_WIDTH)
                
    def draw_board(self):
        """Draw the game board with X's and O's"""
        if self.game_mode == 'online' and self.client and self.client.game_state:
            board = self.client.game_state['board']
        elif self.game_mode == 'ai' and self.ai_manager and self.ai_manager.game_state:
            board = self.ai_manager.game_state['board']
        else:
            return
            
        for row in range(self.BOARD_SIZE):
            for col in range(self.BOARD_SIZE):
                index = row * 3 + col
                
                if board[index] == 1:  # Player 1 (X)
                    # Draw X
                    pygame.draw.line(self.screen, self.X_COLOR, 
                                    (col * self.SQUARE_SIZE + self.SPACE, row * self.SQUARE_SIZE + self.SPACE),
                                    (col * self.SQUARE_SIZE + self.SQUARE_SIZE - self.SPACE, 
                                    row * self.SQUARE_SIZE + self.SQUARE_SIZE - self.SPACE),
                                    self.X_WIDTH)
                    pygame.draw.line(self.screen, self.X_COLOR,
                                    (col * self.SQUARE_SIZE + self.SPACE, 
                                    row * self.SQUARE_SIZE + self.SQUARE_SIZE - self.SPACE),
                                    (col * self.SQUARE_SIZE + self.SQUARE_SIZE - self.SPACE, 
                                    row * self.SQUARE_SIZE + self.SPACE),
                                    self.X_WIDTH)
                elif board[index] == 2:  # Player 2 (O)
                    # Draw O
                    pygame.draw.circle(self.screen, self.CIRCLE_COLOR,
                                    (col * self.SQUARE_SIZE + self.SQUARE_SIZE // 2, 
                                    row * self.SQUARE_SIZE + self.SQUARE_SIZE // 2),
                                    self.CIRCLE_RADIUS, self.CIRCLE_WIDTH)
                    
    def draw_status(self):
        """Draw the status area at the bottom"""
        status_rect = pygame.Rect(0, self.HEIGHT - 100, self.WIDTH, 100)
        pygame.draw.rect(self.screen, self.BLACK, status_rect)
        
        text_surface = self.font.render(self.status_message, True, self.WHITE)
        text_rect = text_surface.get_rect(center=(self.WIDTH // 2, self.HEIGHT - 70))
        self.screen.blit(text_surface, text_rect)
        
        if self.show_restart_button:
            button_rect = pygame.Rect(self.WIDTH // 2 - 100, self.HEIGHT - 40, 200, 30)
            pygame.draw.rect(self.screen, self.GREEN, button_rect)
            
            restart_text = self.small_font.render("RESTART GAME", True, self.BLACK)
            restart_text_rect = restart_text.get_rect(center=button_rect.center)
            self.screen.blit(restart_text, restart_text_rect)
            
        # Add back button to return to mode selection when in a game
        if self.game_mode:
            back_rect = pygame.Rect(10, self.HEIGHT - 40, 100, 30)
            pygame.draw.rect(self.screen, self.RED, back_rect)
            
            back_text = self.small_font.render("BACK", True, self.WHITE)
            back_text_rect = back_text.get_rect(center=back_rect.center)
            self.screen.blit(back_text, back_text_rect)
            
            return {'restart': pygame.Rect(self.WIDTH // 2 - 100, self.HEIGHT - 40, 200, 30) if self.show_restart_button else None,
                    'back': back_rect}
        return {'restart': pygame.Rect(self.WIDTH // 2 - 100, self.HEIGHT - 40, 200, 30) if self.show_restart_button else None}
        
    def check_button_click(self, pos, buttons):
        """Check if buttons were clicked"""
        for button_name, button_rect in buttons.items():
            if button_rect and button_rect.collidepoint(pos):
                return button_name
        return None
        
    def check_board_click(self, pos):
        """Handle clicks on the game board"""
        if not self.can_make_move:
            return False
            
        x, y = pos
        
        # Make sure the click is on the board
        if y > self.HEIGHT - 100:
            return False
            
        # Convert screen position to board position
        col = x // self.SQUARE_SIZE
        row = y // self.SQUARE_SIZE
        position = row * 3 + col
        
        # Validate the position
        if row < 0 or row >= self.BOARD_SIZE or col < 0 or col >= self.BOARD_SIZE:
            return False
        
        # Online mode    
        if self.game_mode == 'online' and self.client and self.client.game_state:
            # Check if the position is empty
            if self.client.game_state['board'][position] == 0:
                self.client.make_move(position)
                return True
                
        # AI mode
        elif self.game_mode == 'ai' and self.ai_manager and self.ai_manager.game_state:
            # Check if the position is empty
            if self.ai_manager.game_state['board'][position] == 0:
                self.ai_manager.make_move(position)
                return True
                
        return False
        
    def reset_game(self):
        """Reset the game state and go back to mode selection"""
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
        
    def on_connect(self):
        """Callback when connected to server"""
        self.status_message = "Connected to server. Waiting for opponent..."
        
    def on_waiting(self):
        """Callback when waiting for opponent"""
        self.status_message = "Waiting for an opponent..."
        
    def on_game_start(self, player_number, game_state):
        """Callback when game starts"""
        self.player_number = player_number
        self.status_message = f"You are {'X' if player_number == 1 else 'O'}"
        self.can_make_move = (game_state['current_player'] == player_number)
        self.show_restart_button = False
        
    def on_update(self, game_state):
        """Callback when game state updates"""
        if self.game_mode == 'online':
            self.can_make_move = (game_state['current_player'] == self.player_number)
        elif self.game_mode == 'ai':
            self.can_make_move = (game_state['current_player'] == 1)  # Human is always player 1 in AI mode
            
    def on_game_end(self, winner, game_state):
        """Callback when game ends"""
        if winner == 3:
            self.status_message = "It's a draw!"
        elif winner == self.player_number:
            self.status_message = "You won!"
        else:
            self.status_message = "You lost!"
        self.can_make_move = False
        self.show_restart_button = True
        
    def on_game_restart(self, game_state):
        """Callback when game restarts"""
        self.status_message = "Game restarted!"
        if self.game_mode == 'online':
            self.can_make_move = (game_state['current_player'] == self.player_number)
        elif self.game_mode == 'ai':
            self.can_make_move = (game_state['current_player'] == 1)  # Human is always player 1 in AI mode
        self.show_restart_button = False
        
    def on_error(self, error_msg):
        """Callback when error occurs"""
        self.status_message = f"Error: {error_msg}"
        
    def on_disconnect(self):
        """Callback when disconnected from server"""
        self.status_message = "Disconnected from server"
        self.can_make_move = False
        self.show_restart_button = False
        
    def on_opponent_disconnect(self):
        """Callback when opponent disconnects"""
        self.status_message = "Opponent disconnected"
        self.can_make_move = False
        self.show_restart_button = False
        
    def run(self):
        """Main game loop"""
        clock = pygame.time.Clock()
        running = True
        
        while running:
            self.screen.fill(self.BG_COLOR)
            
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
                        elif clicked_button == 'easy':
                            self.setup_ai_mode('easy')
                        elif clicked_button == 'medium':
                            self.setup_ai_mode('medium')
                        elif clicked_button == 'hard':
                            self.setup_ai_mode('hard')
                    else:
                        clicked_button = self.check_button_click(mouse_pos, status_buttons)
                        if clicked_button == 'restart' and self.show_restart_button:
                            if self.game_mode == 'online' and self.client:
                                self.client.request_restart()
                                self.show_restart_button = False
                            elif self.game_mode == 'ai' and self.ai_manager:
                                self.ai_manager.restart_game()
                                self.show_restart_button = False
                        elif clicked_button == 'back':
                            self.reset_game()
                        else:
                            self.check_board_click(mouse_pos)
                    
            pygame.display.update()
            clock.tick(30)
        
        pygame.quit()

if __name__ == "__main__":
    gui = PygameTicTacToeGUI()
    gui.run()
