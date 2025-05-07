import datetime
import os
import random
import re
import string
import enchant

from PIL import Image


class Wordle:
    def __init__(self, msg):
        self.is_alive = self  # 用于赋值status['wordle'] 状态集合为{self, None}
        self.game_status = None
        self.is_serious = False
        self.last_guess = {'green': {}, 'orange': []}
        self.alphabet = list(string.ascii_uppercase)
        self.msg = msg
        self.command = {'guess': self.guess, 'remain': self.remain, 'giveup': self.giveup}  # 所有交互函数接收唯一参数msg
        self.dictionary = {}  # {word: definition}
        self.check_dict = enchant.Dict("en_US")
        self.word_length = self.get_length()
        self.guess_count = 6
        self.word = ''
        self.reply_list = []

        if isinstance(self.is_alive, Wordle):
            self.set_mode()
        if isinstance(self.is_alive, Wordle):
            self.create_word()

    def write_dictionary(self):
        """生成词库"""
        word_file = open('./word_guess/words.txt', 'r')
        word_read = word_file.readlines()
        for i in range(len(word_read)):
            try:
                int(word_read[i])
                word, phonetic_symbol, definition = word_read[i + 1][:-1], word_read[i + 2][:-1], word_read[i + 3][:-1]
                self.dictionary[word] = f'{word}\n{phonetic_symbol}\n{definition}'
            except ValueError:
                continue

    def get_length(self):
        try:
            length = int(re.findall('/wordle new (.*)', self.msg)[0].split()[0])
            return length
        except (ValueError, IndexError):
            print('<Wordle> CommandError: Invalid length. Using "/wordle new <length>" to create a word')
            self.is_alive = None  # 如果参数错误，游戏结束

    def set_mode(self):
        mode = re.findall('/wordle new (.*)', self.msg)[0].split()
        if len(mode) == 1:
            return
        if mode[1] == 'serious':
            self.is_serious = True
            return
        if len(mode) > 2:
            print(
                f'<Wordle> CommandError: "/wordle new <length> <mode>" takes 2 positional argument but {len(mode)}'
                f' were given')
            self.is_alive = None
            return
        if mode[1] != 'serious':
            print(f'<Wordle> CommandError: Invalid argument {mode[1]}')
            self.is_alive = None
            return

    @staticmethod
    def delete_image(path):
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            if os.path.isfile(item_path) or os.path.islink(item_path):
                os.unlink(item_path)
            else:
                os.rmdir(item_path)

    @staticmethod
    def combine(image_list, output_file):
        base_image = Image.open(image_list[0])
        width, height = 0, base_image.height
        for image in image_list:
            img = Image.open(image)
            width += img.width

        combined_image = Image.new("RGB", (width, height))

        x_offset = 0
        for image in image_list:
            img = Image.open(image)
            combined_image.paste(img, (x_offset, 0))
            x_offset += img.width

        try:
            base_image = Image.open(output_file)
            width1, height1 = combined_image.size
            width2, height2 = base_image.size

            new_width = max(width1, width2)
            new_height = height1 + height2
            new_image = Image.new('RGB', (new_width, new_height))
            new_image.paste(base_image, (0, 0))
            new_image.paste(combined_image, (0, height2))
            new_image.save(output_file)
        except FileNotFoundError:
            combined_image.save(output_file)

    def match(self, guess_word):
        if self.guess_count >= 1:
            self.guess_count -= 1
            image_list = []
            marked_list = [False] * self.word_length
            for i in range(self.word_length):
                letter = guess_word[i]
                if letter == self.word[i]:
                    marked_list[i] = True
            self.last_guess = {'green': {}, 'orange': []}
            for i in range(self.word_length):
                letter = guess_word[i]
                pic = f'./word_guess/word_guess_resources/{letter}_white.png'
                if letter == self.word[i]:
                    pic = f'./word_guess/word_guess_resources/{letter}_green.png'
                    self.last_guess['green'][i] = letter
                elif letter in self.word:
                    if not [i for i in range(self.word_length) if self.word[i] == letter and not marked_list[i]]:
                        # 若letter在self.word中出现的所有位置i都满足marked_list[i] == True，则该位置显示white
                        # 即对于集合P = {对于所有letter出现的位置i，且marked_list[i] == False}为空集，该位置显示white
                        pic = f'./word_guess/word_guess_resources/{letter}_white.png'
                    else:
                        pic = f'./word_guess/word_guess_resources/{letter}_orange.png'
                        position = \
                            [l for l in range(self.word_length) if self.word[l] == letter and not marked_list[l]][0]
                        marked_list[position] = True
                        self.last_guess['orange'].append(letter)
                image_list.append(pic)
            self.combine(image_list,
                         './word_guess/word_guess_output/combined_image.png')
            image = Image.open(
                './word_guess/word_guess_output/combined_image.png')
            image.show()
            if guess_word == self.word:
                return 'win'
        if self.guess_count == 0:
            return 'lose'
        return 'continue'

    def check_serious(self, guess_word: str) -> bool:
        """用于判断guess_word是否满足serious模式的条件"""
        ret = True
        for green_position in self.last_guess['green'].keys():
            if guess_word[green_position] != self.last_guess['green'][green_position]:
                return False
        marked_list = [False] * self.word_length
        for orange_letter in self.last_guess['orange']:
            if not [p for p in range(self.word_length) if
                    guess_word[p] == orange_letter and p not in self.last_guess['green'].keys()]:
                # 包含该橙色字母的位置均为绿色(包含且不是绿色的list为空)
                return False

            # 橙色字母判断为：guess_word不包含对应次数的橙色字母
            position = \
                [l for l in range(self.word_length) if guess_word[l] == orange_letter and not marked_list[l]]
            if position:
                marked_list[position[0]] = True
            else:
                return False
        return ret

    def create_word(self):
        self.write_dictionary()
        words = [w for w in self.dictionary.keys() if len(w) == self.word_length]
        if not words:  # 若无匹配单词，游戏结束
            print('<Wordle> LengthError: Invalid word length')
            self.is_alive = None
            return
        else:
            random.seed = datetime.datetime.now()
            word = words[random.randrange(0, len(words))]
            self.delete_image('./word_guess/word_guess_output')
            print('Game Start!')
            self.game_status = 'continue'
            self.word = word

    def guess(self, msg):
        guess_word = re.findall('/wordle guess (.*)', msg)[0]
        if len(guess_word) != self.word_length:  # 错误的单词长度
            print(f'<Wordle> WordError: Need {self.word_length} characters, get {len(guess_word)} instead.')
            return
        if not self.check_dict.check(guess_word):  # 不是合法单词
            print('<Wordle> WordError: Word not exist')
            return
        if self.is_serious:
            if not self.check_serious(guess_word):  # 不满足serious的条件
                print('<Wordle> WordError: This guess is not serious enough')
                return
        self.game_status = self.match(guess_word)
        for letter in guess_word:
            if letter.upper() in self.alphabet:
                self.alphabet.remove(letter.upper())
        if self.game_status == 'continue':
            print(f'你还有{self.guess_count}次机会')
        if self.game_status == 'win':
            self.is_alive = None
            print(self.dictionary[self.word])
            print('你猜中了答案！')

        elif self.game_status == 'lose':
            self.is_alive = None
            print('你用完了所有机会，你失败了')
            print(self.dictionary[self.word])

    def remain(self, msg):
        print(f'Letter remained: {' '.join(self.alphabet)}')

    def giveup(self, msg):
        self.is_alive = None
        print('游戏结束')
        print(self.dictionary[self.word])


def command_wordle(msg):  # 所有start函数必须有唯一参数msg
    global status
    if not status['wordle']:  # 检查游戏是否启动
        if msg.split()[1] != 'new':
            print('<Wordle> GameError: Using "/wordle new <length>" to create a word first')
            return
        wordle = Wordle(msg)
        status['wordle'] = wordle.is_alive
    elif isinstance(status['wordle'], Wordle):
        if msg.split()[1] == 'new':
            print('<Wordle> GameError: You can only start one game at a time')
            return
        try:
            status['wordle'].command[msg.split()[1]](msg)
            status['wordle'] = status['wordle'].is_alive  # 若游戏结束将赋值None
        except KeyError:
            print('<Wordle> CommandError: Invalid command')
            return


def message_handler(msg):
    command_dict = {'/wordle': command_wordle}
    command = msg.split()[0]
    try:
        command_dict[command](msg)
    except KeyError:
        return


status = {'wordle': None}  # 记录了各对象状态，所有对象从status内调用
while True:
    message = input('>? ')
    message_handler(message)
