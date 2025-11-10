import pygame
import os
from queue import Queue, LifoQueue, PriorityQueue
from itertools import count
from scipy.optimize import linear_sum_assignment
import numpy as np
import heapq

class State:
    def __init__(self, player_pos, boxes, prev_state = None, depth = 0):
        self.player = player_pos
        self.boxes = frozenset(boxes)
        self.prev_state = prev_state
        self.depth = depth

    def __eq__(self, other):
        if other is None:
            return False
        return self.player == other.player and self.boxes == other.boxes

    def __hash__(self):
        return hash((self.player, self.boxes))

class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption('Sokoban Solver')
        pygame.font.init()
        self.width = 800
        self.height = 800
        self.surface = pygame.display.set_mode((self.width, self.height))

        self.maps = list()
        self.map_rows = 0
        self.map_cols = 0
        self.map = list()

        self.block_size = 40
        self.font = pygame.font.SysFont("Arial", self.block_size)
        self.stats_font = pygame.font.SysFont("Arial", self.block_size // 2)

        self.status = 'menu'
        self.levels = [os.path.splitext(f)[0] for f in os.listdir('Levels') if f.endswith('.txt')]
        self.selected_level = None
        self.level_index = 0

        self.algorithms = ['breadth-first search', 'iterative depth-first search', 'bidirectional search', 'A*(h2)', 'A*(h3)']
        self.algorithm_index = 0

        self.iteration_count = 0
        self.O_max_node_count = 0
        self.O_end_node_count = 0
        self.max_node_count = 0
        self.steps_counter = 0

        self.h2_distances = None

        self.clock = pygame.time.Clock()
        pygame.display.flip()

    def __del__(self):
        pygame.quit()
    
    def Start(self):
        is_active = True
        while is_active:
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    is_active = False
                elif e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_UP and self.status == 'menu':
                        self.level_index = (self.level_index - 1) % len(self.levels)
                    elif e.key == pygame.K_DOWN and self.status == 'menu':
                        self.level_index = (self.level_index + 1) % len(self.levels)
                    elif e.key == pygame.K_SPACE and self.status == 'menu':
                        self.algorithm_index = (self.algorithm_index + 1) % len(self.algorithms) 
                    elif e.key == pygame.K_RETURN:
                        if self.status == 'menu':
                            self.selected_level = self.levels[self.level_index] + '.txt'
                            self.status = 'search'
                        elif self.status == 'stop':
                            self.status = 'stats'
                        elif self.status == 'stats' or self.status == 'error':
                            self.status = 'menu'      
            
            match self.status:
                case 'menu':
                    self.Draw_Menu()
                case 'search':
                    self.iteration_count = 0
                    self.O_max_node_count = 0
                    self.O_end_node_count = 0
                    self.max_node_count = 0
                    self.steps_counter = 0
                    match self.algorithms[self.algorithm_index]:
                        case 'depth-first search':
                            self.maps = self.Find_Solution(self.selected_level, 'stack')
                        case 'iterative depth-first search':
                            self.maps = self.DFS_Iterative(self.selected_level)
                        case 'breadth-first search': 
                            self.maps = self.Find_Solution(self.selected_level, 'queue')
                        case 'bidirectional search':
                            self.maps = self.Bidirectional_Search(self.selected_level)
                        case "A*(h1)":
                            self.maps = self.A_Star(self.selected_level, 'h1')
                        case "A*(h2)":
                            self.maps = self.A_Star(self.selected_level, 'h2')
                        case "A*(h3)":
                            self.maps = self.A_Star(self.selected_level, 'h3')
                    if self.maps == None:
                        self.status = 'error'
                    else:
                        self.status = 'show'

                case 'show':
                    map = self.maps.pop()
                    self.Draw_Map(map)
                    if len(self.maps) == 0:
                        self.status = 'stop'
                    pygame.time.delay(10)

                case 'stop':
                    pass

                case 'stats':
                    self.Draw_Stats()

                case 'error':
                    self.Draw_Error()

            pygame.display.flip()
            self.clock.tick(60)

    def Create_States(self, level_name):
        map_file = open('Levels/' + level_name, 'r') 
        start_map = map_file.read().split(sep='\n')
        map_file.close()
        self.map_rows = len(start_map)
        self.map_cols = len(start_map[0])
        for i in range(self.map_rows):
            start_map[i] = list(start_map[i])

        player = None
        boxes = list()
        self.map.clear()
        for y in range(self.map_rows):
            row = list()
            for x in range(self.map_cols):
                if start_map[y][x] == '@':
                    player = (x, y)
                    row.append('.')
                elif start_map[y][x] == '*':
                    player = (x, y)
                    row.append('X')
                elif start_map[y][x] == 'B':
                    boxes.append((x, y))
                    row.append('.')
                elif start_map[y][x] == '+':
                    boxes.append((x, y))
                    row.append('X')
                else:
                    row.append(start_map[y][x])
            self.map.append(row)
        start_state = State(player, boxes)
        
        final_state_file = open('Levels/Final States/' + level_name, 'r')
        final_map = final_state_file.read().split(sep='\n')
        final_state_file.close()
        final_player = None
        final_boxes = list()
        for y in range(self.map_rows):
            for x in range(self.map_cols):
                if final_map[y][x] == '@':
                    final_player = (x, y)
                elif final_map[y][x] == '+':
                    final_boxes.append((x, y))
        final_state = State(final_player, final_boxes)

        return (start_state, final_state)

    def Find_Solution(self, level_name, structure_type):
        start_state, final_state = self.Create_States(level_name)

        match structure_type:
            case 'stack':
                O = LifoQueue()
            case 'queue':
                O = Queue()
        O.put(start_state)
        C = {start_state}
        directions = ['up', 'down', 'right', 'left']

        while not O.empty():
            self.iteration_count += 1
            state = O.get()
            if state == final_state:
                self.O_end_node_count = O.qsize()
                maps = list()
                while state.prev_state != None:
                    self.steps_counter += 1
                    map = self.Create_Map(state)
                    maps.append(map)
                    state = state.prev_state
                map = self.Create_Map(state)
                maps.append(map)
                return maps

            for direction in directions:
                new_state = self.Check_Direction(direction, state)
                if new_state != None:
                    if not new_state in C:
                        O.put(new_state)
                        C.add(new_state)
                        O_size = O.qsize()
                        self.max_node_count = max(self.max_node_count, len(C) + O_size)
                        self.O_max_node_count = max(self.O_max_node_count, O_size)
                        
        return None

    def DFS_Iterative(self, level_name):
        start_state, final_state = self.Create_States(level_name)

        directions = ['up', 'down', 'right', 'left']
        O = LifoQueue()
        cur_depth = 1
        max_depth = 10000
        
        while True: 
            O.put(start_state)
            C = {start_state: start_state.depth}
            while not O.empty():
                self.iteration_count += 1
                state = O.get()
                if state == final_state:
                    self.O_end_node_count = O.qsize()
                    maps = list()
                    while state.prev_state != None:
                        self.steps_counter += 1
                        map = self.Create_Map(state)
                        maps.append(map)
                        state = state.prev_state
                    map = self.Create_Map(state)
                    maps.append(map)
                    return maps    

                if state.depth < cur_depth:
                    for direction in directions:
                        new_state = self.Check_Direction(direction, state)
                        if new_state != None:
                            new_state.depth = state.depth + 1
                            if not new_state in C or new_state.depth < C[new_state]:
                                O.put(new_state)
                                C[new_state] = new_state.depth
                                O_size = O.qsize()
                                self.max_node_count = max(self.max_node_count, len(C) + O_size)
                                self.O_max_node_count = max(self.O_max_node_count, O_size)   

            cur_depth += 1 
            if cur_depth >= max_depth:
                break

        return None

    def Bidirectional_Search(self, level_name):
        start_state, final_state = self.Create_States(level_name)

        O_start = Queue()
        O_start.put(start_state)
        C_start = {start_state}

        O_final = Queue()
        O_final.put(final_state)
        C_final = {final_state}

        directions = ['up', 'down', 'right', 'left']

        while not O_start.empty() or not O_final.empty():
            self.iteration_count += 1
            if not O_start.empty():
                state = O_start.get()

                if state in C_final:
                    self.O_end_node_count = O_start.qsize() + O_final.qsize()
                    C_final_list = list(C_final)
                    second_state = C_final_list.pop(C_final_list.index(state))
                    return self.Connect_Ways(state, second_state)

                for direction in directions:
                    new_state = self.Check_Direction(direction, state)
                    if new_state != None:
                        if not new_state in C_start:
                            O_start.put(new_state)
                            C_start.add(new_state)
                            O_size = O_start.qsize() + O_final.qsize()
                            self.max_node_count = max(self.max_node_count, len(C_start) + len(C_final) + O_size)
                            self.O_max_node_count = max(self.O_max_node_count, O_size)
            
            if not O_final.empty():
                state = O_final.get()

                if state in C_start:
                    self.O_end_node_count = O_start.qsize() + O_final.qsize()
                    C_start_list = list(C_start)
                    second_state = C_start_list.pop(C_start_list.index(state))
                    return self.Connect_Ways(second_state, state)

                for direction in directions:
                    new_states = self.Check_Direction_Backwards(direction, state)
                    for new_state in new_states:
                        if not new_state in C_final:
                            O_final.put(new_state)
                            C_final.add(new_state)
                            O_size = O_start.qsize() + O_final.qsize()
                            self.max_node_count = max(self.max_node_count, len(C_start) + len(C_final) + O_size)
                            self.O_max_node_count = max(self.O_max_node_count, O_size)
        
        return None

    def A_Star(self, level_name, h_number):
        start_state, final_state = self.Create_States(level_name)

        goals = list()
        for y in range(self.map_rows):
            for x in range(self.map_cols):
                if self.map[y][x] == 'X':
                    goals.append((x, y))

        counter = count()
        O = PriorityQueue()
        match h_number:
            case 'h1':
                h = self.H1(start_state, goals)
            case 'h2':
                h = self.H2(start_state, goals)
            case 'h3':
                h = self.H3(start_state, goals)
        # h = max(self.H1(start_state, goals) ,self.H2(start_state, goals))
        O.put((h, next(counter), start_state))
        open_states = {start_state: h}
        C = {start_state: h}
        directions = ['up', 'down', 'right', 'left']

        while not O.empty():
            state_f, _, state = O.get()
            if state not in open_states:
                continue
            open_states.pop(state)
            self.iteration_count += 1
            if state == final_state:
                self.h2_distances = None
                self.O_end_node_count = O.qsize()
                maps = list()
                while state.prev_state != None:
                    self.steps_counter += 1
                    map = self.Create_Map(state)
                    maps.append(map)
                    state = state.prev_state
                map = self.Create_Map(state)
                maps.append(map)
                return maps

            for direction in directions:
                new_state = self.Check_Direction(direction, state)
                if new_state != None:
                    new_state.depth = state.depth + 1
                    match h_number:
                        case 'h1':
                            f = new_state.depth + self.H1(new_state, goals)
                        case 'h2':
                            f = new_state.depth + self.H2(new_state, goals)
                        case 'h3':
                            f = new_state.depth + self.H3(new_state, goals)
                    # f = new_state.depth + max(self.H1(new_state, goals), self.H2(new_state, goals))
                    if not new_state in C or f < C[new_state]:
                        O.put((f, next(counter), new_state))
                        open_states[new_state] = f
                        C[new_state] = f
                        O_size = O.qsize()
                        self.max_node_count = max(self.max_node_count, len(C) + O_size)
                        self.O_max_node_count = max(self.O_max_node_count, O_size)
                        
        return None

    def Is_Wall(self, x, y):
        if not (0 <= x < self.map_cols and 0 <= y < self.map_rows):
            return True

        return self.map[y][x] == '#'

    def H1(self, state, goals):
        boxes = list(state.boxes)
        player_x, player_y = state.player
        min_player_way = 10000

        for x, y in boxes:
            if self.map[y][x] != 'X':
                if ((self.Is_Wall(x + 1, y) or self.Is_Wall(x - 1, y)) and
                    (self.Is_Wall(x, y + 1) or self.Is_Wall(x, y - 1))):
                    return float('inf')

        cost_matrix = np.zeros((len(boxes), len(goals)), dtype=int)
        for i, (bx, by) in enumerate(boxes):
            min_player_way = min(min_player_way, abs(bx - player_x) + abs(by - player_y) - 1)
            for j, (gx, gy) in enumerate(goals):
                cost_matrix[i, j] = abs(bx - gx) + abs(by - gy)

        row_ind, col_ind = linear_sum_assignment(cost_matrix)
        total_cost = cost_matrix[row_ind, col_ind].sum()
        
        total_cost += min_player_way
        return total_cost
 
    def Calculate_Distance(self, goals):
        distances = {}
        queue = Queue()

        for gx, gy in goals:
            queue.put((gx, gy, 0))
            distances[(gx, gy)] = 0

        while not queue.empty():
            x, y, d = queue.get()
            for dx, dy in [(0,1), (0,-1), (1,0), (-1,0)]:
                nx, ny = x + dx, y + dy
                if not (0 <= nx < self.map_cols and 0 <= ny < self.map_rows):
                    continue
                if self.map[ny][nx] == '#':
                    continue
                if (nx, ny) not in distances:
                    distances[(nx, ny)] = d + 1
                    queue.put((nx, ny, d + 1))

        return distances

    def H2(self, state, goals):
        boxes = list(state.boxes)
        pattern_size = len(boxes) // 2 + 1
        pattern_boxes = boxes[:pattern_size]

        player_x, player_y = state.player
        min_player_way = 10000

        for x, y in boxes:
            min_player_way = min(min_player_way, abs(x - player_x) + abs(y - player_y) - 1)
            if self.map[y][x] != 'X':
                if ((self.Is_Wall(x + 1, y) or self.Is_Wall(x - 1, y)) and
                    (self.Is_Wall(x, y + 1) or self.Is_Wall(x, y - 1))):
                    return float('inf')

        if self.h2_distances == None:
            self.h2_distances = self.Calculate_Distance(goals)

        total = 0
        for bx, by in pattern_boxes:
            if (bx, by) in self.h2_distances:
                total += self.h2_distances[(bx, by)]
            else:
                return float('inf')

        return total + min_player_way

    def H3(self, state, goals):
        boxes = list(state.boxes)

        for x, y in boxes:
            if self.map[y][x] != 'X':
                if ((self.Is_Wall(x + 1, y) or self.Is_Wall(x - 1, y)) and
                    (self.Is_Wall(x, y + 1) or self.Is_Wall(x, y - 1))):
                    return float('inf')

        cost_matrix = np.zeros((len(boxes), len(goals)), dtype=int)
        for i, (bx, by) in enumerate(boxes):
            for j, (gx, gy) in enumerate(goals):
                cost_matrix[i, j] = abs(bx - gx) + abs(by - gy)

        row_ind, col_ind = linear_sum_assignment(cost_matrix)
        total_cost = cost_matrix[row_ind, col_ind].sum()
        
        return total_cost

    def Connect_Ways(self, state_start_end, state_final_end):
        path = list()
        state = state_final_end
        while state is not None:
            path.append(state)
            state = state.prev_state
        path.reverse()

        state = state_start_end.prev_state
        while state is not None:
            path.append(state)
            state = state.prev_state
        
        maps = list()
        for state in path:
            self.steps_counter += 1
            maps.append(self.Create_Map(state))

        self.steps_counter -= 1
        return maps

    def Check_Direction(self, direction, state):
        delta = {
            'up':    (0, -1),
            'down':  (0,  1),
            'left':  (-1, 0),
            'right': (1,  0)
        }
        dx, dy = delta[direction]
        x, y = state.player
        nx, ny = x + dx, y + dy 

        if not (0 <= nx < self.map_cols and 0 <= ny < self.map_rows):
            return None

        if self.map[ny][nx] == '#':
            return None

        boxes = set(state.boxes)
        if (nx, ny) in boxes:
            nnx, nny = nx + dx, ny + dy
            if not (0 <= nnx < self.map_cols and 0 <= nny < self.map_rows):
                return None
            if self.map[nny][nnx] == '#' or (nnx, nny) in boxes:
                return None
            boxes.remove((nx, ny))
            boxes.add((nnx, nny))

        return State((nx, ny), boxes, state)

    def Check_Direction_Backwards(self, direction, state):
        dx, dy = {
            'up':    (0, -1),
            'down':  (0,  1),
            'left':  (-1, 0),
            'right': (1,  0)
        }[direction]

        x, y = state.player
        bx, by = x + dx, y + dy 
        px, py = x - dx, y - dy 
        states = list()

        if not (0 <= bx < self.map_cols and 0 <= by < self.map_rows):
            return states
        if not (0 <= px < self.map_cols and 0 <= py < self.map_rows):
            return states

        if self.map[py][px] == '#':
            return states

        boxes = set(state.boxes)
        
        if (px, py) in boxes:
            return states

        if (bx, by) in boxes:
            states.append(State((px, py), boxes, state))
            boxes.remove((bx, by))
            boxes.add((x, y))
            states.append(State((px, py), boxes, state))
            return states

        states.append(State((px, py), boxes, state))
        return states

    def Create_Map(self, state):
        map = [list(row) for row in self.map]
        x, y = state.player
        if map[y][x] == '.':
            map[y][x] = '@'
        else:
            map[y][x] = '*'

        for box in state.boxes:
            x, y = box
            if map[y][x] == '.':
                map[y][x] = 'B'
            else:
                map[y][x] = '+'

        return map

    def Draw_Map(self, map):
        self.surface.fill((62, 180, 137))
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

    def Draw_Menu(self):
        self.surface.fill((62, 180, 137))
        center_x = self.width // 2

        level = self.font.render(self.levels[self.level_index], True, (0, 0, 0))
        level_rect = level.get_rect(center=(center_x, self.height // 3))
        self.surface.blit(level, level_rect)

        algo_text = self.font.render(f"{self.algorithms[self.algorithm_index]}", True, (0, 0, 0))
        algo_rect = algo_text.get_rect(center=(center_x, self.height // 3 * 2))
        self.surface.blit(algo_text, algo_rect)

    def Draw_Stats(self):
        self.surface.fill((62, 180, 137))
        center_x = self.width // 2

        lines = [
            f"Алгоритм: {self.algorithms[self.algorithm_index]}",
            f"Количество итераций: {self.iteration_count}",
            f"Максимальное количество узлов в O: {self.O_max_node_count}",
            f"Конечное количество узлов в O: {self.O_end_node_count}",
            f"Максимальное количество узлов в памяти: {self.max_node_count}",
            f"Количество шагов: {self.steps_counter}"
        ]

        start_y = self.height // 6
        line_spacing = self.height // 12

        for i, text in enumerate(lines):
            rendered = self.stats_font.render(text, True, (0, 0, 0))
            rect = rendered.get_rect(center=(center_x, start_y + i * line_spacing))
            self.surface.blit(rendered, rect)

    def Draw_Error(self):
        self.surface.fill((62, 180, 137))
        center_x = self.width // 2
        center_y = self.height // 2
        error = self.font.render('Не удалось найти решение', True, (0, 0, 0))
        error_rect = error.get_rect(center=(center_x, center_y))
        self.surface.blit(error, error_rect)


    def A_Star_New(self, level_name, h_number):
        start_state, final_state = self.Create_States(level_name)

        goals = list()
        for y in range(self.map_rows):
            for x in range(self.map_cols):
                if self.map[y][x] == 'X':
                    goals.append((x, y))


        match h_number:
            case 'h1':
                h = self.H1(start_state, goals)
            case 'h2':
                h = self.H2(start_state, goals)

        counter = count()
        O = [(h, next(counter), start_state)]
        heapq.heapify(O)
        open_states = {start_state: h}
        C = {start_state: h}
        directions = ['up', 'down', 'right', 'left']

        while len(O) != 0:
            self.iteration_count += 1
            state_f, _, state = heapq.heappop(O)
            open_states.pop(state)
            C[state] = state_f
            if self.iteration_count % 10000 == 1:
                print(f'Игрок: {state.player}')
                print(f'Коробки: {state.boxes}')
                print(f'Цели: {goals}')
                print(f'f: {state_f}')
                print(f'Итерация: {self.iteration_count}')

            if state == final_state:
                self.h2_distances = None
                self.O_end_node_count = len(O)
                maps = list()
                while state.prev_state != None:
                    self.steps_counter += 1
                    map = self.Create_Map(state)
                    maps.append(map)
                    state = state.prev_state
                map = self.Create_Map(state)
                maps.append(map)
                return maps

            for direction in directions:
                new_state = self.Check_Direction(direction, state)
                if new_state != None:
                    new_state.depth = state.depth + 1
                    match h_number:
                        case 'h1':
                            f = new_state.depth + self.H1(new_state, goals)
                        case 'h2':
                            f = new_state.depth + self.H2(new_state, goals)
                    if new_state not in open_states and new_state not in C:
                        heapq.heappush(O, (f, next(counter), new_state))
                        open_states[new_state] = f
                    elif new_state in open_states and open_states[new_state] > f:
                        len_o = len(O)
                        for i in range(len_o):
                            i_f, i_c, i_state = O[i]
                            if i_state == new_state:
                                O[i] = (f, i_c, new_state)
                                break
                        open_states[new_state] = f
                    elif new_state in C and C[new_state] > f:
                        C.pop(new_state)
                        heapq.heappush(O, (f, next(counter), new_state))
                        open_states[new_state] = f
                    O_size = len(O)
                    self.max_node_count = max(self.max_node_count, len(C) + O_size)
                    self.O_max_node_count = max(self.O_max_node_count, O_size)
                        
        return None

game = Game()
game.Start()