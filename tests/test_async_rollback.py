from unittest import mock
import pytest

from rollback import Rollback

pytestmark = pytest.mark.asyncio

class RollbackError(Exception):
    pass


class RollbackSubclass(Rollback):
    def do_rollback(self):
        super().do_rollback()
        raise RollbackError("test")


class TestRollback:
    def setup_method(self):
        self.mock_step = mock.Mock()

    def teardown_method(self):
        self.mock_step = None

    async def test_Rollback_sets_on_error_attribute(self):
        sentinel = object()
        async with Rollback(on_success=True, on_error=sentinel) as rollback:
            assert rollback.on_error is sentinel

    def test_Rollback_sets_on_success_attribute(self):
        sentinel = object()
        with Rollback(on_error=True, on_success=sentinel) as rollback:
            assert rollback.on_success is sentinel

    def test_Rollback_sets_raise_error_attribute(self):
        sentinel = object()
        with Rollback(raise_error=sentinel) as rollback:
            assert rollback.raise_error is sentinel

    def test_Rollback_do_rollback_calls_in_reverse_order(self):
        idx_max = 3
        expected_calls = reversed([mock.call(idx) for idx in range(idx_max)])
        with Rollback() as rollback:
            for idx in range(idx_max):
                rollback.add_step(self.mock_step, idx)
            rollback.do_rollback()
        self.mock_step.assert_has_calls(expected_calls)

    def test_Rollback_raises_error_by_default(self):
        with pytest.raises(RollbackError):
            with Rollback():
                raise RollbackError("test")
            raise RuntimeError("should not raise this")

    def test_Rollback_does_not_raise_error(self):
        with pytest.raises(RollbackError):
            with Rollback(raise_error=False):
                raise RuntimeError("should not raise this")
            raise RollbackError("test")

    def test_Rollback_does_rollback_on_error(self):
        with Rollback(on_error=True, raise_error=False) as rollback:
            rollback.add_step(self.mock_step)
            raise RollbackError("test")
        self.mock_step.assert_called_once_with()

    def test_Rollback_does_rollback_on_success(self):
        with Rollback(on_success=True) as rollback:
            rollback.add_step(self.mock_step)
        self.mock_step.assert_called_once_with()

    def test_Rollback_does_not_rollback_on_error_by_default(self):
        with Rollback(raise_error=False) as rollback:
            rollback.add_step(self.mock_step)
            raise RuntimeError("should not raise this")
        self.mock_step.has_no_calls()

    def test_Rollback_does_not_rollback_on_success_by_default(self):
        with Rollback() as rollback:
            rollback.add_step(self.mock_step)
        self.mock_step.has_no_calls()

    def test_Rollback_clear_steps_clears_steps(self):
        with Rollback() as rollback:
            rollback.add_step(self.mock_step)
            rollback.clear_steps()
            assert rollback.steps == []

    def test_Rollback_do_rollback_clears_steps(self):
        with Rollback() as rollback:
            rollback.add_step(self.mock_step)
            rollback.do_rollback()
            assert rollback.steps == []

    def test_Rollback_do_rollback_raises_error(self):
        with pytest.raises(RollbackError):
            with Rollback(raise_error=False) as rollback:

                def doError():
                    raise RollbackError("test")

                rollback.add_step(doError)
                rollback.do_rollback()

    def test_Rollback_do_rollback_raises_error(self):
        with pytest.raises(RollbackError):
            with Rollback(raise_error=False) as rollback:

                def doError():
                    raise RollbackError("test")

                rollback.add_step(doError)
                rollback.do_rollback()

    def test_Rollback_do_rollback_raises_error_as_subclass(self):
        with pytest.raises(RollbackError):
            with RollbackSubclass(raise_error=False) as rollback:
                rollback.do_rollback()

    def test_Rollback_as_standalone_instance(self):
        rollback = Rollback()
        rollback.add_step(self.mock_step)
        rollback.do_rollback()
        self.mock_step.assert_called_once_with()
