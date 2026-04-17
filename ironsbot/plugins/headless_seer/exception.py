from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .packets.head import HeadInfo


class ConnectError(Exception): ...


class ClientNotInitializedError(Exception): ...


class NotLoggedInError(Exception): ...


class SocketRecvError(Exception):
    def __init__(
        self,
        head: "HeadInfo",
        message: str = "",
    ) -> None:
        self.head = head
        self.message = message

    def __str__(self) -> str:
        return self.__repr__()

    def __repr__(self) -> str:
        return f"SocketRecvError(head={self.head}, message={self.message or '无'})"
