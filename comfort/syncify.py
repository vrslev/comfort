# From https://gist.github.com/mikeckennedy/033ad92c165a9041fafc5c429e6c3c28

import asyncio
import threading
import time
import uuid
from typing import Any, Awaitable, NoReturn, TypeVar

import uvloop

uvloop.install()

_add_lock = threading.Lock()
_receive_lock = threading.Lock()

_pending_items: dict[uuid.UUID, Awaitable[Any]] = {}
_finished_items: dict[uuid.UUID, Any] = {}

T = TypeVar("T")


def _add_work(aw: Awaitable[Any]) -> uuid.UUID:
    id = uuid.uuid4()

    with _add_lock:
        _pending_items[id] = aw

    return id


def _is_done(item_id: uuid.UUID) -> bool:
    with _receive_lock:
        return item_id in _finished_items


def _get_result(id: uuid.UUID) -> Any:
    with _receive_lock:
        result = _finished_items[id]
        del _finished_items[id]

    return result


def run(aw: Awaitable[T]) -> T:
    id = _add_work(aw)
    while not _is_done(id):
        time.sleep(0.0005)
        continue

    result = _get_result(id)
    if isinstance(result, Exception):
        raise result

    return result


def run_worker() -> NoReturn:
    loop = uvloop.new_event_loop()

    while True:
        with _add_lock:
            count = len(_pending_items)

        if count == 0:
            time.sleep(0.001)
            continue

        with _add_lock:
            work = list(_pending_items.items())
            for id, _ in work:
                del _pending_items[id]

        running = {k: loop.create_task(w) for k, w in work}

        for id, task in running.items():
            try:
                loop.run_until_complete(asyncio.wait((task,)))
                result = task.result()

                with _receive_lock:
                    _finished_items[id] = result
            except Exception as x:
                with _receive_lock:
                    _finished_items[id] = x


_thread = threading.Thread(target=run_worker, daemon=True)
_thread.start()
