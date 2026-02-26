import asyncio
import inspect


def pytest_pyfunc_call(pyfuncitem):
    test_func = pyfuncitem.obj
    if inspect.iscoroutinefunction(test_func):
        sig = inspect.signature(test_func)
        accepted = {
            name: value
            for name, value in pyfuncitem.funcargs.items()
            if name in sig.parameters
        }
        asyncio.run(test_func(**accepted))
        return True
    return None
