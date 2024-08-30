from functools import wraps
import time

def time_execution(func):
    """Decorator to measure and report function execution time."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        elapsed_time = time.time() - start_time
        print(f"{func.__name__} completed in {elapsed_time:.2f} seconds.")
        return result
    return wrapper
