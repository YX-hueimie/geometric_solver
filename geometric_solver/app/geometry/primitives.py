# app/geometry/primitives.py

"""
================================================================================
 几何图元与状态哈希模块 (app/geometry/primitives.py)
================================================================================

模块功能:
本模块负责两件核心任务：
1.  **数据表示**: 定义几何对象（点、线、圆）在内存中的标准表示方式。
2.  **状态规范化与哈希**: 为任何一个几何状态（当前所有已知对象的集合）生成
    一个唯一的、可比较的、可作为字典键或集合元素的“指纹”（哈希值）。

工作原理 (状态规范化与哈希):
- **核心挑战**: 在搜索算法中，我们需要一个`visited`集合来记录所有已经探索过
  的状态，以避免重复计算和陷入死循环。然而，由浮点数定义的几何对象不能
  直接作为键或放入集合中。
- **原因**: 计算机浮点数存在精度问题（例如 `0.1 + 0.2` 不精确等于 `0.3`）。
  这会导致两个在几何上完全等价的状态，可能因为作图顺序不同而导致其内部
  浮点数坐标存在微小的差异。如果直接哈希，它们会被误认为是两个不同的状态，
  导致算法进行大量不必要的重复工作。

- **解决方案 (规范化流程)**: 我们为每个几何状态设计了一套严格的“规范化”流程，
  以确保“所见相同即所得相同”。
    1.  **统一精度**: 所有浮点数坐标都四舍五入到统一的、足够高的小数位数。
        这消除了微小的计算噪声。
    2.  **对象内部规范化**: 每种类型的对象都被转换为一种唯一的数学表示形式。
        - **点**: 其坐标元组。
        - **直线**: 其标准方程 `Ax+By+C=0` 的系数被归一化（使 `A^2+B^2=1`），
          并遵循统一的符号约定。这样，由(P1,P2)定义的直线和由(P2,P1)定义的
          直线将具有完全相同的规范表示。
        - **圆**: 由圆心坐标和半径的平方组成。
    3.  **状态整体规范化**: 将一个状态内的所有规范化对象按类型分组，并在组内
        按字典序排序。

- **最终结果**: 经过这套流程后，任何两个在几何上等价的状态，无论它们是
  通过何种作图顺序得到的，都会生成完全相同的、可哈希的元组。这保证了
  `visited`集合的绝对可靠，是算法正确性和效率的关键基石。
"""
import numpy as np

# 定义用于规范化和哈希的浮点数精度。
# 这是一个关键参数，它平衡了精度和对计算误差的容忍度。
HASH_PRECISION = 10

def normalize_point(p):
    """
    为点创建一个规范化的、可哈希的表示。

    Args:
        p (np.array): 点的坐标数组 [x, y]。

    Returns:
        tuple: 四舍五入后的坐标元组 (rounded_x, rounded_y)。
    """
    return (round(p[0], HASH_PRECISION), round(p[1], HASH_PRECISION))

def normalize_line(l):
    """
    为直线创建一个规范化的、可哈希的表示。

    Args:
        l (np.array): 直线的系数数组 [A, B, C]。

    Returns:
        tuple: 经过归一化和符号固定的系数元组 (norm_A, norm_B, norm_C)。
    """
    A, B, C = l
    norm = np.sqrt(A**2 + B**2)
    if norm < 1e-9: # 对于有效直线，这不应发生
        return (0.0, 0.0, 0.0)
    
    A, B, C = A / norm, B / norm, C / norm
    
    # 强制执行符号约定（例如，第一个非零系数必须为正），以确保唯一性。
    if abs(A) > 1e-9 and A < 0:
        A, B, C = -A, -B, -C
    elif abs(A) < 1e-9 and abs(B) > 1e-9 and B < 0:
        A, B, C = -A, -B, -C
        
    return (
        round(A, HASH_PRECISION),
        round(B, HASH_PRECISION),
        round(C, HASH_PRECISION)
    )

def normalize_circle(c):
    """
    为圆创建一个规范化的、可哈希的表示。

    Args:
        c (np.array): 圆的数组 [cx, cy, r_sq]。

    Returns:
        tuple: 四舍五入后的圆心和半径平方元组 (rounded_cx, rounded_cy, rounded_r_sq)。
    """
    return (
        round(c[0], HASH_PRECISION),
        round(c[1], HASH_PRECISION),
        round(c[2], HASH_PRECISION)
    )

def get_state_hash(current_objects):
    """
    为整个几何状态生成一个唯一的、规范化的哈希值。
    
    Args:
        current_objects (dict): 一个包含当前所有点、线、圆的字典。
    
    Returns:
        一个可哈希的、排序的、不可变的嵌套元组，代表整个状态的“指纹”。
    """
    # 对每种类型的对象进行规范化和排序
    norm_points = sorted([normalize_point(p) for p in current_objects['points'].values()])
    norm_lines = sorted([normalize_line(l) for l in current_objects['lines'].values()])
    norm_circles = sorted([normalize_circle(c) for c in current_objects['circles'].values()])
    
    # 将所有排序后的对象组合成一个大的、不可变的元组
    return (
        ('points',) + tuple(norm_points),
        ('lines',) + tuple(norm_lines),
        ('circles',) + tuple(norm_circles)
    )