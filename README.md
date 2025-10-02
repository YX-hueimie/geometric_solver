# High-Performance Geometric Solver Backend

This project implements a high-performance backend for solving optimal geometric construction problems, as detailed in the design report.

It uses a Branch and Bound (A\*) algorithm to find the shortest construction sequence. The performance is achieved through:

-   **NumPy:** for efficient, data-oriented representation of geometric primitives.
-   **Numba:** for Just-In-Time (JIT) compilation of computationally intensive geometric kernels.
-   **Robust Geometric Predicates:** to ensure numerical stability and correctness.

The backend is exposed as a RESTful API built with FastAPI.

## Installation

1.  **Create a virtual environment:**

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Running the Server

Use `uvicorn` to run the FastAPI application:

```bash
uvicorn app.api.main:app --reload
```

The API will be available at http://127.0.0.1:8000.
Interactive API documentation (Swagger UI) can be accessed at http://127.0.0.1:8000/docs.
