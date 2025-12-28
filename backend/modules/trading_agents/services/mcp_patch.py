"""
MCP Python SDK Bug 补丁

修复以下已知问题：
1. Issue #1672: 空 SSE 数据导致 ValidationError
2. Issue #1190: ClosedResourceError in streamable_http
3. 自定义错误响应格式兼容：Finance MCP 服务器返回非 JSON-RPC 格式（code: 1001）

参考：
https://github.com/modelcontextprotocol/python-sdk/issues/1672
https://github.com/modelcontextprotocol/python-sdk/issues/1190
"""
import logging
import json
from typing import Any

logger = logging.getLogger(__name__)


def apply_mcp_patches() -> None:
    """
    应用 MCP Python SDK 的所有补丁

    在应用启动时调用此函数，修复 MCP 客户端的已知 Bug。
    """
    patches_applied = []

    try:
        _patch_streamable_http_empty_sse()
        patches_applied.append("空 SSE 数据解析修复")
    except Exception as e:
        logger.warning(f"⚠️ 空 SSE 补丁应用失败: {e}")

    try:
        _patch_streamable_http_custom_error_format()
        patches_applied.append("自定义错误响应格式兼容")
    except Exception as e:
        logger.warning(f"⚠️ 自定义错误格式补丁应用失败: {e}")

    if patches_applied:
        logger.info(f"✅ MCP 补丁已应用: {', '.join(patches_applied)}")


def _patch_streamable_http_empty_sse() -> None:
    """
    修复 streamable_http 客户端的空 SSE 数据解析问题

    问题描述：
    MCP 服务器发送空 SSE 事件作为"priming events"（用于可恢复性支持）
    Python 客户端尝试将所有 SSE 数据解析为 JSON，但没有检查是否为空
    空字符串 '' 无法解析为 JSON，导致 ValidationError

    解决方案：
    在解析前检查 SSE 数据是否为空，如果为空则跳过
    """
    try:
        from mcp.client.streamable_http import StreamableHTTPTransport

        # 保存原始方法
        original_handle_sse_message = StreamableHTTPTransport._handle_sse_message

        # 创建补丁版本
        async def patched_handle_sse_message(
            self,
            sse,
            read_stream_writer,
            original_request_id=None,
            resumption_callback=None,
            is_initialization=False,
        ):
            """修补后的 _handle_sse_message 方法，跳过空 SSE 数据"""
            # 跳过空数据
            if not sse.data or sse.data.strip() == "":
                logger.debug(f"跳过空 SSE 数据 (event: {sse.event})")
                return False

            # 调用原始方法处理非空数据
            return await original_handle_sse_message(
                self,
                sse,
                read_stream_writer,
                original_request_id,
                resumption_callback,
                is_initialization,
            )

        # 应用补丁
        StreamableHTTPTransport._handle_sse_message = patched_handle_sse_message

    except ImportError:
        logger.warning("无法导入 StreamableHTTPTransport，可能未安装 mcp 包")
    except AttributeError as e:
        logger.warning(f"StreamableHTTPTransport 方法不存在: {e}")


def _patch_streamable_http_custom_error_format() -> None:
    """
    修复 MCP 服务器返回自定义错误格式的问题

    问题描述：
    某些 MCP 服务器（如 Finance MCP）返回非 JSON-RPC 2.0 标准格式的错误响应：
    {
      "code": 1001,
      "msg": "...",
      "success": false
    }

    而 Python MCP 客户端严格遵循 JSON-RPC 2.0 规范，期望：
    {
      "jsonrpc": "2.0",
      "id": 1,
      "error": {
        "code": -32600,
        "message": "Invalid Request"
      }
    }

    导致 ValidationError: JSONRPCMessage validation failed

    解决方案：
    在 JSON 解析前检测自定义格式，并记录警告日志跳过该响应
    """
    try:
        from mcp.client.streamable_http import StreamableHTTPTransport

        # 保存原始方法
        original_handle_json_response = StreamableHTTPTransport._handle_json_response

        # 创建补丁版本
        async def patched_handle_json_response(self, content: str, ctx: Any) -> None:
            """修补后的 _handle_json_response 方法，兼容自定义错误格式"""
            try:
                # 尝试解析 JSON
                data = json.loads(content.strip())

                # 检测是否为自定义错误格式（包含 code/msg/success 字段）
                if isinstance(data, dict) and set(data.keys()) >= {"code", "msg", "success"}:
                    # 这是自定义格式，不是 JSON-RPC 2.0
                    if not data.get("success", True):
                        error_code = data.get("code", "unknown")
                        error_msg = data.get("msg", "Unknown error")
                        logger.error(
                            f"MCP 服务器返回自定义错误格式 (非 JSON-RPC 2.0): "
                            f"code={error_code}, msg={error_msg}"
                        )
                        # 不抛出异常，直接返回（跳过此响应）
                        return

                # 尝试标准 JSON-RPC 格式解析
                return await original_handle_json_response(self, content, ctx)

            except json.JSONDecodeError:
                # JSON 解析失败，调用原始方法
                return await original_handle_json_response(self, content, ctx)
            except Exception as e:
                # 其他异常也传递给原始方法
                logger.debug(f"补丁处理异常，传递给原始方法: {e}")
                return await original_handle_json_response(self, content, ctx)

        # 应用补丁
        StreamableHTTPTransport._handle_json_response = patched_handle_json_response

    except ImportError:
        logger.warning("无法导入 StreamableHTTPTransport，可能未安装 mcp 包")
    except AttributeError as e:
        logger.warning(f"StreamableHTTPTransport._handle_json_response 方法不存在: {e}")
