import socket
import json
import threading
import pygame
import sys
import logging
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


class PygameTicTacToeGUI:
    """Pygame GUI for the Tic Tac Toe game"""
    
    def __init__(self, client: TicTacToeClient):
        self.client = client
        
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
        
        # Set up display
        self.screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT))
        pygame.display.set_caption('Tic Tac Toe - Network Game')
        self.screen.fill(self.BG_COLOR)
        
        # Font
        self.font = pygame.font.SysFont('Arial', 40)
        self.small_font = pygame.font.SysFont('Arial', 20)
        
        # Game state
        self.status_message = "Connecting to server..."
        self.can_make_move = False
        self.show_restart_button = False
        
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
        if not self.client.game_state:
            return
            
        board = self.client.game_state['board']
        
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
            
    def check_button_click(self, pos):
        """Check if restart button was clicked"""
        if self.show_restart_button:
            button_rect = pygame.Rect(self.WIDTH // 2 - 100, self.HEIGHT - 40, 200, 30)
            if button_rect.collidepoint(pos):
                self.client.request_restart()
                self.show_restart_button = False
                return True
        return False
        
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
            
        # Check if the position is empty
        if self.client.game_state and self.client.game_state['board'][position] == 0:
            self.client.make_move(position)
            return True
            
        return False
        
    def run(self):
        """Main game loop"""
        clock = pygame.time.Clock()
        running = True
        
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    self.client.disconnect()
                    
                if event.type == pygame.MOUSEBUTTONDOWN:
                    mouse_pos = pygame.mouse.get_pos()
                    
                    # Check if restart button clicked
                    if not self.check_button_click(mouse_pos):
                        # If not button, check board click
                        self.check_board_click(mouse_pos)
                        
            # Draw everything
            self.screen.fill(self.BG_COLOR)
            self.draw_lines()
            self.draw_board()
            self.draw_status()
            
            pygame.display.update()
            clock.tick(30)
            
        pygame.quit()
        
    # Callback handlers
    def on_connect(self):
        """Handle connection to server"""
        self.status_message = "Connected to server"
        
    def on_waiting(self):
        """Handle waiting for opponent"""
        self.status_message = "Waiting for an opponent..."
        self.can_make_move = False
        self.show_restart_button = False
        
    def on_game_start(self, player_number: int, game_state: Dict):
        """Handle game start"""
        player_symbol = 'X' if player_number == 1 else 'O'
        self.status_message = f"Game started! You are {player_symbol}"
        
        if game_state['current_player'] == player_number:
            self.status_message = "Your turn"
            self.can_make_move = True
        else:
            self.status_message = "Opponent's turn"
            self.can_make_move = False
            
    def on_update(self, game_state: Dict):
        """Handle game state update"""
        if not game_state['game_active']:
            return
            
        if game_state['current_player'] == self.client.player_number:
            self.status_message = "Your turn"
            self.can_make_move = True
        else:
            self.status_message = "Opponent's turn"
            self.can_make_move = False
            
    def on_game_end(self, winner: int, game_state: Dict):
        """Handle game end"""
        self.can_make_move = False
        
        if winner == self.client.player_number:
            self.status_message = "You won!"
        elif winner == 3:
            self.status_message = "It's a draw!"
        else:
            self.status_message = "You lost!"
            
        # Show restart button
        self.show_restart_button = True
        
    def on_error(self, error_msg: str):
        """Handle error from server"""
        self.status_message = f"Error: {error_msg}"
        
    def on_disconnect(self):
        """Handle disconnection from server"""
        self.status_message = "Disconnected from server"
        self.can_make_move = False
        
    def on_opponent_disconnect(self):
        """Handle opponent disconnection"""
        self.status_message = "Opponent disconnected"
        self.can_make_move = False
        self.show_restart_button = False
        
    def on_game_restart(self, game_state: Dict):
        """Handle game restart"""
        player_text = "Your turn" if game_state['current_player'] == self.client.player_number else "Opponent's turn"
        self.status_message = f"Game restarted! {player_text}"
        self.show_restart_button = False
        
        if game_state['current_player'] == self.client.player_number:
            self.can_make_move = True
        else:
            self.can_make_move = False

if __name__ == "__main__":
    client = TicTacToeClient()
    gui = PygameTicTacToeGUI(client)
    gui.run()