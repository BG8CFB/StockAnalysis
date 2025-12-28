"""
MCP Python SDK 自定义错误格式兼容补丁

问题描述：
某些 MCP 服务器（如智谱 AI 的 web-search-prime、web-reader）返回非 JSON-RPC 2.0 标准格式的错误响应：
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
在 JSON 解析前检测自定义格式，记录日志并跳过该响应，避免崩溃
"""
import json
import logging

logger = logging.getLogger(__name__)


def apply_mcp_patches() -> None:
    """
    应用 MCP Python SDK 的兼容性补丁

    在应用启动时调用此函数，修复与自定义 MCP 服务器的兼容性问题。
    """
    try:
        _patch_streamable_http_custom_error_format()
        logger.info("✅ MCP 补丁已应用: 自定义错误响应格式兼容")
    except Exception as e:
        logger.warning(f"⚠️ MCP 补丁应用失败: {e}")


def _patch_streamable_http_custom_error_format() -> None:
    """
    修复 MCP 服务器返回自定义错误格式的问题

    使用 monkey patch 替换 StreamableHTTPTransport._handle_json_response 方法，
    在解析 JSON 前检测并跳过自定义错误格式。
    """
    try:
        from mcp.client.streamable_http import StreamableHTTPTransport
        import httpx

        # 保存原始方法
        original_handle_json_response = StreamableHTTPTransport._handle_json_response

        # 创建补丁版本（方法签名必须与原始方法完全一致）
        async def patched_handle_json_response(
            self,
            response: httpx.Response,
            read_stream_writer,
            is_initialization: bool = False,
        ) -> None:
            """修补后的 _handle_json_response 方法，兼容自定义错误格式"""
            try:
                # 读取响应内容
                content = await response.aread()
                content_str = content.decode("utf-8") if isinstance(content, bytes) else content

                # 尝试解析 JSON 进行自定义格式检测
                data = json.loads(content_str.strip())

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

                # 标准格式：继续原始流程
                return await original_handle_json_response(
                    self, response, read_stream_writer, is_initialization
                )

            except json.JSONDecodeError:
                # JSON 解析失败，调用原始方法
                return await original_handle_json_response(
                    self, response, read_stream_writer, is_initialization
                )
            except Exception as e:
                # 其他异常也传递给原始方法
                logger.debug(f"补丁处理异常，传递给原始方法: {e}")
                return await original_handle_json_response(
                    self, response, read_stream_writer, is_initialization
                )

        # 应用补丁
        StreamableHTTPTransport._handle_json_response = patched_handle_json_response

    except ImportError:
        logger.warning("无法导入 StreamableHTTPTransport，可能未安装 mcp 包")
    except AttributeError as e:
        logger.warning(f"StreamableHTTPTransport._handle_json_response 方法不存在: {e}")
