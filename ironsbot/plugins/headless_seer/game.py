import asyncio
import json
import random
import time
from typing import NamedTuple, overload

import httpx
from nonebot import logger

from .command_id import COMMAND_ID
from .core import SeerConnect, SeerEncryptConnect
from .packets.head import HeadInfo
from .packets.login import SessionPackct
from .packets.team import SimpleTeamInfo
from .type_hint import CommandID, SocketRecvPacketBody, T_Deserializable


class Address(NamedTuple):
    host: str
    port: int


class SeerGame:
    def __init__(
        self,
        user_id: int,
        password: str,
        *,
        login_server_url: str,
        heartbeat_interval: float | None = None,
        reconnect_retries: int = 0,
        reconnect_delay: float = 5.0,
        reconnect_delay_max: float = 120.0,
    ) -> None:
        self.user_id = user_id
        self._password: str = password
        self._impl: SeerEncryptConnect | None = None
        self._is_logged_in = False
        self._lock = asyncio.Lock()
        self._heartbeat_interval = heartbeat_interval
        self._reconnect_retries = reconnect_retries
        self._reconnect_delay = reconnect_delay
        self._reconnect_delay_max = reconnect_delay_max
        self._reconnect_task: asyncio.Task[None] | None = None
        self._login_server_url: str = login_server_url

    @property
    def is_logged_in(self) -> bool:
        return self._impl is not None and self._impl.is_connected and self._is_logged_in

    @property
    def client(self) -> SeerEncryptConnect:
        if self._impl is None:
            raise RuntimeError("客户端尚未初始化，请先登录")
        return self._impl

    @overload
    async def send_and_wait(
        self,
        command_id: CommandID[T_Deserializable],
        *body: object,
        timeout: float = 10.0,
    ) -> tuple[HeadInfo, T_Deserializable]: ...
    @overload
    async def send_and_wait(
        self,
        command_id: CommandID,
        *body: object,
        timeout: float = 10.0,
    ) -> tuple[HeadInfo, SocketRecvPacketBody]: ...
    async def send_and_wait(
        self,
        command_id: CommandID,
        *body: object,
        timeout: float = 10.0,
    ) -> tuple[HeadInfo, SocketRecvPacketBody]:
        """发送封包并等待响应，自动附加 user_id。"""
        return await self.client.send_and_wait(
            command_id, self.user_id, *body, timeout=timeout
        )

    async def _send_heartbeat(self) -> None:
        """心跳回调，由连接层周期性调用。"""
        logger.info(f"{self.user_id}：发送心跳包")
        await self.get_team_info(8847403)

    async def login(self) -> None:
        """完整的登录流程：登录服务器认证 -> 获取服务器列表 -> 连接游戏服务器。"""
        session = await self._fetch_session_token(str(self.user_id), self._password)
        async with self._lock:
            if self._impl is not None:
                self._impl.disconnect()
                self._impl = None

            address = await self._fetch_login_server_addr(self._login_server_url)
            login_client = await SeerConnect.new_client(*address)

            _head, svr_list_info = await login_client.send_and_wait(
                COMMAND_ID.COMMEND_ONLINE,
                self.user_id,
                SessionPackct(session=session),
                timeout=20.0,
            )
            logger.info("登录认证成功")
            if not svr_list_info.svr_list:
                raise RuntimeError("登录失败，服务器列表为空")

            servers = [
                server for server in svr_list_info.svr_list if server.online_id > 0
            ]
            if not servers:
                raise RuntimeError("登录失败，服务器列表为空")

            server = random.choice(servers)
            await login_client.send_and_wait(
                COMMAND_ID.RANGE_ONLINE,
                self.user_id,
                server.online_id,
                server.online_id,
                0,
                timeout=20.0,
            )

            ip = server.ip.strip(b"\x00").decode("utf-8")
            port = server.port

            self._impl = SeerEncryptConnect(
                asyncio.get_running_loop(),
                heartbeat_interval=self._heartbeat_interval,
                on_heartbeat=self._send_heartbeat,
                on_disconnect=self._handle_disconnect,
            )
            await self._impl.connect(ip, port)
            await asyncio.sleep(5)
            _head, res = await self._impl.send_and_wait(
                COMMAND_ID.LOGIN_IN,
                self.user_id,
                self.build_login_packet(session),
            )
            if len(res) == 0:
                raise RuntimeError("登录失败，响应为空")

            # self._impl.key = decrypt.clac_encrypt_key(res, self.user_id)
            self._is_logged_in = True
            logger.info("成功进入游戏服务器")
            login_client.disconnect()

    def logout(self) -> None:
        self._stop_reconnect()
        if self._impl is not None:
            self._impl.disconnect()
        self._is_logged_in = False

    async def _handle_disconnect(self) -> None:
        """连接断开回调，由传输层触发。"""
        self._is_logged_in = False
        logger.warning(f"{self.user_id}：连接已断开")
        if self._reconnect_retries > 0 and self._password and self._login_server_url:
            self._reconnect_task = asyncio.create_task(self._auto_reconnect())

    async def _auto_reconnect(self) -> None:
        """带指数退避的游戏级自动重连，重新执行完整登录流程。"""
        assert self._password is not None and self._login_server_url is not None
        delay = self._reconnect_delay
        for attempt in range(1, self._reconnect_retries + 1):
            logger.info(
                f"{self.user_id}：将在 {delay:.1f}s 后尝试重连 "
                f"({attempt}/{self._reconnect_retries})"
            )
            try:
                await asyncio.sleep(delay)
            except asyncio.CancelledError:
                return
            try:
                await self.login()
                logger.info(f"{self.user_id}：重连成功")
                return
            except asyncio.CancelledError:
                return
            except Exception:
                logger.opt(exception=True).warning(
                    f"{self.user_id}：重连失败 ({attempt}/{self._reconnect_retries})"
                )
            delay = min(delay * 2, self._reconnect_delay_max)
        logger.error(
            f"{self.user_id}：已达最大重试次数 ({self._reconnect_retries})，放弃重连"
        )

    def _stop_reconnect(self) -> None:
        if self._reconnect_task is not None and not self._reconnect_task.done():
            self._reconnect_task.cancel()
        self._reconnect_task = None

    async def get_team_info(self, team_id: int) -> SimpleTeamInfo:
        """获取当前用户的战队信息。"""
        _head, body = await self.send_and_wait(COMMAND_ID.TEAM_GET_INFO, team_id)
        return body

    @staticmethod
    async def _fetch_login_server_addr(url: str) -> Address:
        async with httpx.AsyncClient() as http:
            resp = await http.get(url)
            resp.raise_for_status()
            text = resp.text.strip()
        all_server_addr = text.split("|")
        addr = random.choice(all_server_addr).split(":")
        return Address(addr[0], int(addr[1]))

    @staticmethod
    async def _fetch_session_token(account: str, password: str) -> bytes:
        timestamp = str(int(time.time() * 1000))
        callback = f"jQuery19008830978978300397_{timestamp}"
        params = {
            "r": "userIdentity/authenticate",
            "callback": callback,
            "account": account,
            "rememberAcc": "false",
            "passwd": password,
            "rememberPwd": "true",
            "vericode": "",
            "game": "02",
            "tad": "none",
            "_": timestamp,
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://account-co.61.com/index.php", params=params
            )
            response.raise_for_status()

        payload = SeerGame.parse_jsonp(response.text.strip(), callback)
        if payload.get("result") != 0:
            err_msg = payload.get("err_desc") or payload
            raise ValueError(f"登录失败: {err_msg}")
        data = payload.get("data") or {}
        if not (session := data.get("session")):
            raise ValueError("响应中缺少 session")
        try:
            return bytes.fromhex(session)
        except ValueError as exc:
            raise ValueError("session 格式错误") from exc

    @staticmethod
    def parse_jsonp(response_text: str, expected_callback: str | None = None) -> dict:
        suffix = ");"
        if not response_text.endswith(suffix):
            raise ValueError("回调格式不正确")
        open_paren = response_text.find("(")
        if open_paren == -1:
            raise ValueError("响应缺少括号")
        actual_callback = response_text[:open_paren]
        if expected_callback and not actual_callback.startswith(expected_callback):
            raise ValueError(f"回调名称不匹配: {actual_callback}")
        json_text = response_text[open_paren + 1 : -len(suffix)]
        return json.loads(json_text)

    @staticmethod
    def build_login_packet(session_bytes: bytes) -> bytes:
        return session_bytes + bytearray.fromhex(
            "74616F6D65650000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000B38000000015043000000000000000000000000000000002710000000010000000100000002756E6974795F6170705F74616F6D656500000000000000000000000000000000636F6D2E74616F6D65652E736565722E6D6F62696C65000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000004E6974726F414E3531352D35352841636572290000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
        )
