# app/api/main.py

"""
================================================================================
 API端点手册 (app/api/main.py)
================================================================================

致API使用者（尤其是前端工程师）：

这个文件是API服务器的入口点。它使用FastAPI框架来设置和定义所有HTTP端点。
你将通过网络请求与这里定义的端点进行交互。

交互式文档 (Swagger UI):
后端服务运行时，我们强烈建议你访问自动生成的交互式API文档。
1. 运行后端服务器。
2. 在浏览器中打开 http://127.0.0.1:8000/docs。
3. 在该页面，你可以浏览所有端点、查看其详细的请求/响应模型，并直接发送
   测试请求来验证你的前端逻辑。

核心端点:
- **`POST /solve`**: 这是本服务的核心功能。你将一个描述几何问题的JSON对象
  (`GeometricProblem` 结构)发送到此端点，服务会返回一个包含最优解题步骤
  的JSON响应 (`SolverResponse` 结构)。
"""
import time
from fastapi import FastAPI, HTTPException
from .schemas import GeometricProblem, SolverResponse, PerformanceMetrics
from app.solver.search import solve as solve_geometric_problem
from app.geometry import kernels
import numpy as np

app = FastAPI(
    title="高性能几何求解器 (High-Performance Geometric Solver)",
    description="一个使用即时编译(JIT)分支限界算法来寻找最优几何作图序列的API。",
    version="1.1.0",
)

@app.post("/solve", response_model=SolverResponse, tags=["Solver"])
def solve_problem(problem: GeometricProblem):
    """
    接收一个包含“已知”和“目标”的几何问题，进行求解，并返回最优的作图步骤。

    **功能**:
    此端点是后端求解能力的主要入口。它接收一个JSON对象，其中定义了初始的
    几何图形和希望构造的特定目标。后端会运行高性能的A*搜索算法，寻找从
    “已知”到“目标”的最少作图步骤。

    **请求体 (Request Body)**:
    - 一个符合 `GeometricProblem` 模型的JSON对象。详细结构请参考 
      `app/api/schemas.py` 文件或 `/docs` 页面。

    **成功响应 (Success Response - HTTP 200)**:
    - 返回一个 `SolverResponse` 类型的JSON对象。
    - `status` 字段会是 "solved" 或 "unsolvable"。
    - `steps` 字段会包含一个详细的步骤数组（如果已解决）。
    - `performance` 字段会包含本次请求的计算耗时和复杂度信息。

    **错误响应 (Error Responses)**:
    - **HTTP 422 (Unprocessable Entity)**: 请求的JSON结构正确，但内容逻辑
      有误（例如，一条线引用了一个不存在的点ID）。
    - **HTTP 400 (Bad Request)**: 输入的几何定义无效或无法处理。
    - **HTTP 500 (Internal Server Error)**: 服务器在处理过程中发生了未预料
      到的内部错误。
    """
    # 阶段 1: 数据编组 (Marshalling)
    # 此阶段将前端发送的、人类可读的JSON对象，转换为后端内部使用的、为性能
    # 优化的数据格式（主要是NumPy数组）。
    try:
        initial_objects = {'points': {}, 'lines': {}, 'circles': {}}
        for obj in problem.knowns:
            if obj.type == 'point':
                initial_objects['points'][obj.id] = np.array(obj.coords, dtype=np.float64)
        for obj in problem.knowns:
            if obj.type == 'line':
                p1 = initial_objects['points'][obj.points[0]]
                p2 = initial_objects['points'][obj.points[1]]
                initial_objects['lines'][obj.id] = kernels.construct_line_from_points(p1, p2)
            elif obj.type == 'circle':
                center = initial_objects['points'][obj.center]
                on_circ = initial_objects['points'][obj.point_on_circumference]
                initial_objects['circles'][obj.id] = kernels.construct_circle_from_points(center, on_circ)
    except KeyError as e:
        raise HTTPException(status_code=422, detail=f"请求实体无法处理：无效的对象ID引用。在已知条件中未找到ID '{e.args[0]}'。")
    
    # 解析精确的目标定义
    target_definition_from_api = problem.target.definition
    target_type = problem.target.type
    target_internal_def = {'type': target_type}
    try:
        if target_type == 'point':
            target_internal_def['data'] = np.array(target_definition_from_api['coords'], dtype=np.float64)
        elif target_type == 'line':
            # 直接使用前端预先计算好的、规范化的直线系数
            target_internal_def['data'] = np.array(target_definition_from_api['coeffs'], dtype=np.float64)
        elif target_type == 'circle':
            # 直接使用前端提供的圆心和半径平方
            center = np.array(target_definition_from_api['center'], dtype=np.float64)
            r_sq = float(target_definition_from_api['radius_squared'])
            target_internal_def['data'] = np.array([center[0], center[1], r_sq], dtype=np.float64)
        else:
            raise ValueError(f"不支持的目标类型: {target_type}")
    except KeyError as e:
        raise HTTPException(status_code=422, detail=f"定义目标时出错：在已知条件中未找到用于定义目标的ID '{e.args[0]}'。")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 阶段 2: 调用核心求解器并监控性能
    # 记录求解函数开始前和结束后的时间，以精确计算执行耗时。
    start_time = time.perf_counter()
    solution_steps, stats = solve_geometric_problem(initial_objects, target_internal_def)
    end_time = time.perf_counter()
    
    performance = PerformanceMetrics(
        calculation_time_ms=(end_time - start_time) * 1000,
        states_explored=stats["states_explored"]
    )

    # 阶段 3: 数据解组 (Unmarshalling)
    # 将求解器返回的内部数据结构，转换成符合 `SolverResponse` 模型的、
    # 标准化的JSON格式，然后发送给前端。
    if solution_steps:
        for i, step in enumerate(solution_steps):
            step['step'] = i + 1
        return SolverResponse(status="solved", steps=solution_steps, performance=performance)
    else:
        return SolverResponse(status="unsolvable", steps=[], performance=performance)

@app.get("/", include_in_schema=False)
def root():
    """根路径，用于简单的健康检查或服务发现。"""
    return {"message": "几何求解器API正在运行。请访问 /docs 查看API文档。"}