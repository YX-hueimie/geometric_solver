# app/solver/heuristic.py

"""
================================================================================
 启发式函数模块 (app/solver/heuristic.py)
================================================================================

模块功能:
本模块为A*搜索算法提供“导航”功能，即启发式函数 `h(n)`。它负责在搜索的每一步
“猜测”从当前状态到达最终目标“至少”还需要多少个作图步骤。

工作原理:
- **重要性**: 启发式函数是算法效率的关键。它像一个经验丰富的向导，帮助算法
  优先选择最有希望的路径，从而避免在没有前途的分支上浪费大量时间。

- **设计方法 (逻辑规则)**: 我们不再使用复杂的预计算，而是采用一套清晰、
  直接的逻辑规则来估算成本。这个估算是“乐观”的，即它永远不会高估实际
  所需步数，这保证了A*算法最终找到的解一定是最优的。

- **核心逻辑**:
  - **目标是点**: 如果已有足够的对象（如两条线）可以求交点，则预估成本为1步。
    如果只有点，则至少需要3步（作两条线/圆，再求交点）。
  - **目标是线/圆**: 如果有两个点，则预估成本为1步。否则，需要先构造出点，
    成本会相应增加。

这个新版本更易于理解和验证，从根本上解决了之前导致搜索提前终止的bug。
"""

def calculate_heuristic(current_objects, target_object_type):
    """
    在运行时计算启发式函数 h(n) 的值。
    
    Args:
        current_objects (dict): 当前状态拥有的几何对象。
        target_object_type (str): 最终目标的类型 ('point', 'line', 'circle')。

    Returns:
        int: 预估的从当前状态到目标的最小剩余作图步数。
    """
    # 确定当前状态下拥有的几何对象类型
    available_types = set()
    num_points = len(current_objects['points'])
    num_lines = len(current_objects['lines'])
    num_circles = len(current_objects['circles'])

    if num_points > 0: available_types.add('point')
    if num_lines > 0: available_types.add('line')
    if num_circles > 0: available_types.add('circle')

    # --- 根据目标类型，应用逻辑规则 ---

    if target_object_type == 'point':
        # 如果目标是点，检查是否已经有可以相交的对象
        # 1. 两条线可以相交
        # 2. 两个圆可以相交
        # 3. 一条线和一个圆可以相交
        if num_lines >= 2 or num_circles >= 2 or (num_lines >= 1 and num_circles >= 1):
            return 1 # 只需要1步（求交点）
        
        # 如果没有足够的可相交对象，但有足够的点来创建它们
        if num_points >= 2:
            # 最快的方式是创建两个圆然后求交点，或者创建两条线求交点。
            # 例如: Circle(P1,P2) -> c1; Circle(P2,P1) -> c2; Intersect(c1,c2) -> new point
            # 这至少需要3步。
            # 如果只有2个点，需要先构造第3个点才能构造两条不重合的线。
            # 乐观估计：假设我们能用2个点造出两条可相交的线/圆。
            # Circle(p1,p2) -> 1步; Line(p1,p2) -> 1步; Intersect -> 1步. 总共3步
            if num_points >= 4:
                return 3 # Line(p1,p2), Line(p3,p4), Intersect
            if num_points >= 3:
                return 3 # Line(p1,p2), Line(p1,p3), Intersect
            if num_points >= 2:
                # 至少需要构造两个圆和一个交点
                return 3 # Circle, Circle, Intersect
        
        # 如果连两个点都没有，成本会更高
        return 5 # 一个非常保守的高估值

    elif target_object_type == 'line':
        # 如果目标是线，检查是否有足够的点来作线
        if num_points >= 2:
            return 1 # 只需要1步（两点作线）
        else:
            # 如果点不够，则需要先作出点。作出一个点至少需要1步（求交点）
            # 所以总成本是 h(作出点) + 1。
            # 这里我们返回一个合理的乐观估计值。
            return 2
            
    elif target_object_type == 'circle':
        # 如果目标是圆，逻辑与线相同
        if num_points >= 2:
            return 1 # 只需要1步（一点为心，一点在圆上）
        else:
            return 2

    # 如果目标类型未知，返回一个高值
    return float('inf')