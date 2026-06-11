"""
PR Reviewer - 重试装饰器
🎯 让 HTTP 调用更稳定
"""
import time
import functools
from typing import Callable
import requests


# 哪些异常可以重试（瞬时性错误）
RETRYABLE_EXCEPTIONS = (
    requests.exceptions.Timeout,       # 超时
    requests.exceptions.ConnectionError,  # 连接失败
)

# 哪些 HTTP 状态码可以重试
RETRYABLE_STATUS_CODES = {
    500,  # 服务器内部错误
    502,  # Bad Gateway
    503,  # Service Unavailable
    504,  # Gateway Timeout
}


def retry_on_failure(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    on_retry: Callable = None,
):
    """
    重试装饰器（指数退避）
    
    参数：
        max_attempts: 最大尝试次数（包括第一次）
        initial_delay: 首次重试等待秒数
        backoff_factor: 退避倍数（每次等待时间 × 这个）
        on_retry: 重试前的回调（用于打日志/通知前端）
    
    使用示例：
        @retry_on_failure(max_attempts=3)
        def call_api():
            return requests.get(...)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    result = func(*args, **kwargs)
                    
                    # 🔑 检查 requests.Response 的状态码
                    if isinstance(result, requests.Response):
                        if result.status_code in RETRYABLE_STATUS_CODES:
                            raise requests.HTTPError(
                                f"HTTP {result.status_code}",
                                response=result,
                            )
                    
                    return result
                
                except RETRYABLE_EXCEPTIONS as e:
                    last_exception = e
                    if attempt >= max_attempts:
                        break
                    
                    if on_retry:
                        on_retry(attempt, max_attempts, delay, e)
                    
                    time.sleep(delay)
                    delay *= backoff_factor
                
                except requests.HTTPError as e:
                    if (
                        e.response is not None
                        and e.response.status_code in RETRYABLE_STATUS_CODES
                        and attempt < max_attempts
                    ):
                        last_exception = e
                        if on_retry:
                            on_retry(attempt, max_attempts, delay, e)
                        time.sleep(delay)
                        delay *= backoff_factor
                    else:
                        raise  # 4xx 错误直接抛
                
                # 其他异常不重试
                except Exception:
                    raise
            
            # 重试完了还失败
            raise last_exception
        
        return wrapper
    return decorator


# ===== 测试 =====
if __name__ == "__main__":
    # 模拟一个"前 2 次会失败，第 3 次成功"的场景
    call_count = 0
    
    def my_callback(attempt, max_attempts, delay, error):
        print(f"  🔄 第 {attempt}/{max_attempts} 次失败，{delay:.1f}s 后重试... 错误: {type(error).__name__}")
    
    @retry_on_failure(max_attempts=3, initial_delay=0.5, on_retry=my_callback)
    def flaky_function():
        global call_count
        call_count += 1
        print(f"  📞 第 {call_count} 次调用...")
        if call_count < 3:
            raise requests.exceptions.ConnectionError("假装连不上")
        return "✅ 成功！"
    
    print("测试 1：前 2 次失败，第 3 次成功")
    result = flaky_function()
    print(f"  结果：{result}\n")
    
    # 测试不可重试的错误
    print("测试 2：不可重试的错误（应该立刻抛出）")
    
    @retry_on_failure(max_attempts=3)
    def bad_request():
        raise ValueError("这种错不该重试")
    
    try:
        bad_request()
    except ValueError as e:
        print(f"  ✅ 正确抛出了 ValueError: {e}")