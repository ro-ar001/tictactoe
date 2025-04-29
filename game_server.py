import socket
import json
import threading
import logging
import random
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('TicTacToe-Server')

class GameSession:
    """Class to manage individual game sessions"""
    def _init_(self, session_id: str, player1: socket.socket, player2: socket.socket):
        self.session_id = session_id
        self.players = {1: player1, 2: player2}
        self.board = [0] * 9
        self.current_player = 1
        self.game_active = True

    def get_state(self) -> Dict:
        """Return current game state"""
        return {
            'board': self.board.copy(),
            'current_player': self.current_player,
            'game_active': self.game_active
        }

    def make_move(self, player: int, position: int) -> bool:
        """Process a player move"""
        if not self.game_active or player != self.current_player:
            return False
            
        if self.board[position] != 0:
            return False
            
        self.board[position] = player
        winner = self.check_winner()
        
        if winner or 0 not in self.board:
            self.game_active = False
            
        self.current_player = 2 if self.current_player == 1 else 1
        return True

    def check_winner(self) -> Optional[int]:
        """Check for winner returns player number or 3 for draw"""
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
        
        # Check for draw
        if 0 not in self.board:
            return 3
            
        return None

class ServerClientHandler(threading.Thread):
    """Handle client connections"""
    def _init_(self, conn: socket.socket, addr: tuple, server):
        super()._init_()
        self.conn = conn
        self.addr = addr
        self.server = server
        self.player_number = None
        self.session_id = None

    def run(self):
        """Main client handling loop"""
        try:
            buffer = ""
            while True:
                data = self.conn.recv(1024).decode('utf-8')
                if not data:
                    break
                    
                buffer += data
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    self.handle_message(json.loads(line))
                    
        except ConnectionResetError:
            logger.info(f"Client {self.addr} disconnected")
        finally:
            self.handle_disconnect()

    def handle_message(self, message: Dict):
        """Process client messages"""
        msg_type = message.get('type')
        
        if msg_type == 'join':
            self.handle_join()
        elif msg_type == 'move':
            self.handle_move(message)
        elif msg_type == 'restart':
            self.handle_restart()

    def handle_join(self):
        """Handle new player joining"""
        if self.server.queue:
            # Start new game with queued player
            opponent = self.server.queue.pop()
            session_id = str(random.randint(1000, 9999))
            player_numbers = {self: 1, opponent: 2}
            
            for handler in [self, opponent]:
                handler.session_id = session_id
                handler.player_number = player_numbers[handler]
                handler.send_message({
                    'type': 'game_start',
                    'session_id': session_id,
                    'player': handler.player_number,
                    'game_state': {
                        'board': [0]*9,
                        'current_player': 1,
                        'game_active': True
                    }
                })
            
            self.server.sessions[session_id] = GameSession(
                session_id, self.conn, opponent.conn
            )
            
        else:
            # Add to queue
            self.server.queue.append(self)
            self.send_message({'type': 'waiting'})

    def handle_move(self, message: Dict):
        """Process game move"""
        session = self.server.sessions.get(self.session_id)
        if not session:
            return
            
        position = message.get('position')
        if session.make_move(self.player_number, position):
            # Update both players
            game_state = session.get_state()
            winner = session.check_winner()
            
            for player_num in [1, 2]:
                self.server.send_to_player(
                    self.session_id,
                    player_num,
                    {
                        'type': 'update',
                        'game_state': game_state
                    }
                )
                
            if winner is not None:
                self.handle_game_end(winner)

    def handle_game_end(self, winner: int):
        """Handle game conclusion"""
        session = self.server.sessions[self.session_id]
        for player_num in [1, 2]:
            self.server.send_to_player(
                self.session_id,
                player_num,
                {
                    'type': 'game_end',
                    'winner': winner,
                    'game_state': session.get_state()
                }
            )

    def handle_restart(self):
        """Handle game restart request"""
        session = self.server.sessions.get(self.session_id)
        if session:
            # Reset game state
            session.board = [0]*9
            session.current_player = 1
            session.game_active = True
            
            for player_num in [1, 2]:
                self.server.send_to_player(
                    self.session_id,
                    player_num,
                    {
                        'type': 'game_restart',
                        'game_state': session.get_state()
                    }
                )

    def handle_disconnect(self):
        """Handle client disconnection"""
        if self.session_id:
            session = self.server.sessions.get(self.session_id)
            if session:
                # Notify other player
                other_player = 2 if self.player_number == 1 else 1
                self.server.send_to_player(
                    self.session_id,
                    other_player,
                    {'type': 'opponent_disconnected'}
                )
                del self.server.sessions[self.session_id]
        
        if self in self.server.queue:
            self.server.queue.remove(self)
            
        self.conn.close()

    def send_message(self, message: Dict):
        """Send message to client"""
        try:
            self.conn.sendall((json.dumps(message) + '\n').encode('utf-8'))
        except:
            pass

class TicTacToeServer:
    """Main server class"""
    def _init_(self, host: str = '0.0.0.0', port: int = 5555):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sessions: Dict[str, GameSession] = {}
        self.queue: List[ServerClientHandler] = []
        
    def start(self):
        """Start the server"""
        self.sock.bind((self.host, self.port))
        self.sock.listen(5)
        logger.info(f"Server listening on {self.host}:{self.port}")
        
        try:
            while True:
                conn, addr = self.sock.accept()
                logger.info(f"New connection from {addr}")
                handler = ServerClientHandler(conn, addr, self)
                handler.start()
        except KeyboardInterrupt:
            logger.info("Shutting down server")
        finally:
            self.sock.close()

    def send_to_player(self, session_id: str, player_num: int, message: Dict):
        """Send message to specific player in a session"""
        session = self.sessions.get(session_id)
        if not session:
            return
            
        handler = next(
            (h for h in self.queue if h.session_id == session_id and h.player_number == player_num),
            None
        )
        
        if handler:
            handler.send_message(message)

if _name_ == "_main_":
    server = TicTacToeServer()
    server.start()
