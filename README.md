# Networked Trivia Game System

A client-server based multiplayer trivia game focused on animal facts, specifically about capybaras. The system uses UDP for server discovery and TCP for reliable game communication.

## Overview

This project implements a complete multiplayer trivia game with the following components:

- **Server**: Broadcasts its presence, accepts TCP connections, and manages the game logic
- **Client**: Discovers servers, connects to them, and allows users to play the game
- **Bot**: An automated client that can play the game with random responses

## Features

### Server
- UDP broadcasting for server discovery
- TCP connection handling for multiple simultaneous players
- Capybara-themed true/false question system
- Round-based gameplay with elimination mechanics
- Game statistics tracking and reporting
- Colorful terminal output for better user experience

### Client
- Automatic server discovery via UDP
- Reliable TCP connection management
- User input handling with timeout functionality
- Error handling for network issues
- Random colorful terminal output

### Bot
- Extends the client functionality for automated play
- Generates random player names using Faker library
- Simulates human responses automatically

## Technical Details

### Communication Protocol
- **Server Discovery**: UDP broadcast on port 2515
- **Game Communication**: TCP connections with packet validation
- **Message Authentication**: Magic Cookie verification (0xabcddcba)
- **Timeout Handling**: 10-second response window for players

### Security Features
- Socket reuse prevention (SO_REUSEADDR)
- Magic Cookie validation for packet authentication
- Exception handling for connection termination detection
- Timeout mechanisms to prevent indefinite waiting

## Requirements
- Python 3.x
- Required libraries:
  - socket
  - struct
  - colorama
  - faker (for bot functionality)
  - scapy
  - msvcrt (for Windows systems)

## Installation

1. Clone this repository:
```
git clone https://github.com/sabagom/trivia-game.git
cd trivia-game
```

2. Install the required dependencies:
```
pip install colorama faker scapy
```

## Usage

### Running the Server
```
python server.py
```
The server will start broadcasting its presence on the local network and wait for clients to connect.

### Running a Client
```
python client.py
```
The client will automatically discover any servers on the local network and connect to the first one it finds.

### Running an Automated Bot
```
python bot.py
```
The bot will connect to the server and automatically play the game with random responses.

## Game Rules

1. Players connect to the server and provide their team names
2. The server presents true/false questions about capybaras and other animals
3. Players have 10 seconds to respond (T/Y/1 for True, F/N/0 for False)
4. Incorrect answers eliminate players from the round
5. If all players answer incorrectly, a rematch occurs
6. The last player standing wins the game
7. Game statistics are presented at the end

## Project Structure

- `server.py`: Contains the Server class and game logic
- `client.py`: Contains the Client class for player interaction
- `bot.py`: Contains the Bot class for automated play