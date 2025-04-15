import socket
import json
import threading
import tkinter as tk
from tkinter import messagebox
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


class TicTacToeGUI:
    """GUI for the Tic Tac Toe game"""
    
    def __init__(self, client: TicTacToeClient):
        self.client = client
        self.root = tk.Tk()
        self.root.title("Tic Tac Toe")
        self.root.geometry("400x500")
        self.root.resizable(False, False)
        
        self.status_label = tk.Label(self.root, text="Connecting to server...", font=("Arial", 12))
        self.status_label.pack(pady=10)
        
        # Game board frame
        self.board_frame = tk.Frame(self.root)
        self.board_frame.pack(pady=20)
        
        # Create the grid of buttons
        self.buttons = []
        for i in range(3):
            row = []
            for j in range(3):
                button = tk.Button(self.board_frame, text="", font=("Arial", 24), width=5, height=2,
                                  command=lambda pos=i*3+j: self.on_cell_click(pos))
                button.grid(row=i, column=j, padx=5, pady=5)
                row.append(button)
            self.buttons.append(row)
            
        # Restart button (initially hidden)
        self.restart_button = tk.Button(self.root, text="Restart Game", font=("Arial", 12),
                                      command=self.request_restart)
        
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
            self.status_label.config(text="Failed to connect to server")
            
        # Window close handler
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
    def run(self):
        """Start the GUI event loop"""
        self.root.mainloop()
        
    def update_board(self, board: List[int]):
        """Update the board display based on current state"""
        symbols = {0: "", 1: "X", 2: "O"}
        
        for i in range(3):
            for j in range(3):
                index = i * 3 + j
                self.buttons[i][j].config(text=symbols[board[index]])
                
                # Color coding
                if board[index] == 0:
                    self.buttons[i][j].config(bg="SystemButtonFace")  # Default color
                elif board[index] == 1:
                    self.buttons[i][j].config(bg="#ffe6e6")  # Light red for X
                else:
                    self.buttons[i][j].config(bg="#e6f2ff")  # Light blue for O
                    
    def disable_board(self):
        """Disable all board buttons"""
        for i in range(3):
            for j in range(3):
                self.buttons[i][j].config(state=tk.DISABLED)
                
    def enable_board(self):
        """Enable all empty board buttons"""
        board = self.client.game_state['board']
        for i in range(3):
            for j in range(3):
                index = i * 3 + j
                if board[index] == 0:
                    self.buttons[i][j].config(state=tk.NORMAL)
                else:
                    self.buttons[i][j].config(state=tk.DISABLED)
                    
    def on_cell_click(self, position: int):
        """Handle a cell click"""
        # Check if it's this player's turn
        if (self.client.game_state['current_player'] != self.client.player_number or
            not self.client.game_state['game_active']):
            return
            
        self.client.make_move(position)
        
    def request_restart(self):
        """Request to restart the game"""
        self.client.request_restart()
        self.restart_button.pack_forget()  # Hide the restart button after clicking
        
    # Callback handlers
    def on_connect(self):
        """Handle connection to server"""
        self.status_label.config(text="Connected to server")
        
    def on_waiting(self):
        """Handle waiting for opponent"""
        self.status_label.config(text="Waiting for an opponent...")
        self.disable_board()
        self.restart_button.pack_forget()  # Hide restart button while waiting
        
    def on_game_start(self, player_number: int, game_state: Dict):
        """Handle game start"""
        self.status_label.config(text=f"Game started! You are {'X' if player_number == 1 else 'O'}")
        self.update_board(game_state['board'])
        
        if game_state['current_player'] == player_number:
            self.status_label.config(text=f"Your turn")
            self.enable_board()
        else:
            self.status_label.config(text=f"Opponent's turn")
            self.disable_board()
            
    def on_update(self, game_state: Dict):
        """Handle game state update"""
        self.update_board(game_state['board'])
        
        if not game_state['game_active']:
            return
            
        if game_state['current_player'] == self.client.player_number:
            self.status_label.config(text="Your turn")
            self.enable_board()
        else:
            self.status_label.config(text="Opponent's turn")
            self.disable_board()
            
    def on_game_end(self, winner: int, game_state: Dict):
        """Handle game end"""
        self.update_board(game_state['board'])
        self.disable_board()
        
        if winner == self.client.player_number:
            self.status_label.config(text="You won!")
        elif winner == 3:
            self.status_label.config(text="It's a draw!")
        else:
            self.status_label.config(text="You lost!")
            
        # Show restart button
        self.restart_button.pack(pady=10)
        
    def on_error(self, error_msg: str):
        """Handle error from server"""
        messagebox.showerror("Error", error_msg)
        
    def on_disconnect(self):
        """Handle disconnection from server"""
        self.status_label.config(text="Disconnected from server")
        self.disable_board()
        messagebox.showinfo("Disconnected", "Lost connection to server")
        
    def on_opponent_disconnect(self):
        """Handle opponent disconnection"""
        self.status_label.config(text="Opponent disconnected")
        self.disable_board()
        messagebox.showinfo("Opponent Disconnected", "Your opponent has disconnected from the game")
        # Hide restart button as it's not useful without an opponent
        self.restart_button.pack_forget()
        
    def on_game_restart(self, game_state: Dict):
        """Handle game restart"""
        self.status_label.config(text=f"Game restarted! {'Your turn' if game_state['current_player'] == self.client.player_number else 'Opponent\'s turn'}")
        self.update_board(game_state['board'])
        self.restart_button.pack_forget()  # Hide restart button after restart
        
        if game_state['current_player'] == self.client.player_number:
            self.enable_board()
        else:
            self.disable_board()
    
    def on_close(self):
        """Handle window close event"""
        if messagebox.askokcancel("Quit", "Do you want to quit the game?"):
            self.client.disconnect()
            self.root.destroy()


if __name__ == "__main__":
    client = TicTacToeClient()
    gui = TicTacToeGUI(client)
    gui.run()