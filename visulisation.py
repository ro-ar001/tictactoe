import matplotlib.pyplot as plt
import pickle
import numpy as np
import os

def plot_episode_rewards():
    if not os.path.exists('ai_training_data.pkl'):
        print("No training data found. Play some games with training enabled first.")
        return
    
    with open('ai_training_data.pkl', 'rb') as f:
        rewards = pickle.load(f)
    
    plt.figure(figsize=(12, 6))
    
    # Create episode numbers
    episodes = np.arange(1, len(rewards) + 1)
    
    # Plot raw rewards
    plt.scatter(episodes, rewards, alpha=0.3, label='Per-Episode Reward')
    
    # Plot moving average
    window_size = 50
    moving_avg = [np.mean(rewards[max(0, i-window_size):i+1]) 
                 for i in range(len(rewards))]
    
    plt.plot(episodes, moving_avg, color='red', 
            label=f'{window_size}-Episode Moving Average')
    
    plt.title('DRL Training Progress')
    plt.xlabel('Episode Number')
    plt.ylabel('Reward')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    plot_episode_rewards()
