import asyncio
import inspect
from typing import Callable, Any, List, Tuple


class Rollback:
    """
    Provides rollback methods and context manager.
    """

    def __init__(self, on_error: bool = False, on_success: bool = False, raise_error: bool = True):
        """
        Initializes the Rollback instance.

        :param on_error: Call `do_rollback` if an exception is raised.
        :param on_success: Call `do_rollback` if no exception is raised.
        :param raise_error: Re-raise exceptions if they are raised during the context manager block.
        """
        self.steps: List[Tuple[Callable[..., Any], Tuple[Any, ...], dict]] = []
        self.on_error = on_error
        self.on_success = on_success
        self.raise_error = raise_error

    def __enter__(self) -> 'Rollback':
        """
        Enters the context manager block.

        :return: The current Rollback instance.
        """
        return self

    async def __aenter__(self) -> 'Rollback':
        """
        Enters the async context manager block.

        :return: The current Rollback instance.
        """
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        """
        Exits the context manager block.

        :param exception_type: Type of the raised exception.
        :param exception_value: Value of the raised exception.
        :param traceback: Traceback of the raised exception.
        :return: Whether to suppress the raised exception.
        """
        return self._handle_exit(exception_type, exception_value, traceback)

    async def __aexit__(self, exception_type, exception_value, traceback):
        """
        Exits the async context manager block.

        :param exception_type: Type of the raised exception.
        :param exception_value: Value of the raised exception.
        :param traceback: Traceback of the raised exception.
        :return: Whether to suppress the raised exception.
        """
        return await self._handle_exit(exception_type, exception_value, traceback)

    def _handle_exit(self, exception_type, exception_value, traceback):
        """
        Handles the exit process for the context manager.

        :param exception_type: Type of the raised exception.
        :param exception_value: Value of the raised exception.
        :param traceback: Traceback of the raised exception.
        :return: Whether to suppress the raised exception.
        """
        error = bool(traceback is not None)
        suppress_error = not self.raise_error
        if (error and self.on_error) or (self.on_success and not error):
            if asyncio.get_event_loop().is_running():
                asyncio.create_task(self.do_rollback())
            else:
                asyncio.run(self.do_rollback())
        if error and suppress_error:
            suppress_error = not self._method_in_traceback("do_rollback", traceback)
        return suppress_error

    @staticmethod
    def _frames(traceback):
        """
        Returns a generator that iterates over frames in a traceback.

        :param traceback: The traceback object.
        :return: Generator for frames in the traceback.
        """
        frame = traceback
        while frame.tb_next:
            frame = frame.tb_next
            yield frame.tb_frame

    def _method_in_traceback(self, name: str, traceback) -> bool:
        """
        Checks if a method from this instance is present in the traceback.

        :param name: The name of the method to check.
        :param traceback: The traceback object.
        :return: True if the method is found, otherwise False.
        """
        found_method = False
        for frame in self._frames(traceback):
            this = frame.f_locals.get("self")
            if this is self and frame.f_code.co_name == name:
                found_method = True
                break
        return found_method

    def add_step(self, callback: Callable[..., Any], *args: Any, **kwargs: Any):
        """
        Adds a rollback step with optional arguments.

        :param callback: The callback function for the rollback step.
        :param args: Positional arguments for the callback.
        :param kwargs: Keyword arguments for the callback.
        """
        self.steps.append((callback, args, kwargs))

    def clear_steps(self):
        """
        Clears all rollback steps.
        """
        self.steps.clear()

    async def do_rollback(self):
        """
        Calls each rollback step in LIFO order asynchronously if the step is a coroutine.
        """
        while self.steps:
            callback, args, kwargs = self.steps.pop()
            if asyncio.iscoroutinefunction(callback):
                await callback(*args, **kwargs)
            else:
                callback(*args, **kwargs)
