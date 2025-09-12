import pygame
import copy
from queue import Queue, LifoQueue

class State:
    def __init__(self, map, prev_state = None):
        self.map = tuple(tuple(row) for row in map)
        self.rows_count = len(self.map)
        self.cols_count = len(self.map[0])
        self.prev_state = prev_state
    
    def __eq__(self, __o: object) -> bool:
        if __o == None:
            return False
        for row in range(self.rows_count):
            for col in range(self.cols_count):
                if self.map[row][col] !=  __o.map[row][col]:
                    if self.map[row][col] == '@' and __o.map[row][col] == '.':
                        continue
                    return False
        return True

    def __hash__(self) -> int:
        return hash(tuple(self.map))

class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption('Sokoban Solver')
        pygame.font.init()
        self.width = 800
        self.height = 800
        self.surface = pygame.display.set_mode((self.width, self.height))
        self.surface.fill((62, 180, 137))
        self.maps = list()
        self.map_rows = 0
        self.map_cols = 0
        self.block_size = 60
        self.font = pygame.font.Font(None, self.block_size)
        self.status = 'search'
        pygame.display.flip()

    def __del__(self):
        pygame.quit()
    
    def Start(self):
        is_active = True
        while is_active:
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    is_active = False
            
            match self.status:
                case 'search':
                    self.maps = self.Find_Solution('level №3.txt', 'stack')
                    if self.maps == None:
                        print('решение не найдено')
                    self.status = 'show'

                case 'show':
                    map = self.maps.pop()
                    self.Draw_Map(map)
                    if len(self.maps) == 0:
                        self.status = 'stop'
                    pygame.time.delay(250)

                case 'stop':
                    pass

            pygame.display.update()

    def Find_Solution(self, level_name, structure_type):
        map_file = open('Levels/' + level_name, 'r') 
        start_map = map_file.read().split(sep='\n')
        map_file.close()
        self.map_rows = len(start_map)
        self.map_cols = len(start_map[0])
        for i in range(self.map_rows):
            start_map[i] = list(start_map[i])
        
        final_state_file = open('Levels/Final States/' + level_name, 'r')
        final_map = final_state_file.read().split(sep='\n')
        final_state_file.close()
        for i in range(self.map_rows):
            final_map[i] = list(final_map[i])
        final_state = State(final_map)

        match structure_type:
            case 'stack':
                O = LifoQueue()
            case 'queue':
                O = Queue()
        start_state = State(start_map)
        O.put(start_state)
        C = {start_state}
        directions = ['up', 'down', 'right', 'left']

        while not O.empty():
            state = O.get()
            map = state.map
            if state == final_state:
                maps = list()
                while state.prev_state != None:
                    maps.append(state.map)
                    state = state.prev_state
                maps.append(state.map)
                return maps
            x, y = 0, 0
            for row in range(self.map_rows):
                if '@' in map[row]:
                    y = row
                    x = map[row].index('@')
                    break
                elif '*' in map[row]:
                    y = row
                    x = map[row].index('*')
                    break

            for direction in directions:
                new_map = self.Check_Direction(direction, map, x, y)
                if new_map != None:
                    new_state = State(new_map, state)
                    if not new_state in C:
                        O.put(new_state)
                        C.add(new_state)
        return None
    
    def Check_Direction(self, direction, map, x, y):
        delta = {
            'up':    (0, -1),
            'down':  (0,  1),
            'left':  (-1, 0),
            'right': (1,  0)
        }
        dx, dy = delta[direction]
        new_map = [list(row) for row in map]
        nx, ny = x + dx, y + dy       
        nnx, nny = x + 2*dx, y + 2*dy

        if not (0 <= nx < self.map_cols and 0 <= ny < self.map_rows):
            return None

        target = new_map[ny][nx]
        if target == '#':
            return None

        if target in ['B', '+']:
            if not (0 <= nnx < self.map_cols and 0 <= nny < self.map_rows):
                return None
            behind = new_map[nny][nnx]
            if behind in ['#', 'B', '+']: 
                return None

            if behind == 'X':  
                new_map[nny][nnx] = '+'
            else:
                new_map[nny][nnx] = 'B'

            if target == 'B':
                new_map[ny][nx] = '.'
            elif target == '+':
                new_map[ny][nx] = 'X'
            target = new_map[ny][nx]

        if target == '.':
            new_map[ny][nx] = '@'
        elif target == 'X':
            new_map[ny][nx] = '*'

        if new_map[y][x] == '@':
            new_map[y][x] = '.'
        elif new_map[y][x] == '*':
            new_map[y][x] = 'X'

        return new_map

    def Draw_Map(self, map):
        start_x = self.width // 2 - self.map_cols * self.block_size // 2 
        start_y = self.height // 2 - self.map_rows * self.block_size // 2 
        for row in range(self.map_rows):
            for col in range(self.map_cols):
                x = start_x + col * self.block_size
                y = start_y + row * self.block_size
                match map[row][col]:
                    case ' ':
                        continue
                    case '#':   
                        pygame.draw.rect(self.surface, (0, 0, 0), [x, y, self.block_size, self.block_size])
                    case '.':
                        pygame.draw.rect(self.surface, (255, 255, 255), [x, y, self.block_size, self.block_size])
                    case '@':
                        pygame.draw.rect(self.surface, (255, 255, 255), [x, y, self.block_size, self.block_size])
                        pygame.draw.circle(self.surface, (139, 159, 215), 
                            [x + self.block_size / 2, y + self.block_size // 2], self.block_size // 2)
                    case '*':
                        pygame.draw.rect(self.surface, (255, 255, 255), [x, y, self.block_size, self.block_size])
                        pygame.draw.circle(self.surface, (139, 159, 215), 
                            [x + self.block_size / 2, y + self.block_size // 2], self.block_size // 2)
                    case 'B':
                        pygame.draw.rect(self.surface, (215, 157, 139), [x, y, self.block_size, self.block_size])
                        pygame.draw.rect(self.surface, (50, 50, 50), [x, y, self.block_size, self.block_size], 1)
                    case 'X':
                        pygame.draw.rect(self.surface, (255, 255, 255), [x, y, self.block_size, self.block_size])
                        text = self.font.render("X", True, (229, 43, 80))
                        text_rect = text.get_rect()
                        text_rect.center = (x + self.block_size // 2, y + self.block_size // 2)
                        self.surface.blit(text, text_rect)
                    case '+':
                        pygame.draw.rect(self.surface, (241, 221, 215), [x, y, self.block_size, self.block_size])
                        pygame.draw.rect(self.surface, (50, 50, 50), [x, y, self.block_size, self.block_size], 1)

game = Game()
game.Start()