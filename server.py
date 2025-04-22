import copy
import socket
import struct
import sys
import time
import random
import colorama
from colorama import Fore, Style
import threading
from select import select

CHANNEL_UDP = 2515
MAGIC_COOKIE = 0xabcddcba
TYPE_BROADCAST = 0x2
KILO_BYTE = 1024
SELECT_TIMEOUT = 0.5
TENSEC = 10
SERVER_NAME = 'Kapibarot'


class Server():

    def __init__(self, IP, channel) -> None:
        self._IP = IP
        self._channel = channel
        self._serverAddress = (self._IP, 0)
        self._socketTCP = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socketTCP.bind(self._serverAddress)
        self._socketTCP.listen()
        self._port = self._socketTCP.getsockname()[1]
        self._socketUDP = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self._socketUDP.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socketUDP.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self._numTeamINC = threading.Lock()
        self._FirstAns = threading.Lock()
        self._event = threading.Event()
        self._startGame = threading.Event()
        self.round = 1
        self._Teams = {}
        self._numTeams = 0
        self._result = ""
        self._stopServer = False
        self._finishGame = False
        self.players = {}
        self.losers = []
        self._stat = {}
        self.rematch = 0
        self.Winner = False
        self.used_questions = []
        self.all_players = {}
        self._last_connection_time = time.time()
        self.startServer()

    def stopServer(self):
        self._stopServer = True

    def startServer(self):
        '''
        Start the server by initiating UDP and TCP listening threads.
        '''
        game_event = threading.Event()
        udp_thread = threading.Thread(target=self.Listening_UDP)
        tcp_thread = threading.Thread(target=self.Listening_TCP, args=(game_event,))
        udp_thread.start()
        tcp_thread.start()
        while not game_event.is_set():
            continue

        # Start the game thread and wait for it to finish
        game_thread = threading.Thread(target=self.Game)
        game_thread.start()
        game_thread.join()
        self.clear()
        self.startServer()

    def Listening_UDP(self):
        '''
        Listen for UDP packets, sending server information to clients.
        Sends packets with server information to potential clients using the broadcast address.
        '''
        self.bonusPrint("Server started, listening on IP address " + self._IP)
        packet_to_send = struct.pack(">IbH", MAGIC_COOKIE, TYPE_BROADCAST, self._port)
        server_name_bytes = SERVER_NAME.encode('utf-8')
        packet_to_send += server_name_bytes
        ip = '.'.join(self._IP.split('.')[:-1]) + '.255'
        while (True):
            self._socketUDP.sendto(packet_to_send, (ip, CHANNEL_UDP))
            time.sleep(1)

    def Listening_TCP(self, game_event):
        '''
        Listen for TCP connections from clients.
        Accepts TCP connections from clients and initializes team information.
        If there are at least 2 teams and 10 seconds have passed since the last connection,
        starts the game in a new thread.
        '''
        self._socketTCP.settimeout(1)
        while True:
            try:
                connection, client_address = self._socketTCP.accept()
            except socket.timeout:
                if self._numTeams > 1 and time.time() - self._last_connection_time > 10:
                    # threading.Thread(target=self.Game).start()
                    game_event.set()
                    break
                continue
            except Exception as e:
                self.bonusPrint("exceptServer:", e)

            self._last_connection_time = time.time()
            self._numTeamINC.acquire()
            self._numTeams += 1
            self._Teams[self._numTeams] = ['', connection, client_address]

            threading.Thread(target=self.initializeNameOfTeams, args=(connection, self._numTeams)).start()

    def clear(self):
        for key, val in self.all_players.items():
            val.close()
        self.bonusPrint("Game Over, sending out offer requests...")
        self._event.clear()
        self._startGame.clear()
        self._stopServer = False
        self._finishGame = False
        self._Teams.clear()
        self._numTeams = 0
        self._FirstAns = threading.Lock()
        self.round = 1
        self.players.clear()
        self.losers = []
        self._stat = {}
        self.rematch = 0
        self.used_questions = []
        self.all_players = {}
        self.Winner = False

    def initializeNameOfTeams(self, connection, nt):
        '''
        Initialize the name of teams and store player information.
        Receives the team name from the client connection, stores it in the team information,
        and adds the player information to the list of all players.
        If the team name is not in the statistics dictionary, initializes its entry with a count of 0.
        '''
        nameOfTeam = str(connection.recv(KILO_BYTE), 'utf-8')
        self._Teams[nt][0] = nameOfTeam[:nameOfTeam.index("\n")]
        self.all_players[nt] = connection
        if self._Teams[nt][0] not in self._stat.keys():
            self._stat[self._Teams[nt][0]] = 0
        self._numTeamINC.release()

    def Game(self):
        '''
        Manage the gameplay, including sending questions to clients, receiving answers, and determining winners.
        Generates a problem/question for the current round and sends it to all teams.
        Then, spawns threads to handle input from each client simultaneously.
        After receiving all answers, determines the correctness and sends the results to clients.
        If there is a single winner, declares the winner and sends game statistics to all clients.
        If there is a rematch, restarts the game. Otherwise, clears out losers and proceeds to the next round.
        '''
        problem = self.GeneratingProblem()
        if self.round == 1 and self.rematch == 0:
            message = f"Welcome to {SERVER_NAME} server, where we are answering trivia questions about Capybaras and animals.\n"
            for team_num, team_info in self._Teams.items():
                player_info = f"Player {team_num}: {team_info[0]}"
                message += f"{player_info}\n"
            message += "==\n"
            message += f"True or false: {problem['question']}"
        elif self.rematch > 0:
            message = f"True or false: {problem['question']}"
        else:
            player_names = [team_info[0] for team_info in self._Teams.values()]
            message = f"Round {self.round}, played by {' and '.join(player_names)}:\n"
            message += f"True or false: {problem['question']}"
        for key, value in self._Teams.items():
            try:
                value[1].sendall(message.encode())
            except Exception as e:
                self._stopServer = True
                self.bonusPrint("connection lost")
                return
        self.bonusPrint(message)

        self.rematch = 0
        self.losers = []
        threads = []
        eventLostConnection = threading.Event()
        for team_num, team_info in self._Teams.items():
            thread = threading.Thread(target=self.getInputFromClient,
                                      args=(problem['is_true'], team_info[1], team_num, eventLostConnection))
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join()
        if eventLostConnection.is_set():
            self._stopServer = True
            return

        result_message = ""
        correct_players = [player for player, is_correct in self.players.items() if is_correct]

        if self.rematch == 0:
            for player, is_correct in self.players.items():
                if len(correct_players) == 1 and correct_players[0] == player:
                    result_message += f"{player} is correct! {player} Wins!\n"
                    self.Winner = True
                else:
                    result_message += f"{player} is {'correct' if is_correct else 'incorrect'}!\n"
        else:
            result_message = "N"
        for key, value in self._Teams.items():
            try:
                value[1].sendall(result_message.encode())
                if result_message != "N":
                    self.bonusPrint(result_message)
            except Exception as e:
                self._stopServer = True
                self.bonusPrint("connection lost")
                return

        if self.Winner:
            summary_message = f"Game over!\nCongratulations to the winner: {correct_players[0]}"
            for team_num, socket in self.all_players.items():
                try:
                    socket.sendall(summary_message.encode())
                except Exception as e:
                    self._stopServer = True
                    self.bonusPrint("connection lost")
                    return
            self.bonusPrint(summary_message)
            statistics = self.Statistics()
            for team_num, socket in self.all_players.items():
                try:
                    socket.sendall(statistics.encode())
                except Exception as e:
                    self._stopServer = True
                    self.bonusPrint("connection lost")
                    return
            self.bonusPrint(statistics)
            self.clear()
            self.startServer()
            return

        if self.rematch > 0:
            self.Game()
            return

        for key in list(self._Teams.keys()):
            if key in self.losers:
                del self._Teams[key]
        self.losers = []
        self.players.clear()

        self.round += 1
        self.Game()

    def getInputFromClient(self, answer, connection, numteam, eventLostConnection):
        '''
        Receive and process input from a client within a time limit of 10 seconds and check if the received answer is correct.
        '''
        start_time = time.time()
        valid_responses = {'Y', 'T', 'N', 'F', '0', '1'}
        while not eventLostConnection.is_set() and time.time() - start_time < 10:
            ready_to_read, _, _ = select([connection], [], [], 0.1)
            if ready_to_read:
                try:
                    answer_received = connection.recv(1024).strip().decode('utf-8').upper()
                except Exception as e:
                    self._stopServer = True
                    self.bonusPrint("connection lost")
                    eventLostConnection.set()
                    return
                if answer_received in valid_responses and ((answer_received in {'T', 'Y', '1'} and answer == True) or (
                        answer_received in {'F', 'N', '0'} and answer == False)):
                    self.players[self._Teams[numteam][0]] = True
                else:
                    self.players[self._Teams[numteam][0]] = False
                    self.losers.append(numteam)

        if len(self.losers) == len(self._Teams):
            self.rematch += 1

    def GeneratingProblem(self) -> list:
        '''
        Generate a trivia problem from a list of questions, ensuring each question is used only once.

        Returns:
        --------
            list:
                A list representing a trivia problem, containing 'question' and 'is_true'.
        '''
        trivia_questions = [
            {"question": "Capybaras are the largest rodents in the world.", "is_true": True},
            {"question": "Capybaras are native to Asia.", "is_true": False},
            {"question": "Capybaras are excellent swimmers.", "is_true": True},
            {"question": "Capybaras are solitary animals.", "is_true": False},
            {"question": "Capybaras are closely related to guinea pigs.", "is_true": True},
            {"question": "Capybaras are carnivorous.", "is_true": False},
            {"question": "Capybaras are herbivorous.", "is_true": True},
            {"question": "Capybaras communicate using vocalizations.", "is_true": True},
            {"question": "Capybaras are nocturnal animals.", "is_true": False},
            {"question": "Capybaras have webbed feet.", "is_true": True},
            {"question": "Capybaras are able to hold their breath underwater for up to 5 minutes.", "is_true": True},
            {"question": "Capybaras are endangered species.", "is_true": False},
            {"question": "Capybaras live in groups called herds.", "is_true": True},
            {"question": "Capybaras are legal to own as pets in most countries.", "is_true": False},
            {"question": "Capybaras are territorial animals.", "is_true": True},
            {"question": "Capybaras have poor eyesight.", "is_true": False},
            {"question": "Capybaras have a lifespan of about 10 years in the wild.", "is_true": False},
            {"question": "Capybaras are fast runners, capable of reaching speeds up to 35 miles per hour.",
             "is_true": False},
            {"question": "Capybaras are featured in the national emblem of Brazil.", "is_true": True},
            {"question": "Capybaras are commonly found in mountainous regions.", "is_true": False}
        ]
        available_questions = [q for q in trivia_questions if q not in self.used_questions]
        if not available_questions:
            self.used_questions = []
            available_questions = trivia_questions
        problem = random.choice(available_questions)
        self.used_questions.append(problem)
        return problem

    def bonusPrint(self, text):
        '''
        Print text in a random color using colorama.
        '''
        notGood = ['BLACK']
        style = vars(colorama.Fore)
        randomColors = [style[c] for c in style if c not in notGood]
        _color = random.choice(randomColors)
        print(''.join([_color + word for word in text]))

    def Statistics(self):
        '''
        Calculate game statistics based on the number of players and their answers.
        '''
        # Calculate statistics based on game results
        total_players = len(self.all_players)
        total_correct_answers = sum(self.players.values())
        total_incorrect_answers = total_players - total_correct_answers

        # Calculate percentage of correct and incorrect answers
        if total_players > 0:
            percentage_correct = (total_correct_answers / total_players) * 100
            percentage_incorrect = (total_incorrect_answers / total_players) * 100
        else:
            percentage_correct = 0
            percentage_incorrect = 0

        data = ("Game Statistics:\n"
                "Total Players: {}\n"
                "Total Correct Answers: {}\n"
                "Total Incorrect Answers: {}\n"
                "Percentage of Correct Answers: {:.2f}%\n"
                "Percentage of Incorrect Answers: {:.2f}%").format(total_players,
                                                                   total_correct_answers,
                                                                   total_incorrect_answers,
                                                                   percentage_correct,
                                                                   percentage_incorrect)

        return data


if __name__ == "__main__":
    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)
    Server(ip_address, CHANNEL_UDP)