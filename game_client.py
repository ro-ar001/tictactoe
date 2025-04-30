import socket
import json
import threading
import logging
from typing import Dict, List, Optional, Callable

logger = logging.getLogger('TicTacToe-Client')

class TicTacToeClient:
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
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(10)
            self.sock.connect((self.host, self.port))
            self.sock.settimeout(None)
            self.connected = True
            logger.info(f"Connected to server at {self.host}:{self.port}")
            
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
        if self.connected:
            self.connected = False
            if self.sock:
                try:
                    self.sock.close()
                except:
                    pass
            logger.info("Disconnected from server")
            
    def send_message(self, message: Dict):
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
        message_type = message.get('type')
        
        if message_type == 'welcome':
            self._trigger_callback('on_connect')
        elif message_type == 'waiting':
            self._trigger_callback('on_waiting')
        elif message_type == 'game_start':
            self.session_id = message.get('session_id')
            self.player_number = message.get('player')
            self.game_state = message.get('game_state')
            self._trigger_callback('on_game_start', self.player_number, self.game_state)
        elif message_type == 'update':
            self.game_state = message.get('game_state')
            self._trigger_callback('on_update', self.game_state)
        elif message_type == 'game_end':
            winner = message.get('winner')
            self.game_state = message.get('game_state')
            self._trigger_callback('on_game_end', winner, self.game_state)
        elif message_type == 'error':
            error_msg = message.get('message')
            self._trigger_callback('on_error', error_msg)
        elif message_type == 'opponent_disconnected':
            self._trigger_callback('on_opponent_disconnect')
        elif message_type == 'game_restart':
            self.game_state = message.get('game_state')
            self._trigger_callback('on_game_restart', self.game_state)
            
    def make_move(self, position: int):
        if not self.connected or not self.session_id:
            return False
        return self.send_message({
            'type': 'move',
            'session_id': self.session_id,
            'player': self.player_number,
            'position': position
        })
        
    def request_restart(self):
        if not self.connected or not self.session_id:
            return False
        return self.send_message({
            'type': 'restart',
            'session_id': self.session_id
        })
        
    def register_callback(self, event_type: str, callback: Callable):
        if event_type in self.callbacks:
            self.callbacks[event_type].append(callback)
            return True
        return False
        
    def _trigger_callback(self, event_type: str, *args):
        if event_type in self.callbacks:
            for callback in self.callbacks[event_type]:
                try:
                    callback(*args)
                except Exception as e:
                    logger.error(f"Error in callback {event_type}: {e}")
