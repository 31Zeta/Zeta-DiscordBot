from typing import *
import aiohttp
import asyncio
import base64
import json
import os
import re
from io import BytesIO
from pathlib import Path
from enum import Enum
import qrcode
from PIL import Image

import errors
import utils
from utils import Result, success_result, failed_result

from zeta_bot import (
    output_console,
    audio,
)
from zeta_bot.resource import MediaPlatform, LinkType, DownloadHandler, DownloadType, ResourceClassifier

# 设置控制台
console = output_console.Console()

# 加载资源分类器
resource_classifier = ResourceClassifier()

level = "Go-Music-API模块"

CHUNK_SIZE = 256 * 1024
GO_MUSIC_SUPPORTED_PLATFORM = {"bilibili", "netease", "qq", "kugou", "kuwo", "migu", "qianqian", "soda", "fivesing", "jamendo", "joox"}
GO_MUSIC_INFO_TYPE = {"song", "playlist", "album"}
GO_MUSIC_DOWNLOAD_TYPE = {f"{i}_{j}" for i in GO_MUSIC_SUPPORTED_PLATFORM for j in GO_MUSIC_INFO_TYPE}
SOURCE_MAP = {
    "bilibili": "哔哩哔哩",
    "netease": "网易云音乐",
    "qq": "QQ音乐",
    "kugou": "酷狗音乐",
    "kuwo": "酷我音乐",
    "migu": "咪咕音乐",
    "qianqian": "千千音乐",
    "soda": "汽水音乐",
    "fivesing": "5sing",
    "jamendo": "Jamendo",
    "joox": "JOOX"
}
PLATFORM_SOURCE_MAP: Dict[MediaPlatform, str] = {
    MediaPlatform.BILIBILI: "bilibili",
    MediaPlatform.QQ: "qq",
    MediaPlatform.NETEASE: "netease",
    MediaPlatform.KUGOU: "kugou",
    MediaPlatform.KUWO: "kuwo",
    MediaPlatform.MIGU: "migu",
    MediaPlatform.QIANQIAN: "qianqian",
    MediaPlatform.SODA: "soda",
    MediaPlatform.FIVESING: "fivesing",
    MediaPlatform.JAMENDO: "jamendo",
    MediaPlatform.JOOX: "joox"
}


# 初始化各平台Cookie文件，已有文件不覆盖
try:
    cookie_directory = Path(__file__).resolve().parent.parent / "data" / "cookies"
    cookie_directory.mkdir(parents=True, exist_ok=True)
    for cookie_source in GO_MUSIC_SUPPORTED_PLATFORM:
        try:
            with (cookie_directory / f"{cookie_source}.json").open("x", encoding="utf-8") as cookie_file:
                cookie_file.write("{}")
        except OSError:
            continue
except OSError:
    pass


def api_url_format(api_url: str) -> str:
    return str(api_url).strip().rstrip("/")


async def handle_exception(exception: Exception) -> Result:
    message = "音乐服务发生错误"
    if isinstance(exception, RuntimeError):
        await console.rp(
            f"触发异常{type(exception).__module__}.{type(exception).__name__}：{exception}",
            f"[{level}]",
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        retryable = False
    elif isinstance(exception, errors.NoSearchResultsError):
        await console.rp(
            f"获取失败，音乐链接解析结果缺少songs列表",
            f"[{level}]",
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        retryable = False
        message = "搜索结果为空"
    elif isinstance(exception, errors.ResourceRestrictedError):
        await console.rp(
            f"获取失败，资源可能存在会员或者区域版权限制：{exception}",
            f"[{level}]",
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        retryable = False
        message = "资源可能存在会员或者区域版权限制"
    # 不支持链接的情况
    elif isinstance(exception, errors.URLNotSupportedError):
        await console.rp(
            f"触发异常URLNotSupportedError：{exception}",
            f"[{level}]",
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        retryable = False
        message = str(exception)  # 将API报错信息发至上层message打印到Discord中
    # 网络连接、响应中断和超时
    elif isinstance(exception, (aiohttp.ClientConnectionError, aiohttp.ClientPayloadError, asyncio.TimeoutError)):
        await console.rp(
            f"触发异常{type(exception).__module__}.{type(exception).__name__}：{exception}，无法连接go-music-api或请求超时",
            f"[{level}]",
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        retryable = True

    # 无效服务地址
    elif isinstance(exception, aiohttp.InvalidURL):
        await console.rp(
            f"触发异常{type(exception).__module__}.{type(exception).__name__}：{exception}，go-music-api服务地址无效",
            f"[{level}]",
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        retryable = False

    elif isinstance(exception, (aiohttp.ClientError, aiohttp.ClientResponseError)):
        await console.rp(
            f"触发异常{type(exception).__module__}.{type(exception).__name__}：{exception}，go-music-api网络请求失败",
            f"[{level}]",
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        retryable = True

    elif isinstance(exception, json.JSONDecodeError):
        await console.rp(
            f"触发异常{type(exception).__module__}.{type(exception).__name__}：{exception}，返回的JSON格式无效",
            f"[{level}]",
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        retryable = False

    elif isinstance(exception, OSError):
        await console.rp(
            f"触发异常{type(exception).__module__}.{type(exception).__name__}：{exception}，本地音频文件处理失败",
            f"[{level}]",
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        retryable = False

    elif isinstance(exception, (ValueError, TypeError, KeyError)):
        await console.rp(
            f"触发异常{type(exception).__module__}.{type(exception).__name__}：{exception}，参数或响应数据无效",
            f"[{level}]",
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        retryable = False

    else:
        await console.rp(
            f"触发异常{type(exception).__module__}.{type(exception).__name__}：{exception}",
            f"[{level}]",
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        retryable = False

    return failed_result(exception=exception, message=message, retryable=retryable)


def extract_cookie(cookie_data: Any, source: str) -> str:
    """
    将扫码登录或浏览器插件导出的JSON内容转换为Cookie请求头字符串。

    支持平台映射、Cookie字符串、name/value数组、Cookie键值映射，
    以及包含cookie、cookies或登录响应data的包装对象。
    浏览器导出内容应属于指定平台；仅提取名称和值，不验证登录是否有效。
    """
    source = source.strip().lower()
    if source == "qq_wx":
        source = "qq"

    def cookie_pair(name: Any, value: Any) -> str:
        # 拒绝非法字段，异常信息不包含凭据内容。
        if not isinstance(name, str) or not re.fullmatch(r"[!#$%&'*+\-.^_`|~0-9A-Za-z]+", name):
            raise RuntimeError("本地Cookie包含无效名称")
        if not isinstance(value, str) or any(char in value for char in ("\r", "\n", ";", "\x00")):
            raise RuntimeError("本地Cookie包含无效值，值必须为字符串且不能包含换行或分号")
        return f"{name}={value}"

    def extract(data: Any, depth: int = 0) -> str:
        if depth > 8:
            raise RuntimeError("本地Cookie的JSON嵌套层级过多")
        if data is None:
            return ""
        if isinstance(data, str):
            data = data.strip()
            if data.lower().startswith("cookie:"):
                data = data[7:].strip()
            pairs = []
            for part in data.split(";"):
                if not part.strip():
                    continue
                name, separator, value = part.strip().partition("=")
                if not separator:
                    raise RuntimeError("本地Cookie字符串必须为name=value格式")
                pairs.append(cookie_pair(name.strip(), value))
            return "; ".join(pairs)
        if isinstance(data, list):
            pairs = []
            for item in data:
                if not isinstance(item, dict) or "name" not in item or "value" not in item:
                    raise RuntimeError("浏览器Cookie数组的每项必须包含name和value")
                # domain、path、expirationDate等字段属于浏览器元数据，不发送给API。
                pairs.append(cookie_pair(item["name"], item["value"]))
            return "; ".join(pairs)
        if not isinstance(data, dict):
            raise RuntimeError("本地Cookie必须为字符串、对象或name/value数组")
        if not data:
            return ""
        if source in data:
            return extract(data[source], depth + 1)
        if source == "qq" and "qq_wx" in data:
            return extract(data["qq_wx"], depth + 1)

        # 平台映射内没有当前平台时，不使用其他平台的凭据。
        if any(platform in data for platform in GO_MUSIC_SUPPORTED_PLATFORM | {"qq_wx"}):
            return ""
        declared_source = data.get("source", data.get("platform"))
        if declared_source is not None:
            if not isinstance(declared_source, str):
                raise RuntimeError("本地Cookie的平台标识必须为字符串")
            declared_source = declared_source.strip().lower()
            if declared_source == "qq_wx":
                declared_source = "qq"
            if declared_source != source:
                return ""
        if "name" in data and "value" in data:
            return cookie_pair(data["name"], data["value"])
        for key in ("cookie", "cookies", "data"):
            if key in data:
                cookie = extract(data[key], depth + 1)
                if cookie:
                    return cookie
        # 已识别的包装对象不再作为Cookie键值映射，避免发送登录状态等元数据。
        if any(key in data for key in ("cookie", "cookies", "data", "source", "platform", "status", "code", "msg", "message")):
            return ""
        return "; ".join(cookie_pair(name, value) for name, value in data.items())

    return extract(cookie_data)


async def use_local_cookie(api_url: str, session: aiohttp.ClientSession, source: Optional[str]) -> bool:
    """
    请求前读取本地平台Cookie，并同步到go-music-api的全局配置。

    :param api_url: go-music-api服务根地址
    :param session: aiohttp客户端会话
    :param source: 单个平台，None时不读取文件、不同步Cookie
    :return: 是否成功同步了本地Cookie；文件不存在、不可读或内容无效时返回False

    读取data/cookies/<平台>.json，自动提取扫码登录或浏览器插件导出的Cookie。
    API不支持通过单次音乐请求传入平台Cookie，因此先调用配置接口热更新并持久化。
    本地Cookie不可用时跳过同步并继续请求，不清除API已有的Cookie。
    Cookie同步接口失败时仍向上抛出异常。
    """
    if source is None:
        return False
    if not isinstance(source, str):
        raise TypeError("Cookie平台source必须为字符串或None")
    source = source.strip().lower()
    if source == "qq_wx":
        source = "qq"
    # 只检查已知的单个平台，避免将未知来源或路径当作本地文件名。
    if source not in GO_MUSIC_SUPPORTED_PLATFORM:
        return False

    cookie_path = Path(__file__).resolve().parent.parent / "data" / "cookies" / f"{source}.json"
    try:
        cookie_text = await asyncio.to_thread(cookie_path.read_text, encoding="utf-8-sig")
        cookie_data = json.loads(cookie_text)
        cookie = extract_cookie(cookie_data, source)
    except (OSError, UnicodeError, ValueError, RuntimeError, RecursionError):
        # 空文件、损坏的JSON、编码错误及无效Cookie均按未配置处理。
        return False
    if not cookie:
        return False

    # 只更新当前平台，不将凭据放入URL或输出包含凭据的响应正文。
    request_url = f"{api_url_format(api_url)}/api/v1/system/cookies"
    async with session.post(request_url, json={source: cookie}, allow_redirects=False) as response:
        if response.status != 200:
            raise RuntimeError(f"本地Cookie同步失败，HTTP状态码：{response.status}")
        try:
            result = json.loads(await response.text())
        except (ValueError, UnicodeError):
            raise RuntimeError("Cookie同步接口未返回有效JSON") from None
        if not isinstance(result, dict) or result.get("status") != "ok":
            raise RuntimeError("Cookie同步接口未确认更新成功")
    return True


async def request_json(api_url: str, session: aiohttp.ClientSession, endpoint: str, params: Optional[dict] = None, source: Optional[str] = None) -> dict:
    """
    请求go-music-api并解析JSON对象

    :param api_url: go-music-api 服务根地址
    :param session: aiohttp 客户端会话
    :param endpoint: API 路径
    :param params: 查询参数
    :param source: 请求前尝试同步本地Cookie的平台，None时跳过
    :return: API 返回的 JSON 对象
    """
    request_url = f"{api_url_format(api_url)}{endpoint}"

    await use_local_cookie(api_url, session, source)
    async with session.get(request_url, params=params) as response:
        body = await response.text(errors="replace")

        try:
            result = json.loads(body)
        except json.JSONDecodeError as exception:
            raise RuntimeError(f"状态码：{response.status}，返回的JSON格式无效：{body}") from exception

        # 错误状态码的情况
        if response.status >= 400:
            error_message = str(result.get("msg", result.get("error", body)))
            # 资源受限，go-music-api返回404 Failed to get URL
            if response.status == 404:
                raise errors.ResourceRestrictedError(f"疑似资源受限，状态码：{response.status}，{error_message}")
            # 处理不支持的链接的情况，需要将API报错信息发至上层message打印到Discord中
            elif "不支持" in error_message:
                raise errors.URLNotSupportedError(error_message)
            else:
                raise RuntimeError(f"状态码：{response.status}，{error_message}")

    return result


def build_music_params(info_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    构造大小探测和下载接口需要的歌曲参数，网易云默认使用极高品质。

    显式指定的网易云音质优先；指定音质失败后的旧接口回退由后端负责。

    :param info_dict: 标准化后的歌曲信息字典
    :return: 音频流接口查询参数
    """
    extra = info_dict.get("extra") or {}

    # 字符串形式的extra必须可以被解析为JSON
    if isinstance(extra, str):
        try:
            json.loads(extra)
        except json.JSONDecodeError as exception:
            raise RuntimeError("歌曲extra字段不是有效的JSON") from exception
        extra_json = extra

    # 字典等结构统一序列化为 JSON 字符串
    else:
        try:
            extra_json = json.dumps(extra, ensure_ascii=False)
        except (TypeError, ValueError) as exception:
            raise RuntimeError("歌曲extra字段无法转换为JSON") from exception

    if info_dict.get("source") == "netease":
        # 解析为独立字典，避免修改调用方持有的歌曲信息
        netease_extra = json.loads(extra_json)
        if netease_extra is None:
            netease_extra = {}
        if not isinstance(netease_extra, dict):
            raise RuntimeError("网易云歌曲extra字段必须是JSON对象")

        # 未指定音质时默认请求极高品质，后端仍会在失败时尝试旧版下载接口
        if not str(netease_extra.get("netease_level") or "").strip() and not str(netease_extra.get("level") or "").strip():
            netease_extra["netease_level"] = "exhigh"
        extra_json = json.dumps(netease_extra, ensure_ascii=False)

    return {
        "id": info_dict["id"],
        "name": info_dict["name"] or "未知音频",
        "artist": info_dict["artist"] or "未知作者",
        "album": info_dict.get("album", ""),
        "duration": info_dict.get("duration", 0),
        "source": info_dict.get("source") or "未知来源",
        "cover": info_dict.get("cover") or "",
        "extra": extra_json,
    }


async def is_available(api_url: str, silent: bool = True) -> bool:
    """
    检测go-music-api服务是否正常响应

    :param api_url: go-music-api 服务根地址
    :param silent: 是否取消打印测试信息
    :return: 服务是否可用
    """
    timeout = aiohttp.ClientTimeout(total=3)

    # 请求不依赖外部音乐平台的轻量接口
    try:
        if not silent: await console.rp(
            f"测试go-music-api连接：{api_url}",
            f"[{level}]",
        )
        async with aiohttp.ClientSession(timeout=timeout) as session:
            result = await request_json(api_url, session, "/api/v1/system/qr_login/sources",)
    except Exception as e:
        if not silent: await console.rp(
            f"go-music-api服务连接失败：触发异常{type(e).__module__}.{type(e).__name__}",
            f"[{level}]",
            message_type=utils.PrintType.WARNING,
            print_head=True
        )
        return False
    else:
        if not silent: await console.rp(
            f"go-music-api服务连接成功",
            f"[{level}]",
            print_head=True
        )
        return True


async def qr_login(source: str, api_url: str, raise_exception: bool = False) -> Result:
    """
    创建平台扫码登录二维码，异步等待确认并保存Cookie。

    :param source: 扫码平台，支持netease、qq、qq_wx、kugou和bilibili
    :param api_url: go-music-api服务根地址
    :param raise_exception: 是否不调用handle_exception直接raise
    :return: 统一Result，成功结果包含source、cookie_source、qr_path、cookie_path和api_cookie_saved

    二维码保存在项目根目录<source>_qr_<时间>.png，生成后输出路径供用户扫码。
    登录结束后无论成功、失败或取消，都会删除本次二维码；返回的qr_path仅记录原路径。
    最多等待300秒，平台返回更早的过期时间时以平台时间为准。
    Cookie以平台键值对保存到data/cookies/<平台>.json，目录不存在时自动创建。
    qq_wx使用qq作为Cookie平台名；同平台再次登录会覆盖原文件。
    API成功轮询时会更新其自身Cookie；后续指定平台的业务请求会从本地文件重新同步。
    本地文件不会改变API自身的Cookie存储路径。
    """
    def save_qr_image(image_data: Optional[bytes], login_url: str, path: Path) -> None:
        """在工作线程中生成或转换二维码，并以PNG格式完整写入。"""
        part_path = path.with_suffix(".png.part")
        try:
            if image_data is not None:
                with Image.open(BytesIO(image_data)) as image:
                    image.save(part_path, format="PNG")
            else:
                image = qrcode.make(login_url)
                image.save(part_path, format="PNG")
            part_path.replace(path)
        finally:
            part_path.unlink(missing_ok=True)

    def save_cookie(cookie_source: str, cookie: str, path: Path, time_stamp: str) -> None:
        """在工作线程中创建目录，并原子替换对应平台的Cookie文件。"""
        path.parent.mkdir(parents=True, exist_ok=True)
        part_path = path.with_name(f"{path.name}.{time_stamp}.part")
        try:
            utils.json_save(str(part_path), {cookie_source: cookie})
            part_path.replace(path)
        finally:
            part_path.unlink(missing_ok=True)

    qr_path: Optional[Path] = None
    qr_image_task: Optional[asyncio.Task] = None
    try:
        if not isinstance(source, str):
            raise TypeError("扫码登录平台source必须为字符串")
        source = source.strip().lower()
        if source not in {"netease", "qq", "qq_wx", "kugou", "bilibili"}:
            raise ValueError("不支持此扫码登录平台，可选netease、qq、qq_wx、kugou、bilibili")

        project_root = Path(__file__).resolve().parent.parent
        timestamp = utils.ctime_str().replace(":", "_")
        qr_path = project_root / f"{source}_qr_{timestamp}.png"
        cookie_source = "qq" if source == "qq_wx" else source
        cookie_path = project_root / "data" / "cookies" / f"{cookie_source}.json"
        request_url = f"{api_url_format(api_url)}/api/v1/system/qr_login/{source}"
        timeout = aiohttp.ClientTimeout(total=60, connect=10)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async def request_login(method: str, params: Optional[dict] = None) -> dict:
                """请求扫码接口，避免将包含凭据的响应正文或登录key写入异常日志。"""
                async with session.request(method, request_url, params=params) as response:
                    if response.status != 200:
                        raise RuntimeError(f"扫码登录接口请求失败，HTTP状态码：{response.status}")
                    try:
                        result = json.loads(await response.text())
                    except (ValueError, UnicodeError):
                        raise RuntimeError("扫码登录接口未返回有效JSON") from None
                    if not isinstance(result, dict) or result.get("code") != 200:
                        raise RuntimeError("扫码登录接口返回失败状态")
                    data = result.get("data")
                    if not isinstance(data, dict):
                        raise RuntimeError("扫码登录结果缺少data对象")
                    return result

            login_response = await request_login("POST")
            login_session = login_response["data"]
            key = login_session.get("key")
            if not isinstance(key, str) or not key.strip():
                raise RuntimeError("扫码登录会话缺少key")

            # 同时限制本地等待时间和平台会话有效期。
            wait_seconds = 300.0
            expires_at = login_session.get("expires_at")
            if expires_at:
                wait_seconds = min(wait_seconds, float(expires_at) - utils.ctime_datetime().timestamp())
            if wait_seconds <= 0:
                return Result(success=False, result=login_response, exception=None, message="二维码已过期，请重新登录", retryable=False)
            deadline = asyncio.get_running_loop().time() + wait_seconds

            # 优先使用上游二维码图片，只有登录链接时才在本地生成二维码。
            image_data = None
            image_url = login_session.get("image_url") or ""
            login_url = login_session.get("url") or ""
            if not isinstance(image_url, str) or not isinstance(login_url, str):
                raise RuntimeError("二维码图片地址或登录链接格式无效")
            if image_url.startswith("data:image/"):
                header, separator, encoded_image = image_url.partition(",")
                if not separator or not header.endswith(";base64"):
                    raise RuntimeError("二维码图片不是有效的Base64数据")
                image_data = base64.b64decode(encoded_image, validate=True)
            elif image_url:
                async with session.get(image_url) as response:
                    if response.status != 200:
                        raise RuntimeError(f"二维码图片下载失败，HTTP状态码：{response.status}")
                    image_data = await response.read()
            elif not login_url.strip():
                raise RuntimeError("扫码登录会话缺少二维码图片或登录链接")

            # 避免任务取消后工作线程仍在写入，导致清理完成后重新出现图片。
            qr_image_task = asyncio.create_task(asyncio.to_thread(save_qr_image, image_data, login_url, qr_path))
            await asyncio.shield(qr_image_task)
            await console.rp(f"{SOURCE_MAP[source]}扫码登录二维码已保存，请打开图片扫码并确认：{qr_path}", f"[{level}]")

            # 持续轮询到登录成功、失败或过期，取消任务时正常向上传播取消异常。
            poll_timeout = asyncio.timeout_at(deadline)
            try:
                async with poll_timeout:
                    last_status = None
                    while True:
                        login_response = await request_login("GET", params={"key": key})
                        login_result = login_response["data"]
                        status = login_result.get("status")
                        if status == "success":
                            break
                        if status == "expired":
                            return Result(success=False, result=login_response, exception=None, message="二维码已过期，请重新登录", retryable=False)
                        if status == "failed":
                            return Result(success=False, result=login_response, exception=None, message="平台扫码登录失败，请重新登录", retryable=False)
                        if status not in ("waiting", "scanned"):
                            raise RuntimeError("平台返回未知扫码登录状态")
                        if status == "scanned" and last_status != status:
                            await console.rp(f"已扫码，请在手机上确认登录", f"[{level}]")
                        last_status = status
                        await asyncio.sleep(2)
            except asyncio.TimeoutError:
                if poll_timeout.expired():
                    return Result(success=False, result=login_response, exception=None, message="扫码登录超时或二维码已过期，请重新登录", retryable=False)
                raise

            cookie = login_result.get("cookie") or ""
            if not isinstance(cookie, str):
                raise RuntimeError("登录成功，但Cookie格式无效")
            cookie = cookie.strip()
            if not cookie:
                cookies = login_result.get("cookies")
                if isinstance(cookies, dict) and all(isinstance(k, str) and isinstance(v, str) for k, v in cookies.items()):
                    cookie = "; ".join(f"{k}={v.strip()}" for k, v in sorted(cookies.items()) if k.strip() and v.strip())
            if not cookie:
                raise RuntimeError("登录成功，但未获得有效Cookie")

            await asyncio.to_thread(save_cookie, cookie_source, cookie, cookie_path, timestamp)
            extra = login_result.get("extra")
            api_cookie_saved = isinstance(extra, dict) and extra.get("cookie_saved") in ("true", True)
            await console.rp(f"[{source}] 扫码登录成功，Cookie已保存：{cookie_path}", f"[{level}]")
            if not api_cookie_saved:
                await console.rp("API未确认其自身Cookie写盘成功；本地文件已保存，后续指定平台的请求会尝试重新同步", f"[{level}]", message_type=utils.PrintType.WARNING)

    except aiohttp.ClientError:
        # aiohttp异常可能包含带登录key的请求URL，交给公共处理器前替换为不含凭据的异常。
        exception = aiohttp.ClientConnectionError("扫码登录网络请求失败，请检查API地址和网络连接")
        if not raise_exception:
            return await handle_exception(exception)
        else:
            raise exception
    except Exception as exception:
        if not raise_exception:
            return await handle_exception(exception)
        else:
            raise exception
    finally:
        if qr_image_task is not None and qr_path is not None:
            # 先等待图片写入结束，再清理当前会话的二维码。
            try:
                await asyncio.shield(qr_image_task)
            except Exception:
                pass
            try:
                await asyncio.to_thread(qr_path.unlink, missing_ok=True)
            except OSError as exception:
                await console.rp(f"二维码图片删除失败：{qr_path}，{exception}", f"[{level}]", message_type=utils.PrintType.WARNING)

    return success_result(
        result={
            "source": source,
            "cookie_source": cookie_source,
            "qr_path": str(qr_path),
            "cookie_path": str(cookie_path),
            "api_cookie_saved": api_cookie_saved,
        },
        message="扫码登录成功，Cookie已保存"
    )


async def get_info_album(api_url: str, music_url: str, sources: Optional[str] = None, suppress_errors: bool = False) -> Optional[Result]:
    """
    通过音乐链接获取专辑信息

    :param api_url: go-music-api 服务根地址
    :param music_url: 音乐平台的单曲分享链接
    :param sources: 目标平台，非None时请求前尝试同步本地对应平台的Cookie
    :param suppress_errors: 出现错误时是否阻止异常抛出
    :return: 包含歌曲信息或异常的统一结果字典
    """
    try:
        music_url = str(music_url).strip()

        # 请求链接解析接口
        timeout = aiohttp.ClientTimeout(total=20, connect=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            params = {
                "q": music_url,
                "type": "album",
            }
            if sources is not None:
                params["sources"] = sources

            result = await request_json(
                api_url_format(api_url),
                session,
                "/api/v1/music/search",
                params,
                source=sources,
            )

        info_dict = result.get("data")
        if not isinstance(info_dict, dict):
            if suppress_errors: return None
            raise RuntimeError("音乐链接解析结果缺少data对象")

        albums = info_dict.get("albums")
        if not isinstance(albums, list):
            if suppress_errors: return None
            raise RuntimeError("音乐链接解析结果缺少albums列表")
        if "id" not in albums[0]:
            if suppress_errors: return None
            raise RuntimeError("音乐链接中没有解析到专辑")

        album_id = albums[0]["id"]
        album_source = albums[0].get("source")
        album_name = albums[0].get("name")

        await console.rp(f"信息提取完毕：{album_source}专辑：[{album_id}] {album_name}", f"[{level}]")

    except Exception as e:
        return await handle_exception(e)

    result = success_result(result=info_dict)
    result.get_extra()["type"] = "album"
    return result


async def get_info_playlist(api_url: str, music_url: str, sources: Optional[str] = None, suppress_errors: bool = False) -> Optional[Result]:
    """
    通过音乐链接获取歌单信息

    :param api_url: go-music-api 服务根地址
    :param music_url: 音乐平台的单曲分享链接
    :param sources: 目标平台，非None时请求前尝试同步本地对应平台的Cookie
    :param suppress_errors: 出现错误时是否阻止异常抛出
    :return: 包含歌曲信息或异常的统一结果字典
    """
    try:
        music_url = str(music_url).strip()

        # 请求链接解析接口
        timeout = aiohttp.ClientTimeout(total=20, connect=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            params = {
                "q": music_url,
                "type": "playlist",
            }
            if sources is not None:
                params["sources"] = sources

            result = await request_json(
                api_url_format(api_url),
                session,
                "/api/v1/music/search",
                params,
                source=sources,
            )

        info_dict = result.get("data")
        if not isinstance(info_dict, dict):
            if suppress_errors: return None
            raise RuntimeError("音乐链接解析结果缺少data对象")

        playlists = info_dict.get("playlists")
        if not isinstance(playlists, list):
            if suppress_errors: return None
            raise RuntimeError("音乐链接解析结果缺少playlists列表")
        if len(playlists) <= 0:
            if suppress_errors: return None
            raise RuntimeError("音乐链接中没有解析到歌单")

        playlist_id = playlists[0]["id"]
        playlist_source = playlists[0].get("source")
        playlist_name = playlists[0].get("name")

        await console.rp(f"信息提取完毕：{playlist_source}歌单：[{playlist_id}] {playlist_name}", f"[{level}]")

    except Exception as e:
        return await handle_exception(e)

    result = success_result(result=info_dict)
    result.get_extra()["type"] = "playlist"
    return result


async def get_info(api_url: str, music_url: str, sources: Optional[str] = None) -> Result:
    """
    通过音乐链接获取歌曲信息

    :param api_url: go-music-api 服务根地址
    :param music_url: 音乐平台的单曲分享链接
    :param sources: 目标平台，非None时请求前尝试同步本地对应平台的Cookie
    :return: 包含歌曲信息或异常的统一结果字典
    """
    try:
        music_url = str(music_url).strip()

        await console.rp(f"开始提取信息：{music_url}", f"[{level}]")

        # 请求链接解析接口
        timeout = aiohttp.ClientTimeout(total=20, connect=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            params = {
                "q": music_url,
                "type": "song",
            }
            if sources is not None:
                params["sources"] = sources

            result = await request_json(
                api_url_format(api_url),
                session,
                "/api/v1/music/search",
                params,
                source=sources,
            )

        info_dict = result.get("data")
        if not isinstance(info_dict, dict):
            raise RuntimeError("音乐链接解析结果缺少data对象")

        songs = info_dict.get("songs")
        if not isinstance(songs, list):
            raise errors.NoSearchResultsError(music_url)

        extra_info: Dict[str, Any] = {
            "type": "song",
            "playlist_info_dict": None,
            "album_info_dict": None,
        }

        if len(songs) <= 0:
            raise RuntimeError("音乐链接中没有解析到歌曲")
        # 单曲
        elif len(songs) == 1:
            target_id = info_dict["songs"][0]['id']
        # 目标可能为歌单，尝试以歌单方式解析
        else:
            playlist_info_dict_result = await get_info_playlist(api_url, music_url, sources=sources, suppress_errors=True)
            if playlist_info_dict_result is not None and playlist_info_dict_result.result is not None:
                playlist_info_dict = playlist_info_dict_result.result
                extra_info["type"] = "playlist"
                extra_info["playlist_info_dict"] = playlist_info_dict
                target_id = playlist_info_dict["playlists"][0]['id']
            else:
                album_info_dict_result = await get_info_album(api_url, music_url, sources=sources, suppress_errors=True)
                if album_info_dict_result is not None and album_info_dict_result.result is not None:
                    album_info_dict = album_info_dict_result.result
                    extra_info["type"] = "album"
                    extra_info["album_info_dict"] = album_info_dict
                    target_id = album_info_dict["albums"][0]['id']
                # 错误分支，回退至第一音频id
                else:
                    target_id = info_dict["songs"][0]['id']

        await console.rp(f"信息提取完毕：{music_url} [{target_id}]", f"[{level}]")
    except Exception as e:
        return await handle_exception(e)

    result = success_result(result=info_dict)
    result.extra = extra_info
    return result


async def get_filesize(api_url: str, info_dict: dict) -> Result:
    """按info_dict中的source同步本地Cookie后探测大小，source为None时跳过同步。"""
    request_url = f"{api_url_format(api_url)}/api/v1/music/stream"
    try:
        timeout = aiohttp.ClientTimeout(total=10, connect=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            await use_local_cookie(api_url, session, info_dict.get("source"))
            async with session.get(request_url, params=build_music_params(info_dict), headers={"Range": "bytes=0-0"}) as response:
                if response.status == 206:
                    content_range = response.headers.get("Content-Range", "")
                    total_size = content_range.rsplit("/", 1)[-1]

                    if total_size and total_size != "*":
                        return success_result(result=int(total_size))

                # 某些情况可能不支持Range，而直接返回完整响应
                elif response.status == 200:
                    content_length = response.headers.get("Content-Length")
                    if content_length is not None:
                        return success_result(result=int(content_length))

                # 资源受限，go-music-api返回404 Failed to get URL
                elif response.status == 404:
                    body = await response.text(errors="replace")
                    raise errors.ResourceRestrictedError(f"{info_dict['source']}_{info_dict['id']}: {info_dict['name']} 疑似资源受限，状态码：{response.status}，{body}")

                else:
                    body = await response.text(errors="replace")
                    raise RuntimeError(f"状态码：{response.status}，{body}")

                raise RuntimeError("获取文件大小失败，响应中不存在有效的Content-Range或Content-Length")
    except Exception as e:
        return await handle_exception(e)


def construct_uid(source: str, song_id: str, quality: Optional[str] = None) -> str:
    """指定音质时添加音质后缀，否则保留平台与歌曲ID组成的UID。"""
    uid = f"{source}_{song_id}"
    quality = str(quality or "").strip()
    return f"{uid}_{quality}" if quality else uid


def get_music_uid(info_dict: Dict[str, Any]) -> str:
    """
    根据实际发送的音质参数构造缓存、文件名和Audio对象共用的UID。

    网易云自动设置的exhigh也属于指定音质；后端回退后仍按请求音质缓存。
    """
    params = build_music_params(info_dict)
    source = params["source"]
    quality = None
    if source in ("netease", "migu"):
        extra = json.loads(params["extra"])
        if isinstance(extra, dict):
            if source == "netease":
                quality = str(extra.get("netease_level") or "").strip().lower()
                if not quality:
                    quality = str(extra.get("level") or "").strip().lower()
                # 无效音质会被后端忽略，按后端默认下载处理
                if quality not in ("standard", "exhigh", "lossless", "hires"):
                    quality = None
            else:
                quality = extra.get("format_type")
    return construct_uid(source, params["id"], quality)


def extension_format(value: Any) -> str:
    """
    将接口返回的扩展名转换为安全的音频扩展名

    :param value: 接口返回的原始扩展名
    :return: 清理后的扩展名
    """
    extension = str(value or "").strip().lstrip(".").lower()
    extension = re.sub(r"[^a-z0-9]", "", extension)
    if not extension or len(extension) > 10:
        return "mp3"

    return extension


def detect_stream_extension(content_type: Optional[str], first_chunk: bytes, fallback: Any) -> str:
    """
    根据响应类型和文件头识别实际音频扩展名

    :param content_type: 音频流响应的 Content-Type
    :param first_chunk: 音频流的首个数据块
    :param fallback: 无法识别时使用的扩展名
    :return: 识别后的音频扩展名
    """
    # 优先使用文件签名识别实际容器格式
    if first_chunk.startswith(b"ID3"):
        return "mp3"
    if first_chunk.startswith(b"fLaC"):
        return "flac"
    if first_chunk.startswith(b"OggS"):
        return "ogg"
    if first_chunk.startswith(b"RIFF") and first_chunk[8:12] == b"WAVE":
        return "wav"
    if len(first_chunk) >= 8 and first_chunk[4:8] == b"ftyp":
        return "m4a"
    if first_chunk.startswith(b"\x1a\x45\xdf\xa3"):
        return "webm"

    # 使用标准 Content-Type 映射
    normalized_content_type = str(content_type or "").split(";", 1)[0]
    normalized_content_type = normalized_content_type.strip().lower()
    content_type_extensions = {
        "audio/mpeg": "mp3",
        "audio/mp3": "mp3",
        "audio/mp4": "m4a",
        "audio/x-m4a": "m4a",
        "video/mp4": "m4a",
        "audio/flac": "flac",
        "audio/x-flac": "flac",
        "audio/ogg": "ogg",
        "application/ogg": "ogg",
        "audio/wav": "wav",
        "audio/wave": "wav",
        "audio/x-wav": "wav",
        "audio/aac": "aac",
        "audio/webm": "webm",
        "video/webm": "webm",
    }
    detected_extension = content_type_extensions.get(normalized_content_type)
    if detected_extension is not None:
        return detected_extension

    # 第三阶段无法识别时使用接口扩展名
    return extension_format(fallback)


async def download_to_file(api_url: str, session: aiohttp.ClientSession, info_dict: Dict[str, Any], download_dir: Union[str, Path]) -> Tuple[Path, int]:
    """
    从音频流接口分块下载音频并原子保存到UID对应的确定路径

    请求前按info_dict中的source同步本地Cookie，source为None时跳过同步。

    :param api_url: go-music-api服务根地址
    :param session: aiohttp客户端会话
    :param info_dict: 标准化后的歌曲信息字典
    :param download_dir: 音频下载目录
    :return: 最终音频路径和实际下载字节数
    """
    stream_params = build_music_params(info_dict)
    stream_url = f"{api_url_format(api_url)}/api/v1/music/stream"
    uid = get_music_uid(info_dict)

    # 初始化临时文件状态
    part_path: Optional[Path] = None
    part_created = False

    try:
        await use_local_cookie(api_url, session, info_dict.get("source"))
        # 请求go-music-api代理音频流
        async with session.get(stream_url, params=stream_params) as response:
            response.raise_for_status()
            # 资源受限，go-music-api返回404 Failed to get URL
            if response.status == 404:
                body = await response.text(errors="replace")
                raise errors.ResourceRestrictedError(f"{info_dict['source']}_{info_dict['id']}: {info_dict['name']} 疑似资源受限，状态码：{response.status}，{body}")
            elif response.status not in (200, 206):
                raise RuntimeError(
                    f"音频流返回不支持的HTTP状态：{response.status}"
                )

            expected_size = response.content_length
            first_chunk = await response.content.read(CHUNK_SIZE)

            # 创建并校验下载目录
            download_dir = Path(download_dir).expanduser()
            download_dir.mkdir(parents=True, exist_ok=True)
            if not download_dir.is_dir():
                raise RuntimeError(f"下载路径不是目录：{download_dir}")

            # 整理文件名所需的歌曲信息
            if "artist" not in info_dict or info_dict["artist"] is None or info_dict["artist"].strip() == "":
                artist = "未知歌手"
            else:
                artist = info_dict["artist"].strip()

            if "name" not in info_dict or info_dict["name"] is None or info_dict["name"].strip() == "":
                title = "未知歌曲"
            else:
                title = info_dict["name"].strip()

            # 根据真实响应确定扩展名和目标路径
            file_extension = extension_format(
                detect_stream_extension(
                    response.headers.get("Content-Type"),
                    first_chunk,
                    info_dict.get("ext")
                )
            )

            # 使用UID构造确定的文件名
            file_title = utils.legal_name(f"{uid} - {artist} - {title}")
            download_path = download_dir / f"{file_title}.{file_extension}"

            part_path = download_path.with_name(f"{download_path.name}.part")
            await console.rp(f"开始下载：{download_path.name}", f"[{level}]",)

            # 将响应分块写入独立临时文件
            downloaded_size = len(first_chunk)
            with part_path.open("xb") as file:
                part_created = True

                if first_chunk:
                    file.write(first_chunk)

                async for chunk in response.content.iter_chunked(CHUNK_SIZE):
                    if not chunk:
                        continue

                    file.write(chunk)
                    downloaded_size += len(chunk)

                file.flush()
                os.fsync(file.fileno())

        # 校验下载结果
        if downloaded_size <= 0:
            raise RuntimeError("音频流为空，没有下载到任何数据")

        if expected_size is not None and downloaded_size != expected_size:
            raise RuntimeError(f"音频下载不完整，预期 {expected_size} 字节，实际 {downloaded_size} 字节")

        # 使用完整临时文件原子替换正式文件
        part_path.replace(download_path)
        return download_path, downloaded_size

    except BaseException:
        # 下载失败或任务取消时只删除当前任务创建的临时文件
        if part_created and part_path is not None and part_path.exists():
            try:
                part_path.unlink()
            except OSError:
                pass
        raise


async def audio_download(api_url: str, info_dict: Dict[str, Any], download_dir: Union[str, Path], download_type: DownloadType) -> Result:
    """
    使用歌曲信息下载音频并创建 Audio 对象

    底层下载请求会按info_dict中的source尝试同步本地Cookie，None时跳过。

    :param api_url: go-music-api服务根地址
    :param info_dict: get_info返回的歌曲信息字典
    :param download_dir: 音频下载目录
    :param download_type: 写入Audio对象的下载来源类型
    :return: 包含 Audio 对象或异常的统一结果字典
    """
    try:
        if resource_classifier.handler(download_type) is not DownloadHandler.GO_MUSIC_API:
            raise ValueError(f"错误下载类型：{download_type.name}")

        timeout = aiohttp.ClientTimeout(
            total=None,
            connect=10,
            sock_connect=10,
            sock_read=60,
        )
        async with aiohttp.ClientSession(timeout=timeout) as session:
            target_path, downloaded_size = await download_to_file(
                api_url,
                session,
                info_dict,
                download_dir,
            )

        converted_size = utils.convert_byte(downloaded_size)
        await console.rp(
            f"下载完成\n"
            f"文件名：{target_path.name}\n"
            f"来源：[{SOURCE_MAP[info_dict['source']]}] {info_dict['id']}\n"
            f"路径：{target_path.parent}\n"
            f"大小：{converted_size[0]} {converted_size[1]}\n"
            f"时长：{utils.convert_duration_to_str(info_dict['duration'])}",
            f"[{level}]",
        )

        new_audio = audio.Audio(
            title=f"{info_dict['artist']} - {info_dict['name']}",
            uid=get_music_uid(info_dict),
            source=info_dict["source"],
            source_id=info_dict['id'],
            download_type=download_type,
            path=str(target_path),
            duration=info_dict["duration"],
        )

        if "cover" in info_dict:
            new_audio.set_cover_url(info_dict["cover"])

    except Exception as exception:
        return await handle_exception(exception)

    return success_result(result=new_audio)
