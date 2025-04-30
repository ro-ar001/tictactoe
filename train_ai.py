import numpy as np
import time
import os
import matplotlib.pyplot as plt
from tqdm import tqdm
import random
import pickle
from game_ai import TicTacToeAI

class TicTacToeEnvironment:
    """Tic-Tac-Toe environment for training AI agents"""
    
    def __init__ (self):
        self.board = [0] * 9
        self.current_player = 1
        self.game_active = True
        
    def reset(self):
        """Reset the game board to initial state"""
        self.board = [0] * 9
        self.current_player = 1
        self.game_active = True
        return self.board.copy()
        
    def step(self, position):
        """Make a move and return the new state, reward, done"""
        if not self.game_active or position < 0 or position > 8 or self.board[position] != 0:
            return self.board.copy(), -1, True  # Invalid move, penalize
            
        # Make the move
        self.board[position] = self.current_player
        
        # Check for winner
        winner = self.check_winner()
        if winner:
            # Game ended
            self.game_active = False
            if winner == 3:  # Draw
                return self.board.copy(), 0.5, True
            elif winner == self.current_player:  # Win
                return self.board.copy(), 1, True
            else:  # Lose (shouldn't happen in this implementation)
                return self.board.copy(), -1, True
                
        # Switch player
        self.current_player = 3 - self.current_player  # Toggle between 1 and 2
        return self.board.copy(), 0, False  # Game continues
        
    def check_winner(self):
        """Check if there's a winner or a draw
        Returns:
            0: Game continues
            1 or 2: Player number who won
            3: Draw
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

    def get_valid_moves(self):
        """Get all valid moves (empty positions)"""
        return [i for i, val in enumerate(self.board) if val == 0]
    
    def render(self):
        """Render the board to console"""
        symbols = {0: ' ', 1: 'X', 2: 'O'}
        print("-" * 13)
        for i in range(0, 9, 3):
            print(f"| {symbols[self.board[i]]} | {symbols[self.board[i+1]]} | {symbols[self.board[i+2]]} |")
            print("-" * 13)

class SelfPlayTrainer:
    """Trains the AI through self-play"""
    
    def __init__(self, num_episodes=10000, save_interval=1000):
        self.num_episodes = num_episodes
        self.save_interval = save_interval
        self.env = TicTacToeEnvironment()
        self.ai = TicTacToeAI()
        self.opponent_ai = TicTacToeAI()
        
        # Try to load existing AI if available
        self.load_ai()
        
    def load_ai(self):
        """Load existing AI Q-table if available"""
        if os.path.exists('ai_qtable.pkl'):
            try:
                with open('ai_qtable.pkl', 'rb') as f:
                    self.ai.q_table = pickle.load(f)
                print("Loaded existing AI Q-table")
                
                # Copy to opponent for more competitive self-play
                self.opponent_ai.q_table = dict(self.ai.q_table)
                self.opponent_ai.epsilon = 0.2  # More exploitation for opponent
                
            except Exception as e:
                print(f"Error loading AI Q-table: {e}")
    
    def save_ai(self):
        """Save the AI Q-table"""
        with open('ai_qtable.pkl', 'wb') as f:
            pickle.dump(self.ai.q_table, f)
            
        # Also save the training data for visualization
        self.ai.save_training_data()
            
    def train(self):
        """Train the AI through self-play"""
        print("Starting AI training through self-play...")
        
        # Metrics tracking
        win_count = 0
        draw_count = 0
        loss_count = 0
        win_rates = []
        
        # Use tqdm for progress bar
        for episode in tqdm(range(1, self.num_episodes + 1)):
            state = self.env.reset()
            done = False
            
            # Play until game is done
            while not done:
                # Get action based on current player
                if self.env.current_player == 1:  # Main AI
                    action = self.ai.make_move(state, 1)
                else:  # Opponent AI
                    action = self.opponent_ai.make_move(state, 2)
                
                # Take action
                next_state, reward, done = self.env.step(action)
                
                # Record to move history for the AI agent
                if self.env.current_player == 2:  # Just moved with player 1 (main AI)
                    pass  # The move is already recorded in make_move()
                
                # Game ended, update Q-values only if main AI played last
                if done:
                    if self.env.check_winner() == 1:  # Main AI won
                        self.ai.update_q_values(1)
                        win_count += 1
                    elif self.env.check_winner() == 2:  # Opponent won
                        self.ai.update_q_values(-1)
                        loss_count += 1
                    else:  # Draw
                        self.ai.update_q_values(0.5)
                        draw_count += 1
                        
                # Update state
                state = next_state
            
            # Occasionally save AI progress and print stats
            if episode % self.save_interval == 0:
                win_rate = win_count / self.save_interval * 100
                draw_rate = draw_count / self.save_interval * 100
                loss_rate = loss_count / self.save_interval * 100
                
                print(f"\nEpisode {episode}/{self.num_episodes}")
                print(f"Win Rate: {win_rate:.2f}%, Draw Rate: {draw_rate:.2f}%, Loss Rate: {loss_rate:.2f}%")
                print(f"Exploration rate (epsilon): {self.ai.epsilon:.4f}")
                print(f"Q-table size: {len(self.ai.q_table)} states")
                
                win_rates.append(win_rate)
                win_count, draw_count, loss_count = 0, 0, 0
                
                # Save AI
                self.save_ai()
                
                # Update opponent AI with current knowledge but keep higher exploration
                if episode > self.num_episodes // 2:
                    self.opponent_ai.q_table = dict(self.ai.q_table)
                    self.opponent_ai.epsilon = max(0.1, self.ai.epsilon + 0.1)
        
        # Final save
        self.save_ai()
        
        # Plot training progress
        self.plot_training_progress(win_rates)
        
    def plot_training_progress(self, win_rates):
        """Plot the training progress"""
        plt.figure(figsize=(12, 6))
        plt.plot(range(self.save_interval, self.num_episodes + 1, self.save_interval), win_rates, 'b-')
        plt.title('AI Training Progress')
        plt.xlabel('Episodes')
        plt.ylabel('Win Rate (%)')
        plt.grid(True)
        plt.savefig('training_progress.png')
        plt.close()
        
    def evaluate(self, num_games=100):
        """Evaluate the trained AI against a random player"""
        print("\nEvaluating AI against random player...")
        
        # Set epsilon to 0 for pure exploitation during evaluation
        original_epsilon = self.ai.epsilon
        self.ai.epsilon = 0
        
        win_count = 0
        draw_count = 0
        loss_count = 0
        
        for _ in tqdm(range(num_games)):
            state = self.env.reset()
            done = False
            
            while not done:
                if self.env.current_player == 1:  # AI's turn
                    action = self.ai.make_move(state, 1)
                else:  # Random player
                    valid_moves = self.env.get_valid_moves()
                    action = random.choice(valid_moves) if valid_moves else -1
                
                state, _, done = self.env.step(action)
            
            # Check result
            winner = self.env.check_winner()
            if winner == 1:  # AI won
                win_count += 1
            elif winner == 2:  # Random player won
                loss_count += 1
            else:  # Draw
                draw_count += 1
        
        # Report results
        print(f"\nEvaluation results against random player (over {num_games} games):")
        print(f"Win Rate: {win_count/num_games*100:.2f}%")
        print(f"Draw Rate: {draw_count/num_games*100:.2f}%")
        print(f"Loss Rate: {loss_count/num_games*100:.2f}%")
        
        # Restore original epsilon
        self.ai.epsilon = original_epsilon

def main():
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='Train Tic-Tac-Toe AI')
    parser.add_argument('--episodes', type=int, default=10000, help='Number of training episodes')
    parser.add_argument('--save-interval', type=int, default=1000, help='Save interval')
    parser.add_argument('--evaluate', action='store_true', help='Evaluate after training')
    args = parser.parse_args()
    
    # Create and run trainer
    trainer = SelfPlayTrainer(num_episodes=args.episodes, save_interval=args.save_interval)
    
    # Train the AI
    start_time = time.time()
    trainer.train()
    training_time = time.time() - start_time
    print(f"\nTraining completed in {training_time:.2f} seconds")
    
    # Evaluate if requested
    if args.evaluate:
        trainer.evaluate()
    
    # Plot training rewards
    if os.path.exists('ai_training_data.pkl'):
        from visulisation import plot_episode_rewards
        print("Generating training rewards plot...")
        plot_episode_rewards()

if __name__ == '__main__':
    main()
