from faker import Faker
from client import *


class Bot(Client):
    def __init__(self, ip, teamName) -> None:
        super().__init__(ip, bot_name)

    def get_user_input(self):
        '''
        Simulate user input for the bot by randomly choosing a true/false answer.
        This method is specific to the client module.
        '''
        user_input = random.choice(['T', 'Y', '1', 'F', 'N', '0'])  # Randomly choose an answer
        print(user_input)
        return user_input


if __name__ == "__main__":
    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)
    faker = Faker()
    bot_name = "BOT: " + faker.name().split()[0]
    Bot(ip_address, bot_name)