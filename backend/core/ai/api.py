"""
核心 AI 模块 API 路由

提供统一的 AI 模型配置管理接口和聊天补全接口。
"""

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from core.ai import AIMessage, get_ai_service
from core.ai.model import get_model_service
from core.ai.model.schemas import (
    AIModelConfigCreate,
    AIModelConfigResponse,
    AIModelConfigUpdate,
    AIModelTestRequest,
    ConnectionTestResponse,
    ListModelsRequest,
    ListModelsResponse,
)
from core.auth.dependencies import get_current_active_user
from core.auth.rbac import Role
from core.user.models import UserModel

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/ai", tags=["AI Core"])


# =============================================================================
# 请求/响应模型
# =============================================================================

class ChatMessageRequest(BaseModel):
    """聊天消息请求"""
    role: str = Field(..., description="消息角色: system, user, assistant, tool")
    content: str = Field(..., description="消息内容")


class ChatCompletionRequest(BaseModel):
    """聊天补全请求"""
    model_id: str = Field(..., description="模型 ID")
    messages: list[ChatMessageRequest] = Field(..., description="消息列表")
    temperature: Optional[float] = Field(None, ge=0, le=2, description="温度参数")
    max_tokens: Optional[int] = Field(None, gt=0, description="最大 token 数")
    stream: bool = Field(False, description="是否使用流式输出")


class ChatCompletionResponse(BaseModel):
    """聊天补全响应"""
    content: str = Field(..., description="回复内容")
    reasoning_content: Optional[str] = Field(None, description="思考内容")
    thinking_tokens: Optional[int] = Field(None, description="思考 token 数")
    usage: Optional[dict] = Field(None, description="token 使用情况")


# =============================================================================
# AI 模型管理端点
# =============================================================================

@router.post("/models", response_model=AIModelConfigResponse)
async def create_model(
    request: AIModelConfigCreate,
    current_user: UserModel = Depends(get_current_active_user),
):
    """创建 AI 模型配置"""
    is_admin = current_user.role in [Role.ADMIN, Role.SUPER_ADMIN]
    service = get_model_service()
    return await service.create_model(str(current_user.id), request, is_admin)


@router.get("/models")
async def list_models(
    current_user: UserModel = Depends(get_current_active_user),
):
    """列出 AI 模型配置"""
    is_admin = current_user.role in [Role.ADMIN, Role.SUPER_ADMIN]
    service = get_model_service()
    return await service.list_models(str(current_user.id), is_admin)


@router.get("/models/{model_id}", response_model=AIModelConfigResponse)
async def get_model(
    model_id: str,
    current_user: UserModel = Depends(get_current_active_user),
):
    """获取单个 AI 模型配置"""
    is_admin = current_user.role in [Role.ADMIN, Role.SUPER_ADMIN]
    service = get_model_service()
    model = await service.get_model(model_id, str(current_user.id), is_admin)

    if not model:
        raise HTTPException(status_code=404, detail="模型配置不存在")

    return model


@router.put("/models/{model_id}", response_model=AIModelConfigResponse)
async def update_model(
    model_id: str,
    request: AIModelConfigUpdate,
    current_user: UserModel = Depends(get_current_active_user),
):
    """更新 AI 模型配置"""
    is_admin = current_user.role in [Role.ADMIN, Role.SUPER_ADMIN]
    service = get_model_service()
    model = await service.update_model(model_id, str(current_user.id), request, is_admin)

    if not model:
        raise HTTPException(status_code=404, detail="模型配置不存在或无权修改")

    return model


@router.delete("/models/{model_id}")
async def delete_model(
    model_id: str,
    current_user: UserModel = Depends(get_current_active_user),
):
    """删除 AI 模型配置"""
    is_admin = current_user.role in [Role.ADMIN, Role.SUPER_ADMIN]
    service = get_model_service()
    success = await service.delete_model(model_id, str(current_user.id), is_admin)

    if not success:
        raise HTTPException(status_code=404, detail="模型配置不存在或无权删除")

    return {"message": "模型配置已删除", "success": True}


@router.post("/models/{model_id}/test", response_model=ConnectionTestResponse)
async def test_model(
    model_id: str,
    current_user: UserModel = Depends(get_current_active_user),
):
    """测试 AI 模型连接"""
    is_admin = current_user.role in [Role.ADMIN, Role.SUPER_ADMIN]
    service = get_model_service()

    # 使用内部方法获取包含完整 API Key 的模型配置
    model_with_creds = await service.get_model_with_credentials(
        model_id, str(current_user.id), is_admin
    )
    if not model_with_creds:
        raise HTTPException(status_code=404, detail="模型配置不存在")

    test_request = AIModelTestRequest(
        api_base_url=model_with_creds["api_base_url"],
        api_key=model_with_creds["api_key"],
        model_id=model_with_creds["model_id"],
        timeout_seconds=10,
    )

    return await service.test_model_connection(test_request)


@router.post("/models/test", response_model=ConnectionTestResponse)
async def test_model_connection(
    request: AIModelTestRequest,
    current_user: UserModel = Depends(get_current_active_user),
):
    """测试 AI 模型连接（通用接口）"""
    service = get_model_service()
    return await service.test_model_connection(request)


@router.post("/models/list-available", response_model=ListModelsResponse)
async def list_available_models(
    request: ListModelsRequest,
    current_user: UserModel = Depends(get_current_active_user),
):
    """获取可用的模型列表"""
    service = get_model_service()
    return await service.list_available_models(request)


# =============================================================================
# 聊天补全端点
# =============================================================================

@router.post("/chat/completions")
async def chat_completion(
    request: ChatCompletionRequest,
    current_user: UserModel = Depends(get_current_active_user),
):
    """
    聊天补全接口

    支持流式输出和非流式输出。
    """
    ai_service = get_ai_service()

    # 设置配置服务
    from core.ai import AIService
    AIService.set_config_service(get_model_service())

    # 转换消息格式
    messages = [
        AIMessage(
            role=msg.role,
            content=msg.content,
        )
        for msg in request.messages
    ]

    # 流式输出
    if request.stream:
        async def generate():
            try:
                async for chunk in ai_service.stream_completion(
                    user_id=str(current_user.id),
                    messages=messages,
                    model_id=request.model_id,
                ):
                    # SSE 格式输出
                    data = {
                        "content": chunk.content,
                        "is_complete": chunk.is_complete,
                    }
                    yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
            except Exception as e:
                logger.error(f"流式输出错误: {e}")
                error_data = {"error": str(e), "is_complete": True}
                yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            }
        )

    # 非流式输出
    else:
        response = await ai_service.chat_completion(
            user_id=str(current_user.id),
            messages=messages,
            model_id=request.model_id,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )

        return ChatCompletionResponse(
            content=response.content,
            reasoning_content=response.reasoning_content,
            thinking_tokens=response.thinking_tokens,
            usage=response.usage,
        )
