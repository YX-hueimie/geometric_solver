# app/api/schemas.py

"""
================================================================================
 API数据结构手册 (app/api/schemas.py)
================================================================================

致API使用者（尤其是前端工程师）：

你好！这个文件是你的核心参考文档，它精确定义了你需要发送给后端
以及从后端接收的所有JSON对象的格式。

后端服务会严格按照此文件定义的结构来验证请求和生成响应。

主要的数据结构有两个：
1. `GeometricProblem`: 你需要构建并作为POST请求体发送给 `/solve` 端点的对象。
2. `SolverResponse`: `/solve` 端点在处理完你的请求后返回给你的对象。

请仔细阅读每个模型的字段说明以确保顺利对接。
"""
from typing import List, Dict, Any, Union, Optional, Literal
from pydantic import BaseModel, Field

# ==============================================================================
# 1. 请求体模型 (Request Body Models)
# ==============================================================================

class PointKnown(BaseModel):
    """
    描述一个已知的点。
    """
    type: Literal["point"] = Field(description="对象的类型，固定为 'point'。")
    id: str = Field(..., description="点的唯一标识符（例如 'A', 'P1'）。后续定义线或圆时，将使用此ID来引用该点。")
    coords: List[float] = Field(..., description="点的坐标，格式为 [x, y]。例如 [10.5, -3.0]。")

class LineKnown(BaseModel):
    """
    描述一条已知的线。这条线通过引用两个已存在的点的ID来定义的。
    """
    type: Literal["line"] = Field(description="对象的类型，固定为 'line'。")
    id: str = Field(..., description="线的唯一标识符（例如 'l1', 'AB'）。")
    points: List[str] = Field(..., description="一个包含两个点ID的数组，用于定义这条直线。例如 ['A', 'B']。")

class CircleKnown(BaseModel):
    """
    描述一个已知的圆。这个圆是通过引用一个圆心点ID和一个圆周上的点ID来定义的。
    """
    type: Literal["circle"] = Field(description="对象的类型，固定为 'circle'。")
    id: str = Field(..., description="圆的唯一标识符（例如 'c1'）。")
    center: str = Field(..., description="作为圆心的点的ID。例如 'A'。")
    point_on_circumference: str = Field(..., description="位于圆周上的一个点的ID。圆的半径将根据该点到圆心的距离确定。例如 'B'。")

class TargetObject(BaseModel):
    """
    描述你希望求解器构造的“特定”目标对象。
    """
    type: str = Field(..., description="目标对象的类型，可以是 'point', 'line', 或 'circle'。")
    id: str = Field("Target", description="为目标对象设定的一个名称，用于标识。")
    definition: Dict[str, Any] = Field(..., description="一个包含目标对象精确几何定义的字典。")
    # 示例:
    # 1. Point: "definition": { "coords": [3.0, 2.5] }
    # 2. Line:  "definition": { "coeffs": [0.707, -0.707, 0.0] } (归一化的A, B, C系数)
    # 3. Circle:"definition": { "center": [1.0, 1.0], "radius_squared": 4.0 }

class GeometricProblem(BaseModel):
    """
    这是发送到 `/solve` 端点的根JSON对象。它包含了求解一个几何问题所需的所有信息。
    """
    knowns: List[Union[PointKnown, LineKnown, CircleKnown]] = Field(..., description="一个包含所有已知几何对象的数组。数组中可以混合包含点、线、圆。")
    target: TargetObject = Field(..., description="一个描述最终作图目标的对象，包含其精确定义。")

# ==============================================================================
# 2. 响应体模型 (Response Body Models)
# ==============================================================================

class OutputObject(BaseModel):
    """
    描述在作图步骤中新生成的对象。
    """
    type: str
    id: str

class SolutionStep(BaseModel):
    """
    描述作图过程中的一个单独步骤。
    """
    step: int
    operation: str
    inputs: List[str]
    output: OutputObject

class PerformanceMetrics(BaseModel):
    """
    包含关于求解过程性能的统计数据。
    """
    calculation_time_ms: float
    states_explored: int

class SolverResponse(BaseModel):
    """
    这是从 `/solve` 端点返回的根JSON对象。
    """
    status: str
    steps: List[SolutionStep]
    performance: Optional[PerformanceMetrics] = None