# 高性能几何作图求解器后端

## 简介

本项目是一个专为几何作图软件设计的高性能后端服务。其核心功能是接收一组“已知”的几何对象（点、线、圆）和一个“目标”几何对象，然后通过模拟尺规作图（连线、作圆、求交点），找出从“已知”构造出“目标”的**步骤最少**的作图序列。

您可以把它想象成一个几何问题的“最优路径导航器”，能够为任意复杂的几何构造问题，智能地推算出最优雅、最简洁的尺规作图解法。

## 核心功能

-   **最优解保证 (Optimal Solutions)**
    采用 A\* (分支限界) 搜索算法，确保找到的每一个解都是步骤数最少的作图方案。

-   **极致性能 (High Performance)**
    通过以 NumPy 为中心的面向数据设计，以及利用 Numba 对计算密集型几何内核进行即时编译（JIT），将 Python 的执行效率提升至接近原生编译语言的水平，即使是10步以上的复杂问题也能在秒级完成求解。

-   **鲁棒可靠 (Robust & Reliable)**
    集成了基于自适应精度浮点运算的“鲁棒几何谓词”，从根本上解决了计算机浮点数舍入误差导致的几何判断错误问题，确保算法在处理任何几何构型（包括三点共线等退化情况）时都能保持稳定和正确。

-   **现代化API (Modern API)**
    通过 FastAPI 框架提供了一套遵循 RESTful 规范的现代化Web API。接口定义清晰，并能自动生成交互式的 API 文档（通过 Swagger UI），极大地简化了前端的对接与调试工作。

## 技术架构

本项目的技术选型和架构设计旨在同时实现**算法的最优性**、**计算的高性能**和**工程的可靠性**。

-   **算法核心**：将几何作图问题严谨地建模为在隐式图（Implicit Graph）中的**状态空间搜索**问题。我们采用 **A\* 搜索算法** 作为核心，它通过一个高效的**启发式函数（Heuristic Function）**进行智能剪枝，在庞大的可能性空间中高效地寻找最优路径。

-   **性能核心**：
    -   **数据层**：所有几何图元（点、线、圆）均使用 **NumPy** 的 `ndarray` 进行表示，以实现高效的内存布局和向量化计算。
    -   **计算层**：所有底层的几何运算（如求交点）都被封装在独立的函数中，并使用 **Numba** 的 `@njit` 装饰器进行即时编译。这使得Python的计算性能瓶颈被彻底打破。

-   **接口层**：使用 **FastAPI** 框架构建API服务。它基于Pydantic进行数据验证，确保了接口的健壮性，同时其异步特性也为高并发场景提供了支持。

## 安装与运行

#### 1. 环境要求
- Python 3.9+

#### 2. 安装步骤

```bash
# 克隆项目到本地
# git clone <your-repo-url>
# cd geometric_solver

# 创建并激活Python虚拟环境
python -m venv venv
# 在 Windows 上:
# venv\Scripts\activate
# 在 macOS / Linux 上:
# source venv/bin/activate

# 安装所有依赖项
pip install -r requirements.txt
```

#### 3. 启动服务
在项目根目录下，运行以下命令：
```bash
uvicorn app.api.main:app --reload
```
服务启动后，您将在终端看到 `Uvicorn running on http://127.0.0.1:8000` 的提示。

#### 4. 访问API文档
服务运行时，在浏览器中打开 `http://127.0.0.1:8000/docs` 即可访问自动生成的交互式API文档。

## API使用指南

#### 端点: `POST /solve`

这是唯一的核心功能端点，用于接收并求解几何问题。

#### 请求体格式 (`application/json`)

您需要发送一个JSON对象，其中包含 `knowns` (已知条件) 和 `target` (目标) 两个字段。

**示例：求解线段AB的垂直平分线**

```json
{
  "knowns": [
    {
      "type": "point",
      "id": "A",
      "coords": [1, 1]
    },
    {
      "type": "point",
      "id": "B",
      "coords": [5, 5]
    }
  ],
  "target": {
    "type": "line",
    "id": "PerpBisector",
    "definition": {
      "coeffs": [0.7071067812, 0.7071067812, -8.4852813742]
    }
  }
}
```
* `knowns`: 一个对象数组，描述了所有初始几何元素。
* `target`: 一个对象，描述了希望构造的最终几何元素。
    * `definition`: 包含目标的精确几何定义。对于直线，`coeffs` 是其标准方程 `Ax+By+C=0` 经过归一化（`A^2+B^2=1`）后的系数 `[A, B, C]`。

#### 响应体格式 (`application/json`)

如果求解成功，服务器将返回一个包含作图步骤和性能数据的JSON对象。

**示例：成功求解的响应**
```json
{
  "status": "solved",
  "steps": [
    {
      "step": 1,
      "operation": "Circle",
      "inputs": ["A", "B"],
      "output": { "type": "circle", "id": "c1" }
    },
    {
      "step": 2,
      "operation": "Circle",
      "inputs": ["B", "A"],
      "output": { "type": "circle", "id": "c2" }
    },
    {
      "step": 3,
      "operation": "Intersection",
      "inputs": ["c1", "c2"],
      "output": { "type": "point", "id": "p1" }
    },
    {
      "step": 4,
      "operation": "Line",
      "inputs": ["p1", "p2"],
      "output": { "type": "line", "id": "l1" }
    }
  ],
  "performance": {
    "calculation_time_ms": 42.12,
    "states_explored": 85
  }
}
```
* `status`: "solved" 表示成功找到解。
* `steps`: 一个数组，按顺序描述了最优的作图步骤。前端可以根据此数组进行动态的可视化渲染。
* `performance`: 包含后端计算耗时和问题复杂度的统计信息。

#### 使用 `cURL` 进行测试

您可以使用 `curl` 等工具来测试API。请确保您的测试JSON文件（例如 `test_02_perp_bisector.json`）与 `curl` 命令在同一目录下。

**在 Windows PowerShell 中:**
```powershell
curl.exe -X POST "[http://127.0.0.1:8000/solve](http://127.0.0.1:8000/solve)" -H "Content-Type: application/json" -d "@test_02_perp_bisector.json"
```

**在 macOS / Linux 或 Windows CMD 中:**
```bash
curl -X POST "[http://127.0.0.1:8000/solve](http://127.0.0.1:8000/solve)" -H "Content-Type: application/json" -d @test_02_perp_bisector.json
```

## 项目结构

```
/geometric_solver
|-- /app
|   |-- /api
|   |   |-- main.py        # FastAPI应用入口，定义API端点
|   |   |-- schemas.py     # Pydantic模型，定义API的数据结构
|   |-- /solver
|   |   |-- search.py      # A*搜索算法核心实现
|   |   |-- heuristic.py   # 启发式函数计算
|   |-- /geometry
|   |   |-- primitives.py  # 几何对象的规范化与哈希函数
|   |   |-- kernels.py     # Numba JIT加速的几何运算函数
|   |   |-- predicates.py  # 鲁棒几何谓词的封装
|-- /tests                 # 单元测试与集成测试
|   |-- test_01_midpoint.json # 测试文件示例
|   |-- ...
|-- requirements.txt       # 项目依赖
|-- README.md              # 本文件
```

