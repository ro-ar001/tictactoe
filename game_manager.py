import os
import time
import random
import pickle
import threading
from typing import Callable, Dict, List, Optional
from game_ai import TicTacToeAI

class AIGameManager:
    def __init__(self):
        self.ai = TicTacToeAI()
        self.load_ai_qtable()
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

    def load_ai_qtable(self):
        if os.path.exists('ai_qtable.pkl'):
            try:
                with open('ai_qtable.pkl', 'rb') as f:
                    self.ai.q_table = pickle.load(f)
                self.ai.epsilon = 0  # Exploit learned policy
                print("✅ Loaded trained AI Q-table.")
            except Exception as e:
                print(f"⚠️ Failed to load Q-table: {e}")

    def start_game(self):
        self.game_state = {
            'board': [0] * 9,
            'current_player': 1,
            'game_active': True
        }
        self._trigger_callback('on_game_start', self.player_number, self.game_state)

    def restart_game(self):
        self.start_game()
        self._trigger_callback('on_game_restart', self.game_state)

    def make_move(self, position: int) -> bool:
        if (not self.game_state or 
            not self.game_state['game_active'] or 
            self.game_state['current_player'] != self.player_number or
            self.game_state['board'][position] != 0):
            return False

        self.game_state['board'][position] = self.player_number

        winner = self._check_winner()
        if winner:
            self.game_state['game_active'] = False
            self._trigger_callback('on_game_end', winner, self.game_state)
            if self.training_mode:
                reward = 1 if winner == 2 else (-1 if winner == 1 else 0)
                self.ai.update_q_values(reward)
            return True

        self.game_state['current_player'] = 2
        self._trigger_callback('on_update', self.game_state)

        if not self.ai_thinking:
            self.ai_thinking = True
            self.ai_thread = threading.Thread(target=self._ai_make_move)
            self.ai_thread.daemon = True
            self.ai_thread.start()

        return True

    def _ai_make_move(self):
        time.sleep(random.uniform(0.5, 1.5))
        board_copy = self.game_state['board'].copy()
        ai_move = self.ai.make_move(board_copy, 2)

        if ai_move >= 0 and self.game_state['game_active']:
            self.game_state['board'][ai_move] = 2
            winner = self._check_winner()
            if winner:
                self.game_state['game_active'] = False
                self._trigger_callback('on_game_end', winner, self.game_state)
                if self.training_mode:
                    reward = 1 if winner == 2 else (-1 if winner == 1 else 0)
                    self.ai.update_q_values(reward)
            else:
                self.game_state['current_player'] = 1
                self._trigger_callback('on_update', self.game_state)

        self.ai_thinking = False

    def _check_winner(self) -> int:
        board = self.game_state['board']
        for i in range(0, 9, 3):
            if board[i] != 0 and board[i] == board[i+1] == board[i+2]:
                return board[i]
        for i in range(3):
            if board[i] != 0 and board[i] == board[i+3] == board[i+6]:
                return board[i]
        if board[0] != 0 and board[0] == board[4] == board[8]:
            return board[0]
        if board[2] != 0 and board[2] == board[4] == board[6]:
            return board[2]
        if 0 not in board:
            return 3
        return 0

    def register_callback(self, event_type: str, callback: Callable):
        if event_type in self.callbacks:
            self.callbacks[event_type].append(callback)

    def _trigger_callback(self, event_type: str, *args):
        if event_type in self.callbacks:
            for callback in self.callbacks[event_type]:
                try:
                    callback(*args)
                except Exception as e:
                    print(f"Error in callback {event_type}: {e}")
