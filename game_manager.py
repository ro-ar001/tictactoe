import time
import random
import threading
from typing import Callable, Dict, List, Optional  # Added missing imports
from game_ai import TicTacToeAI

class AIGameManager:
    def _init_(self):
        self.ai = TicTacToeAI()
        self.game_state = None
        self.player_number = 1  # Human is always player 1
        self.callbacks = {
            'on_game_start': [],
            'on_update': [],
            'on_game_end': [],
            'on_game_restart': []
        }
        self.ai_thinking = False
        self.ai_thread = None
        self.training_mode = False

    def start_game(self):
        """Start a new game"""
        self.game_state = {
            'board': [0, 0, 0, 0, 0, 0, 0, 0, 0],
            'current_player': 1,
            'game_active': True
        }
        self._trigger_callback('on_game_start', self.player_number, self.game_state)

    def restart_game(self):
        """Restart the current game"""
        self.start_game()
        self._trigger_callback('on_game_restart', self.game_state)

    def make_move(self, position: int) -> bool:
        """Make a player move at the specified position"""
        if (not self.game_state or 
            not self.game_state['game_active'] or 
            self.game_state['current_player'] != self.player_number or
            self.game_state['board'][position] != 0):
            return False

        # Make the move
        self.game_state['board'][position] = self.player_number
        
        # Check for winner
        winner = self._check_winner()
        if winner:
            self.game_state['game_active'] = False
            self._trigger_callback('on_game_end', winner, self.game_state)
            if self.training_mode:
                reward = 1 if winner == 2 else (-1 if winner == 1 else 0)
                self.ai.update_q_values(reward)
            return True
            
        # Switch to AI turn
        self.game_state['current_player'] = 2
        self._trigger_callback('on_update', self.game_state)
        
        # Start AI move in separate thread
        if not self.ai_thinking:
            self.ai_thinking = True
            self.ai_thread = threading.Thread(target=self._ai_make_move)
            self.ai_thread.daemon = True
            self.ai_thread.start()
            
        return True

    def _ai_make_move(self):
        """AI makes its move"""
        time.sleep(random.uniform(0.5, 1.5))  # Simulate thinking
        
        board_copy = self.game_state['board'].copy()
        ai_move = self.ai.make_move(board_copy, 2)
        
        if ai_move >= 0 and self.game_state['game_active']:
            self.game_state['board'][ai_move] = 2
            
            # Check for winner
            winner = self._check_winner()
            if winner:
                self.game_state['game_active'] = False
                self._trigger_callback('on_game_end', winner, self.game_state)
                if self.training_mode:
                    reward = 1 if winner == 2 else (-1 if winner == 1 else 0)
                    self.ai.update_q_values(reward)
            else:
                # Switch back to player
                self.game_state['current_player'] = 1
                self._trigger_callback('on_update', self.game_state)
                
        self.ai_thinking = False

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
            return 3
        return 0

    def register_callback(self, event_type: str, callback: Callable):
        """Register a callback function"""
        if event_type in self.callbacks:
            self.callbacks[event_type].append(callback)

    def _trigger_callback(self, event_type: str, *args):
        """Trigger all registered callbacks for an event"""
        if event_type in self.callbacks:
            for callback in self.callbacks[event_type]:
                try:
                    callback(*args)
                except Exception as e:
                    print(f"Error in callback {event_type}: {e}")
