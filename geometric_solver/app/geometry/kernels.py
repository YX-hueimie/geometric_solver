# app/geometry/kernels.py

"""
================================================================================
 高性能几何计算内核 (app/geometry/kernels.py)
================================================================================

模块功能:
本模块是整个系统的“计算引擎”。它包含了所有底层的、纯粹的几何运算函数，
例如求两条直线的交点、根据两点构造圆等。这些函数构成了所有几何作图操作
的基础。

核心技术 - Numba JIT (即时编译):
- **性能瓶颈**: 纯Python在执行密集的数学计算时速度较慢。在一个复杂的作图
  问题中，搜索算法可能需要执行数百万次几何运算，这将成为巨大的性能瓶颈。
- **解决方案**: 我们使用Numba库的`@njit`装饰器。这个装饰器会在函数第一次
  被调用时，将其从Python代码“翻译”成高度优化的、速度接近C语言的机器码。
- **最终效果**: 经过JIT编译后，这些几何运算的速度可以比纯Python实现快上百
  甚至上千倍。这使得我们有能力在可接受的时间内探索巨大的搜索空间，找到
  最优解。

使用约定:
本模块中的所有函数都工作在“Numba世界”中，为了最高效率，它们只接受并返回
NumPy数组作为参数和返回值。

[函数返回格式说明]
为了兼容Numba JIT编译器的严格类型要求，所有求交点函数
(intersect_*) 都遵循统一的返回格式：一个元组 `(results, count)`。
- `results`: 一个固定的 2x2 NumPy数组，用于存放最多两个点的坐标。
- `count`: 一个整数(0, 1, or 2)，表示实际找到的交点数量。
"""
import numpy as np
from numba import njit

# 定义一个微小量，用于在JIT编译的代码中进行浮点数比较，避免精度问题。
EPSILON = 1e-9

@njit(cache=True)
def construct_line_from_points(p1, p2):
    """
    根据两个点坐标，构造一条直线。
    
    数学原理:
    给定点 P1(x1, y1) 和 P2(x2, y2)，其直线方程的标准形式为 Ax + By + C = 0。
    系数可以通过行列式或直接推导得出：
    A = y1 - y2
    B = x2 - x1
    C = x1*y2 - x2*y1

    Args:
        p1 (np.array): 第一个点的坐标数组, [x1, y1]。
        p2 (np.array): 第二个点的坐标数组, [x2, y2]。

    Returns:
        np.array: 代表直线方程系数的数组 [A, B, C]。
    """
    A = p1[1] - p2[1]
    B = p2[0] - p1[0]
    C = p1[0] * p2[1] - p2[0] * p1[1]
    return np.array([A, B, C], dtype=np.float64)

@njit(cache=True)
def construct_circle_from_points(center, point_on_circumference):
    """
    根据圆心和圆周上的一点，构造一个圆。

    Args:
        center (np.array): 圆心坐标数组, [cx, cy]。
        point_on_circumference (np.array): 圆周上一点的坐标数组, [px, py]。

    Returns:
        np.array: 代表圆的数组 [cx, cy, r_squared]，其中 r_squared 是半径的平方，
                  以避免在后续计算中进行不必要的开方运算。
    """
    cx, cy = center
    px, py = point_on_circumference
    r_squared = (px - cx)**2 + (py - cy)**2
    return np.array([cx, cy, r_squared], dtype=np.float64)

@njit(cache=True)
def intersect_line_line(line1, line2):
    """
    计算两条直线的交点。
    返回一个元组 (results, count)。
    """
    results = np.full((2, 2), np.nan, dtype=np.float64)
    A1, B1, C1 = line1
    A2, B2, C2 = line2
    det = A1 * B2 - A2 * B1

    if abs(det) < EPSILON:
        return results, 0

    x = (B2 * -C1 - B1 * -C2) / det
    y = (A1 * -C2 - A2 * -C1) / det
    
    results[0, 0] = x
    results[0, 1] = y
    return results, 1

@njit(cache=True)
def intersect_line_circle(line, circle):
    """
    计算一条直线和一个圆的交点。
    返回一个元组 (results, count)。
    """
    results = np.full((2, 2), np.nan, dtype=np.float64)
    A, B, C = line
    cx, cy, r_sq = circle
    
    det_line = A * A + B * B
    if det_line < EPSILON:
        return results, 0

    x_closest = (B * B * cx - A * B * cy - A * C) / det_line
    y_closest = (-A * B * cx + A * A * cy - B * C) / det_line
    
    dist_sq = (x_closest - cx)**2 + (y_closest - cy)**2
    
    if dist_sq > r_sq + EPSILON:
        return results, 0
    
    if abs(dist_sq - r_sq) < EPSILON:
        results[0, 0] = x_closest
        results[0, 1] = y_closest
        return results, 1

    half_chord_length = np.sqrt(r_sq - dist_sq)
    line_dir_norm = np.sqrt(det_line)
    
    p1_x = x_closest + (half_chord_length * -B) / line_dir_norm
    p1_y = y_closest + (half_chord_length * A) / line_dir_norm
    results[0, 0] = p1_x
    results[0, 1] = p1_y
    
    p2_x = x_closest - (half_chord_length * -B) / line_dir_norm
    p2_y = y_closest - (half_chord_length * A) / line_dir_norm
    results[1, 0] = p2_x
    results[1, 1] = p2_y

    return results, 2

@njit(cache=True)
def intersect_circle_circle(c1, c2):
    """
    计算两个圆的交点。
    返回一个元组 (results, count)。
    """
    results = np.full((2, 2), np.nan, dtype=np.float64)
    x1, y1, r1_sq = c1
    r1 = np.sqrt(r1_sq)
    x2, y2, r2_sq = c2
    r2 = np.sqrt(r2_sq)

    d_sq = (x1 - x2)**2 + (y1 - y2)**2
    
    if d_sq < EPSILON: # 同心圆
        return results, 0

    d = np.sqrt(d_sq)

    if d > r1 + r2 + EPSILON or d < abs(r1 - r2) - EPSILON:
        return results, 0
    
    A = 2 * (x2 - x1)
    B = 2 * (y2 - y1)
    C = (x1**2 - x2**2) + (y1**2 - y2**2) - (r1_sq - r2_sq)
    radical_line = np.array([A, B, C], dtype=np.float64)

    return intersect_line_circle(radical_line, c1)