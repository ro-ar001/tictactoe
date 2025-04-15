import socket
import threading
import json
import logging
from typing import Dict, List, Tuple, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('TicTacToe-Server')

class GameSession:
    """Manages a game session between two players"""
    
    def __init__(self, session_id: str, player1_conn, player1_addr):
        self.session_id = session_id
        self.player1 = (player1_conn, player1_addr)
        self.player2 = None
        self.current_player = 1  # Player 1 starts
        self.board = [0] * 9  # 0: empty, 1: player1, 2: player2
        self.game_active = True
        logger.info(f"Game session {session_id} created")
        
    def add_player2(self, player2_conn, player2_addr):
        """Add the second player to the game session"""
        self.player2 = (player2_conn, player2_addr)
        logger.info(f"Player 2 joined session {self.session_id}")
        
    def is_full(self) -> bool:
        """Check if the session has two players"""
        return self.player2 is not None
        
    def make_move(self, player: int, position: int) -> bool:
        """Process a player's move"""
        if not self.game_active:
            return False
            
        if player != self.current_player:
            return False
            
        if position < 0 or position > 8 or self.board[position] != 0:
            return False
            
        # Update the board
        self.board[position] = player
        
        # Switch player turn
        self.current_player = 3 - player  # Toggle between 1 and 2
        
        # Check for win or draw
        winner = self.check_winner()
        if winner:
            self.game_active = False
            
        return True
        
    def check_winner(self) -> Optional[int]:
        """Check if there's a winner or draw
        Returns:
            0 for no winner (game continues)
            1 or 2 for player 1 or 2 win
            3 for draw
        """
        # Check rows
        for i in range(0, 9, 3):
            if self.board[i] != 0 and self.board[i] == self.board[i+1] == self.board[i+2]:
                return self.board[i]
                
        # Check columns
        for i in range(3):
            if self.board[i] != 0 and self.board[i] == self.board[i+3] == self.board[i+6]:
                return self.board[i]
                
        # Check diagonals
        if self.board[0] != 0 and self.board[0] == self.board[4] == self.board[8]:
            return self.board[0]
            
        if self.board[2] != 0 and self.board[2] == self.board[4] == self.board[6]:
            return self.board[2]
            
        # Check for draw (board full)
        if 0 not in self.board:
            return 3
            
        return 0  # Game continues
        
    def get_game_state(self) -> Dict:
        """Return the current game state as a dictionary"""
        winner = self.check_winner()
        return {
            'session_id': self.session_id,
            'board': self.board,
            'current_player': self.current_player,
            'game_active': self.game_active,
            'winner': winner
        }
        
    def reset_game(self):
        """Reset the game to start a new round"""
        self.board = [0] * 9
        self.current_player = 1
        self.game_active = True

class TicTacToeServer:
    """Server for Tic Tac Toe game"""
    
    def __init__(self, host: str = '0.0.0.0', port: int = 5555):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sessions: Dict[str, GameSession] = {}
        self.waiting_player = None
        self.next_session_id = 1
        self.running = True
        
    def start(self):
        """Start the server"""
        try:
            self.sock.bind((self.host, self.port))
            self.sock.listen(5)
            self.sock.settimeout(1.0)  # Add timeout to allow for clean shutdown
            logger.info(f"Server started on {self.host}:{self.port}")
            
            while self.running:
                try:
                    client_sock, client_addr = self.sock.accept()
                    logger.info(f"New connection from {client_addr}")
                    client_thread = threading.Thread(target=self.handle_client, args=(client_sock, client_addr))
                    client_thread.daemon = True
                    client_thread.start()
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        logger.error(f"Error accepting connection: {e}")
        except KeyboardInterrupt:
            logger.info("Server shutting down...")
        finally:
            self.cleanup()
            
    def cleanup(self):
        """Clean up resources when shutting down"""
        self.running = False
        # Close all client connections
        for session_id, session in list(self.sessions.items()):
            try:
                session.player1[0].close()
                if session.player2:
                    session.player2[0].close()
            except:
                pass
        # Close server socket
        self.sock.close()
        logger.info("Server shut down completed")
            
    def handle_client(self, client_sock: socket.socket, client_addr):
        """Handle a client connection"""
        client_sock.settimeout(None)  # No timeout for client sockets
        try:
            # Send welcome message
            self.send_message(client_sock, {'type': 'welcome', 'message': 'Connected to Tic Tac Toe server'})
            
            # If no waiting player, this client becomes the waiting player
            if self.waiting_player is None:
                self.waiting_player = (client_sock, client_addr)
                self.send_message(client_sock, {'type': 'waiting', 'message': 'Waiting for opponent'})
            else:
                # Create a new game session with waiting player and this client
                session_id = f"game_{self.next_session_id}"
                self.next_session_id += 1
                
                waiting_sock, waiting_addr = self.waiting_player
                session = GameSession(session_id, waiting_sock, waiting_addr)
                session.add_player2(client_sock, client_addr)
                self.sessions[session_id] = session
                
                # Inform both players the game is starting
                self.send_message(waiting_sock, {
                    'type': 'game_start',
                    'session_id': session_id,
                    'player': 1,
                    'game_state': session.get_game_state()
                })
                
                self.send_message(client_sock, {
                    'type': 'game_start',
                    'session_id': session_id,
                    'player': 2,
                    'game_state': session.get_game_state()
                })
                
                self.waiting_player = None
                
            # Main client loop
            buffer = ""
            while self.running:
                try:
                    data = client_sock.recv(1024).decode('utf-8')
                    if not data:
                        # Connection closed by client
                        break
                        
                    buffer += data
                    
                    # Process complete messages
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        if line:
                            try:
                                message = json.loads(line)
                                self.process_message(message, client_sock, client_addr)
                            except json.JSONDecodeError:
                                logger.error(f"Invalid JSON from {client_addr}: {line}")
                except ConnectionResetError:
                    logger.error(f"Connection reset by client {client_addr}")
                    break
                except Exception as e:
                    logger.error(f"Error receiving data from {client_addr}: {e}")
                    break
                
        except Exception as e:
            logger.error(f"Error handling client {client_addr}: {e}")
        finally:
            # Handle disconnection
            self.handle_disconnect(client_sock, client_addr)
            try:
                client_sock.close()
            except:
                pass
            
    def process_message(self, message: Dict, client_sock: socket.socket, client_addr):
        """Process a message from a client"""
        message_type = message.get('type')
        
        if message_type == 'move':
            session_id = message.get('session_id')
            player = message.get('player')
            position = message.get('position')
            
            if session_id in self.sessions:
                session = self.sessions[session_id]
                
                # Validate this client is in this session
                is_player1 = session.player1[0] == client_sock
                is_player2 = session.player2 and session.player2[0] == client_sock
                
                if (is_player1 and player == 1) or (is_player2 and player == 2):
                    # Process the move
                    if session.make_move(player, position):
                        # Move successful, broadcast the updated state
                        game_state = session.get_game_state()
                        self.send_message(session.player1[0], {
                            'type': 'update',
                            'game_state': game_state
                        })
                        self.send_message(session.player2[0], {
                            'type': 'update',
                            'game_state': game_state
                        })
                        
                        # Check if game ended
                        winner = session.check_winner()
                        if winner:
                            result_message = {
                                'type': 'game_end',
                                'winner': winner,
                                'game_state': game_state
                            }
                            self.send_message(session.player1[0], result_message)
                            self.send_message(session.player2[0], result_message)
                    else:
                        # Invalid move
                        self.send_message(client_sock, {
                            'type': 'error',
                            'message': 'Invalid move'
                        })
                else:
                    self.send_message(client_sock, {
                        'type': 'error',
                        'message': 'Not your turn or not in this session'
                    })
                    
        elif message_type == 'restart':
            session_id = message.get('session_id')
            if session_id in self.sessions:
                session = self.sessions[session_id]
                session.reset_game()
                
                restart_message = {
                    'type': 'game_restart',
                    'game_state': session.get_game_state()
                }
                self.send_message(session.player1[0], restart_message)
                self.send_message(session.player2[0], restart_message)
                
    def send_message(self, client_sock: socket.socket, message: Dict):
        """Send a message to a client"""
        try:
            client_sock.sendall((json.dumps(message) + '\n').encode('utf-8'))
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            
    def handle_disconnect(self, client_sock: socket.socket, client_addr):
        """Handle a client disconnection"""
        logger.info(f"Client {client_addr} disconnected")
        
        # If this was the waiting player, clear waiting player
        if self.waiting_player and self.waiting_player[0] == client_sock:
            self.waiting_player = None
            return
            
        # Check if this client is in a game session
        for session_id, session in list(self.sessions.items()):
            if session.player1[0] == client_sock:
                if session.player2:
                    # Notify other player
                    self.send_message(session.player2[0], {
                        'type': 'opponent_disconnected',
                        'message': 'Your opponent has disconnected'
                    })
                # Remove the session
                del self.sessions[session_id]
                break
                
            if session.player2 and session.player2[0] == client_sock:
                # Notify other player
                self.send_message(session.player1[0], {
                    'type': 'opponent_disconnected',
                    'message': 'Your opponent has disconnected'
                })
                # Remove the session
                del self.sessions[session_id]
                break

if __name__ == "__main__":
    server = TicTacToeServer()
    server.start()