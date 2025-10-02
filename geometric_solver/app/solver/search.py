# app/solver/search.py

"""
================================================================================
 核心求解算法模块 (app/solver/search.py)
================================================================================

模块功能:
本模块是求解器的“大脑”，实现了A* (A-star) 路径搜索算法，负责寻找最优的
几何作图序列。

工作原理:
1.  **状态空间搜索**: 它将“几何作图”问题抽象为一个在巨大的、由所有可能
    的几何状态构成的“地图”上寻找路径的问题。

2.  **寻找最短路径**: 目标是找到从“初始状态”到“目标状态”的“最短路径”，
    也即作图步骤最少。

3.  **A* 算法**: 它使用A*算法智能地优先探索那些“看起来最有希望”的路径。
    评估函数为 f(n) = g(n) + h(n)，其中 g(n) 是已知成本，h(n) 是预估成本。

4.  **目标测试**: 在搜索的每一步，当一个新几何对象被构造出来时，目标测试函数
    `is_goal`会立即将其与用户传入的“精确目标定义”进行几何比对。

5.  **资源控制**: 为了防止因极端复杂问题导致内存耗尽，算法内置了一个“安全阀”，
    限制了待探索路径队列的最大长度 (`MAX_OPEN_LIST_SIZE`)。

"""

import heapq
import itertools
from collections import namedtuple
import numpy as np
from app.geometry import kernels
from app.geometry.primitives import get_state_hash, normalize_point, normalize_line, normalize_circle
from app.solver.heuristic import calculate_heuristic

SearchNode = namedtuple('SearchNode', ['priority', 'tie_breaker', 'g_cost', 'state', 'path'])
State = namedtuple('State', ['objects', 'next_ids'])

MAX_OPEN_LIST_SIZE = 150_000

def solve(initial_objects, target_definition, max_steps=20):
    initial_ids = {
        'point': max([int(k[1:]) for k in initial_objects['points'] if k[1:].isdigit()] or [0]) + 1,
        'line': max([int(k[1:]) for k in initial_objects['lines'] if k[1:].isdigit()] or [0]) + 1,
        'circle': max([int(k[1:]) for k in initial_objects['circles'] if k[1:].isdigit()] or [0]) + 1,
    }
    initial_state = State(objects=initial_objects, next_ids=initial_ids)

    target_type = target_definition['type']
    norm_funcs = { 'point': normalize_point, 'line': normalize_line, 'circle': normalize_circle }
    target_norm = norm_funcs[target_type](target_definition['data'])

    def is_goal(newly_created_object_data, object_type):
        if object_type != target_type: return False
        # 此处修正了变量名的拼写错误
        new_obj_norm = norm_funcs[object_type](newly_created_object_data)
        return new_obj_norm == target_norm

    open_list = []
    visited = set()
    tie_breaker_counter = itertools.count()

    g_cost = 0
    h_cost = calculate_heuristic(initial_state.objects, target_type)
    initial_node = SearchNode(
        priority=g_cost + h_cost, tie_breaker=next(tie_breaker_counter), g_cost=g_cost, state=initial_state, path=[]
    )
    heapq.heappush(open_list, initial_node)
    initial_hash = get_state_hash(initial_state.objects)
    visited.add(initial_hash)

    while open_list:
        priority, tie_breaker, g_cost, current_state, path = heapq.heappop(open_list)
        if g_cost >= max_steps: continue

        successors = generate_successors(current_state)
        
        for new_objects_state, step_info in successors:
            new_state_hash = get_state_hash(new_objects_state)
            if new_state_hash in visited: continue
            
            if len(open_list) > MAX_OPEN_LIST_SIZE: continue

            visited.add(new_state_hash)
            output_info = step_info['output']
            newly_created_id = output_info['id']
            newly_created_type = output_info['type']
            newly_created_data = new_objects_state[f'{newly_created_type}s'][newly_created_id]
            new_path = path + [step_info]
            
            if is_goal(newly_created_data, newly_created_type):
                stats = {"states_explored": len(visited)}
                return new_path, stats
            
            new_g = g_cost + 1
            new_h = calculate_heuristic(new_objects_state, target_type)
            if new_h == float('inf'): continue

            new_priority = new_g + new_h
            current_ids = current_state.next_ids
            
            new_id_num = int(step_info['output']['id'][1:])
            new_ids = {**current_ids}
            if new_id_num >= new_ids[newly_created_type]:
                 new_ids[newly_created_type] = new_id_num + 1
                 
            new_state = State(objects=new_objects_state, next_ids=new_ids)
            new_node = SearchNode(
                priority=new_priority, tie_breaker=next(tie_breaker_counter), g_cost=new_g, state=new_state, path=new_path
            )
            heapq.heappush(open_list, new_node)

    stats = {"states_explored": len(visited)}
    return None, stats


def _add_object(current_objects, obj_type, obj_id_num, obj_data):
    new_objects = {
        'points': current_objects['points'].copy(),
        'lines': current_objects['lines'].copy(),
        'circles': current_objects['circles'].copy()
    }
    type_plural = f"{obj_type}s"
    norm_func = {'point': normalize_point, 'line': normalize_line, 'circle': normalize_circle}[obj_type]
    new_obj_norm = norm_func(obj_data)
    for existing_data in new_objects[type_plural].values():
        if norm_func(existing_data) == new_obj_norm:
            return new_objects, False, None
            
    new_id = f"{obj_type[0]}{obj_id_num}"
    new_objects[type_plural][new_id] = obj_data
    return new_objects, True, new_id


def generate_successors(state):
    objects, next_ids = state
    successors = []
    points, lines, circles = objects['points'], objects['lines'], objects['circles']
    
    # --- 1. 最优先：生成点的后继状态 (通过求交点) ---
    intersection_configs = []
    if len(lines) >= 2:
        intersection_configs.extend([("ll", c) for c in itertools.combinations(lines.keys(), 2)])
    if lines and circles:
        intersection_configs.extend([("lc", p) for p in itertools.product(lines.keys(), circles.keys())])
    if len(circles) >= 2:
        intersection_configs.extend([("cc", c) for c in itertools.combinations(circles.keys(), 2)])

    points_generated_in_this_call = 0
    for op_type, item_ids in intersection_configs:
        if op_type == "ll":
            l1_id, l2_id = item_ids
            results, count = kernels.intersect_line_line(lines[l1_id], lines[l2_id])
        elif op_type == "lc":
            l_id, c_id = item_ids
            results, count = kernels.intersect_line_circle(lines[l_id], circles[c_id])
        else: # "cc"
            c1_id, c2_id = item_ids
            results, count = kernels.intersect_circle_circle(circles[c1_id], circles[c2_id])
        
        if count == 0:
            continue

        obj_after_adds = objects
        added_new_point = False
        new_point_ids = []
        
        for i in range(count):
            p_data = results[i]
            obj_after_adds, is_new, new_id = _add_object(obj_after_adds, 'point', next_ids['point'] + points_generated_in_this_call, p_data)
            if is_new:
                added_new_point = True
                new_point_ids.append(new_id)
                points_generated_in_this_call += 1
        
        if added_new_point:
            step = {"operation": "Intersection", "inputs": list(item_ids), "output": {"type": "point", "id": new_point_ids[0]}}
            successors.append((obj_after_adds, step))

    # --- 2. 其次：生成线的后继状态 ---
    if len(points) >= 2:
        for p1_id, p2_id in itertools.combinations(points.keys(), 2):
            new_line_data = kernels.construct_line_from_points(points[p1_id], points[p2_id])
            new_objs, is_new, new_id = _add_object(objects, 'line', next_ids['line'], new_line_data)
            if is_new:
                step = {"operation": "Line", "inputs": [p1_id, p2_id], "output": {"type": "line", "id": new_id}}
                successors.append((new_objs, step))

    # --- 3. 最后：生成圆的后继状态 ---
    if len(points) >= 2:
        for center_id, on_circ_id in itertools.permutations(points.keys(), 2):
            new_circle_data = kernels.construct_circle_from_points(points[center_id], points[on_circ_id])
            new_objs, is_new, new_id = _add_object(objects, 'circle', next_ids['circle'], new_circle_data)
            if is_new:
                step = {"operation": "Circle", "inputs": [center_id, on_circ_id], "output": {"type": "circle", "id": new_id}}
                successors.append((new_objs, step))
    
    return successors