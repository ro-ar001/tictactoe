import random
import numpy as np
import pickle
import matplotlib.pyplot as plt
from collections import deque

class TicTacToeAI:
    def __init__(self):
        self.q_table = {}
        self.epsilon = 1.0  # Exploration rate
        self.epsilon_min = 0.01
        self.epsilon_decay = 0.995
        self.learning_rate = 0.1
        self.discount_factor = 0.95
        self.reward_history = []  # Track rewards per episode
        self.move_history = []
        
    def get_state_key(self, board: list) -> str:
        return ''.join(map(str, board))
        
    def make_move(self, board: list, player_number: int) -> int:
        state_key = self.get_state_key(board)
        empty_positions = [i for i, value in enumerate(board) if value == 0]
        
        if not empty_positions:
            return -1
            
        if state_key not in self.q_table:
            self.q_table[state_key] = {pos: 0 for pos in empty_positions}
            
        if np.random.random() < self.epsilon:
            move = random.choice(empty_positions)
            self.move_history.append((state_key, move, 0))
            return move
            
        q_values = self.q_table[state_key]
        move = max(q_values, key=q_values.get)
        self.move_history.append((state_key, move, 1))
        return move
        
    def update_q_values(self, reward: float):
        for i in range(len(self.move_history)-1, -1, -1):
            state, move, _ = self.move_history[i]
            next_state = self.move_history[i+1][0] if i < len(self.move_history)-1 else None
            max_next_q = max(self.q_table[next_state].values()) if next_state and next_state in self.q_table else 0
            
            self.q_table[state][move] = (1 - self.learning_rate) * self.q_table[state][move] + \
                                       self.learning_rate * (reward + self.discount_factor * max_next_q)
            
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)
        self.move_history = []
        self.reward_history.append(reward)  # Store the reward
        
    def save_training_data(self):
        with open('ai_training_data.pkl', 'wb') as f:
            pickle.dump(self.reward_history, f)
            
    def plot_training(self):
        if not self.reward_history:
            return
            
        plt.figure(figsize=(12, 6))
        episodes = range(1, len(self.reward_history) + 1)
        
        # Plot raw rewards
        plt.scatter(episodes, self.reward_history, alpha=0.3, label='Per-Episode Reward')
        
        # Plot moving average
        window_size = 50
        moving_avg = []
        for i in range(len(self.reward_history)):
            start = max(0, i - window_size)
            moving_avg.append(np.mean(self.reward_history[start:i+1]))
        
        plt.plot(episodes, moving_avg, color='red', 
                label=f'{window_size}-Episode Moving Average')
        
        plt.title('Deep Reinforcement Learning Progress')
        plt.xlabel('Episode Number')
        plt.ylabel('Reward')
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.show()
