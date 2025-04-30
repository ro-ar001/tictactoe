# Tic-Tac-Toe AI with Self-Play Training and Pygame GUI

This project is an interactive Tic-Tac-Toe game featuring:
- A self-training AI using Q-learning.
- A Pygame-based GUI.
- Online and offline gameplay modes.
- Visualization of training progress.

## Features

- **Self-Play Training**: The AI improves through reinforcement learning.
- **Pygame GUI**: Simple and interactive interface to play against the trained AI.
- **Training Visualization**: Track performance with reward plots.
- **Online Play (Optional)**: Play against other users via socket server.
- **Persistent Learning**: AI saves its Q-table and continues learning across sessions.

## Getting Started

###  Install Requirements

```bash
pip install -r requirements.txt
```

> Python 3.10+ is recommended. Tested with Pygame 2.6+ and NumPy.

## Train the AI

```bash
python train_ai.py --episodes 10000 --save-interval 1000 --evaluate
```

This will:
- Train the AI through self-play.
- Save the Q-table in `ai_qtable.pkl`.
- Evaluate performance against a random player.
- Save reward history to `ai_training_data.pkl`.

## Visualize Training

You can plot the training performance:

```bash
python visulisation.py
```

Or click the **"SHOW GRAPH"** button in the GUI after some training is done.

## Play with GUI

To play against the trained AI:

```bash
python pygame_gui.py
```

- Choose **"Play Against AI"**.
- Toggle training mode ON/OFF with the **TRAIN** button.
- View AI progress with **SHOW GRAPH**.

## Online Mode (Optional)

You can run the game server for online multiplayer:

```bash
python game_server.py
```

Then use **"Play Online"** in the GUI to connect two clients.

## Project Structure


train_ai.py            - AI training script (self-play)
game_ai.py             - Q-learning AI logic
pygame_gui.py          - Pygame-based game UI
game_manager.py        - Manages offline AI matches
game_client.py         - Online client logic
game_server.py         - Socket-based online server
visulisation.py        - Training plot generation
ai_qtable.pkl          - (Generated) Trained Q-table
ai_training_data.pkl   - (Generated) Reward history


## Requirements

- Python >= 3.10
- pygame
- numpy
- matplotlib
- tqdm

Install all dependencies:

```bash
pip install pygame numpy matplotlib tqdm
```

## How It Works

- The AI uses Q-learning to learn optimal moves via exploration and exploitation.
- Training is done through self-play, and results are stored in a Q-table (`dict[state_key][action] = Q-value`).
- The AI chooses actions based on epsilon-greedy strategy and updates Q-values using the Bellman equation.

## Credits

- Built with `pygame` and `numpy`.
- Q-learning inspired by reinforcement learning environments like OpenAI Gym.
