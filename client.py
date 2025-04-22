import socket
import struct
import sys
import threading
import scapy
from scapy.arch import get_if_addr
# import getch
# import keyboard
import time
import random
import select
import colorama
from colorama import Fore, Style, Back
import pickle
import json
import msvcrt
from faker import Faker

CHANNEL_UDP = 2515
MAGIC_COOKIE = 0xabcddcba
TYPE_BROADCAST = 0x2
KILO_BYTE = 1024
TIME_OUT_LENGTH = 10


class Client():

    def __init__(self, ip, teamName) -> None:
        self._ip = ip
        self._teamName = teamName
        self.bonusPrint("Client started, listening for offer requests...")
        self.winner = False
        self.communicateWithServer()

    def communicateWithServer(self):
        '''
        Open TCP and UDP sockets, receive offer from server via UDP, and connect to the server using TCP.
        This function sets up TCP and UDP sockets, binds the UDP socket to listen for offer requests,
        receives an offer from the server via UDP broadcast, and establishes a TCP connection with the server.
        '''
        self._socketTCP = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socketUDP = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socketUDP.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socketUDP.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        # ip2 = '.'.join(self._ip.split('.')[:-1]) + '.255'
        self._socketUDP.bind(('', CHANNEL_UDP))

        while True:
            try:
                offer_from_server, ip = self._socketUDP.recvfrom(KILO_BYTE)
            except Exception as e:
                self.bonusPrint("except")
                continue  # try again
            magic_cookie, types, TCPort = struct.unpack(">IbH", offer_from_server[:struct.calcsize(">IbH")])
            server_name = offer_from_server[struct.calcsize(">IbH"):].decode('utf-8')
            self.bonusPrint("Received offer from server " + '"' + str(server_name) + '"' + " at address " + str(
                ip[0]) + ", attempting to connect...")
            if (magic_cookie != MAGIC_COOKIE or types != TYPE_BROADCAST):
                continue
            break
        while True:
            try:
                self._socketTCP.connect((ip[0], TCPort))
                break
            except Exception as e:
                self.bonusPrint("exceptClient")
                continue
        self.beforeGame()
        self.Game()

    def beforeGame(self):
        message = self._teamName + "\n"
        self._socketTCP.send(bytes(message, encoding='utf-8'))

    def Game(self):
        '''
        Handle the game logic including sending and receiving messages from the server,
        processing user input, and determining the game outcome.
        '''
        checkCorrectness = False
        self.winner = False
        from_server = str(self._socketTCP.recv(KILO_BYTE), 'utf-8')
        self.bonusPrint(from_server)
        user_input = "None"
        try:
            user_input = self.get_user_input()
        except Exception as e:
            self.bonusPrint(
                "Error decoding message from server. \n Please insert valid key format {F, N, 0} or {T, Y, 1}")

        self._socketTCP.send(bytes(user_input, encoding='utf-8'))

        try:
            from_server = str(self._socketTCP.recv(KILO_BYTE), 'utf-8')
            if from_server != "N":
                self.bonusPrint(from_server)
                lines = from_server.strip().split('\n')
                for line in lines:
                    parts = line.split()
                    team_name = parts[0]
                    correctness = parts[-1].strip('!')
                    if correctness == 'Wins' or (self._teamName == team_name and correctness == "incorrect"):
                        self.winner = True
                        wins_from_Server = str(self._socketTCP.recv(KILO_BYTE), 'utf-8')
                        self.bonusPrint(wins_from_Server)
                        statistic = str(self._socketTCP.recv(KILO_BYTE), 'utf-8')
                        self.bonusPrint(statistic)
                        self.closeSockets()
                        self.bonusPrint("Server disconnected, listening for offer requests...")
                        self.communicateWithServer()
                        return
                    elif self._teamName == team_name:
                        checkCorrectness = self.check_participant(correctness)
            else:
                checkCorrectness = True
        except Exception as e:
            self.closeSockets()
            self.bonusPrint("Server disconnected, listening for offer requests...")
            self.communicateWithServer()
            return
        self.new_round(checkCorrectness)

    def new_round(self, checkCorrectness):
        '''
        Start a new round of the game if the correctness check is True.
        '''
        if checkCorrectness == True:
            self.Game()

    def get_user_input(self):
        '''
        Receive user input from the keyboard and return the first character typed.
        '''
        while msvcrt.kbhit():
            msvcrt.getch()
        start_time = time.time()
        user_input = None
        while True:
            if time.time() - start_time > TIME_OUT_LENGTH:
                if not user_input:
                    user_input = "None"
                break
            if msvcrt.kbhit():
                user_input = msvcrt.getch().decode()
                sys.stdout.write(user_input + '\n')
                sys.stdout.flush()
                break
        return user_input

    def closeSockets(self):
        self._socketTCP.close()
        self._socketUDP.close()

    def bonusPrint(self, text):
        '''
        Print text in a random color using colorama.
        '''
        notGood = ['BLACK']
        style = vars(colorama.Fore)
        randomColors = [style[c] for c in style if c not in notGood]
        _color = random.choice(randomColors)
        print(''.join([_color + word for word in text]))

    def check_participant(self, correctness):
        if correctness == 'correct':
            return True
        return False


+q    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)
    faker = Faker()
    client_name = faker.name().split()[0]
    Client(ip_address, client_name)

