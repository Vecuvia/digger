#!/usr/bin/env python3
import curses
from random import randint

Directions = {
	(0, -1): "north",
	(0, +1): "south",
	(-1, 0): "west",
	(+1, 0): "east"
}

def choice_out_of(width, choices, default):
	from random import randint
	what = randint(1, width)
	if type(choices) is dict:
		choices = list(choices.items())
	running_sum = 0
	for i, (item, weight) in enumerate(choices):
		running_sum += weight
		if what < running_sum:
			return item
	return default

class Ore(object):
	def __init__(self, char, x, y, kind, value):
		self.char, self.x, self.y = char, x, y
		self.kind, self.value = kind, value
	def draw(self, screen, x, y):
		screen.addstr(y, x, self.char)
	def on_move(self, other):
		self.level.entities.remove(self)
		other.inventory.append(self)
		return True, "$n pick$s up a chunk of %s. "% self.kind

class Market(object):
	def __init__(self, x, y):
		self.char, self.x, self.y = "$", x, y
	def draw(self, screen, x, y):
		screen.addstr(y, x, self.char)
	def on_move(self, other):
		return True, "$n enter$s the market. "
	def signal(self, trigger, key):
		if key == ord("S"):
			what = self.level.screen.getch()
			what = chr(what)
			try:
				what = trigger.inventory.pop(int(what))
				trigger.gold += what.value
				return True, "$n sell$s a chunk of %s to the market. " % what.kind
			except (ValueError, IndexError):
				return True, "$n don't have that. "
		return False, ""

class Player(object):
	def __init__(self, char, x, y, digger=0):
		self.char, self.x, self.y = char, x, y
		self.digger = digger
		self.inventory = []
		self.gold = 0
	def draw(self, screen, x, y):
		screen.addstr(y, x, self.char)
	def move(self, x, y):
		next_x, next_y = self.x + x, self.y + y
		message = ""
		if 0 <= next_x < self.level.width and 0 <= next_y < self.level.height:
			if self.digger and self.level.map[next_y][next_x].dug > 0:
				self.level.map[next_y][next_x].dug -= self.digger
				message += "$n dig$s a passage %s. " % Directions[(x, y)]
			if self.level.map[next_y][next_x].dug == 0:
				entities = self.level.get_entities(next_x, next_y)
				can_move, messages = True, ""
				for entity in entities:
					can_move, new_message = entity.on_move(self)
					messages += new_message
				if can_move:
					self.x, self.y = next_x, next_y
					message += "$n move$s %s. " % Directions[(x, y)]
				message += messages
				#else:
				#	for entity in entities:
				#		can_move, new_message = entity.on_move(self)
				#		message += new_message
			self.explore(self.x, self.y)
		else:
			message += "$n can't move there."
		return message
	def explore(self, x, y):
		for i in range(x-1, x+2):
			for j in range(y-1, y+2):
				if 0 <= i < self.level.width and 0 <= j < self.level.height:
					self.level.map[j][i].explored = True
	def on_move(self, other):
		pass

class Tile(object):
	def __init__(self, dug=4, explored=False):
		self.dug = dug
		self.explored = explored
	def draw(self, screen, x, y):
		screen.addstr(y, x, str(self))
	def __str__(self):
		if self.explored:
			if self.dug:
				return "#"
			return "."
		return " "

class Level(object):
	def __init__(self, width, height, screen):
		self.width, self.height = width, height
		self.map, self.entities = None, []
		self.screen = screen
	def generate(self, ore_amount=3):
		self.map = [[Tile() for i in range(self.width)] 
					for j in range(self.height)]
		for i in range(ore_amount):
			kind, value = choice_out_of(100, {
				("copper", 3): 20,
				("tin", 4): 10,
				("silver", 10): 5,
				("gold", 100): 1
			}, ("iron", 1))
			self.add_entity(Ore("*", x=randint(1, self.width-1), 
				y=randint(1, self.height-1), kind=kind, value=value))
	def get_entities(self, x, y):
		return [entity for entity in self.entities 
				if entity.x == x and entity.y == y]
	def add_entity(self, entity):
		self.entities.append(entity)
		entity.level = self
	def out(self, screen, cx, cy, vx, vy):
		for j in range(vy):
			y = j + cy - int(vy // 2) + 1
			for i in range(vx):
				x = i + cx - int(vx // 2) + 1
				if 0 <= x < self.width and 0 <= y < self.height:
					self.map[y][x].draw(screen, i, j)
				else:
					#Draw unexplored
					screen.addstr(j, i, ' ')
		for entity in self.entities:
			x = (entity.x - cx) + int(vx // 2) - 1
			y = (entity.y - cy) + int(vy // 2) - 1
			if 0 <= x < vx and 0 <= y < vy and self.map[entity.y][entity.x].explored:
				entity.draw(screen, x, y)
	def send_signal(self, trigger, key, x, y):
		for entity in self.entities:
			if entity.x == x and entity.y == y:
				try:
					signaled, message = entity.signal(trigger, key)
					if signaled:
						return message
				except AttributeError:
					pass
		return ""

MAP_WID, MAP_HGT = 40, 20
INF_WID, INF_HGT = 35, 20
MSG_WID, MSG_HGT = 70, 2

def main(stdscr):
	stdscr.clear()
	stdscr.keypad(True)
	curses.curs_set(0)
	mapwin = curses.newwin(MAP_HGT+1, MAP_WID, 1, 1)
	infwin = curses.newwin(INF_HGT+1, INF_WID, 1, 2+MAP_WID)
	msgwin = curses.newwin(MSG_HGT+1, MSG_WID, 2+MAP_HGT, 1)
	level = Level(50, 50, stdscr)
	level.generate(ore_amount=50)
	player = Player("@", 25, 25, digger=1)
	level.add_entity(Market(25, 25))
	level.add_entity(player)
	player.explore(player.x, player.y)
	x, y = 25, 25
	key = None
	message, last_message = "", ""
	while True:
		level.out(mapwin, player.x, player.y, MAP_WID, MAP_HGT)
		infwin.clear()
		infwin.addstr(0, 0, "Position: %s, %s" % (player.x, player.y))
		infwin.addstr(1, 0, "Money: $%s" % player.gold)
		infwin.addstr(3, 0, "Nearby:")
		if 0 <= player.y - 1 < level.height:
			infwin.addstr(4, 0, "%s N (earth)" % (str(level.map[player.y-1][player.x])))
		if 0 <= player.y + 1 < level.height:
			infwin.addstr(5, 0, "%s S (earth)" % (str(level.map[player.y+1][player.x])))
		if 0 <= player.x - 1 < level.width:
			infwin.addstr(6, 0, "%s E (earth)" % (str(level.map[player.y][player.x-1])))
		if 0 <= player.x + 1 < level.width:
			infwin.addstr(7, 0, "%s W (earth)" % (str(level.map[player.y][player.x+1])))
		infwin.addstr(9, 0, "Carrying:")
		for i, item in enumerate(player.inventory):
			infwin.addstr(10+i, 0, "a chunk of %s ($%s)" % (item.kind, item.value))
		if message:
			msgwin.clear()
			msgwin.addstr(0, 0, message)
			msgwin.addstr(1, 0, last_message)
			last_message = message
		stdscr.refresh()
		mapwin.refresh()
		infwin.refresh()
		msgwin.refresh()
		key = stdscr.getch()
		if key in (ord('q'), 27):
			break
		elif key in (curses.KEY_UP, ord('w')):
			message = player.move(0, -1)
		elif key in (curses.KEY_DOWN, ord('s')):
			message = player.move(0, +1)
		elif key in (curses.KEY_LEFT, ord('a')):
			message = player.move(-1, 0)
		elif key in (curses.KEY_RIGHT, ord('d')):
			message = player.move(+1, 0)
		else:
			message = level.send_signal(player, key, player.x, player.y)
		message = message.replace("$n", "You")
		message = message.replace("$s", "")
		message = message.replace("$$", "$")

if __name__ == "__main__":
	curses.wrapper(main)