"""
管理员核心业务逻辑服务
处理用户审核、管理、列表查询等
"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from core.config import settings
from core.db.mongodb import mongodb
from core.user.models import Role, UserModel, UserStatus, UserListResponse

logger = logging.getLogger(__name__)


class AdminService:
    """管理员核心服务"""

    def __init__(self) -> None:
        pass

    @property
    def db(self) -> AsyncIOMotorDatabase:
        """获取数据库实例"""
        return mongodb.database

    # ==================== 用户列表（带筛选）====================

    async def get_users(
        self,
        skip: int = 0,
        limit: int = 20,
        role: Optional[Role] = None,
        status: Optional[UserStatus] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> tuple[List[dict], int]:
        """获取用户列表（支持筛选和搜索）

        Returns:
            (用户列表, 总数)
        """
        query = {}

        # 角色筛选
        if role:
            query["role"] = role

        # 状态筛选
        if status:
            query["status"] = status

        # 激活状态筛选
        if is_active is not None:
            query["is_active"] = is_active

        # 搜索（邮箱或用户名）
        if search:
            query["$or"] = [
                {"email": {"$regex": search, "$options": "i"}},
                {"username": {"$regex": search, "$options": "i"}},
            ]

        # 计算总数
        total = await self.db.users.count_documents(query)

        # 查询数据
        cursor = (
            self.db.users
            .find(query)
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
        )

        users = []
        async for user_doc in cursor:
            # 使用 UserModel 验证，然后用 UserListResponse 序列化（带有正确的字段别名）
            user_model = UserModel.model_validate(user_doc)
            # 转换为 UserListResponse 以应用 serialization_alias
            user_response = UserListResponse(
                id=str(user_model.id),
                email=user_model.email,
                username=user_model.username,
                role=user_model.role.value,
                status=user_model.status,
                is_active=user_model.is_active,
                is_verified=user_model.is_verified,
                created_at=user_model.created_at,
                last_login_at=user_model.last_login_at,
                reviewed_by=str(user_model.reviewed_by) if user_model.reviewed_by else None,
                reviewed_at=user_model.reviewed_at,
            )
            users.append(user_response.model_dump(by_alias=True))

        return users, total

    async def get_pending_users(
        self,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[List[dict], int]:
        """获取待审核用户列表"""
        query = {"status": UserStatus.PENDING}
        total = await self.db.users.count_documents(query)

        cursor = (
            self.db.users
            .find(query)
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
        )

        users = []
        async for user_doc in cursor:
            # 使用 UserModel 验证，然后用 UserListResponse 序列化（带有正确的字段别名）
            user_model = UserModel.model_validate(user_doc)
            # 转换为 UserListResponse 以应用 serialization_alias
            user_response = UserListResponse(
                id=str(user_model.id),
                email=user_model.email,
                username=user_model.username,
                role=user_model.role.value,
                status=user_model.status,
                is_active=user_model.is_active,
                is_verified=user_model.is_verified,
                created_at=user_model.created_at,
                last_login_at=user_model.last_login_at,
                reviewed_by=str(user_model.reviewed_by) if user_model.reviewed_by else None,
                reviewed_at=user_model.reviewed_at,
            )
            users.append(user_response.model_dump(by_alias=True))

        return users, total

    # ==================== 用户审核 ====================

    async def approve_user(
        self,
        user_id: str,
        admin_id: str,
    ) -> UserModel:
        """通过用户审核"""
        # 检查用户是否存在
        user = await self.db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise ValueError("用户不存在")

        # 检查当前状态
        if user.get("status") != UserStatus.PENDING:
            raise ValueError(f"用户状态为 {user.get('status')}，无法审核")

        # 更新状态
        await self.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "status": UserStatus.ACTIVE,
                    "is_active": True,
                    "reviewed_by": ObjectId(admin_id),
                    "reviewed_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                }
            }
        )

        # 记录审计日志
        await self._create_audit_log(
            action="approve",
            target_user_id=user_id,
            user_id=admin_id,
        )

        logger.info(f"用户审核通过: admin_id={admin_id}, user_id={user_id}")

        return await self._get_user_model(user_id)

    async def reject_user(
        self,
        user_id: str,
        admin_id: str,
        reason: str,
    ) -> UserModel:
        """拒绝用户审核"""
        # 检查用户是否存在
        user = await self.db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise ValueError("用户不存在")

        # 检查当前状态
        if user.get("status") != UserStatus.PENDING:
            raise ValueError(f"用户状态为 {user.get('status')}，无法审核")

        # 更新状态
        await self.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "status": UserStatus.REJECTED,
                    "is_active": False,
                    "reviewed_by": ObjectId(admin_id),
                    "reviewed_at": datetime.utcnow(),
                    "reject_reason": reason,
                    "updated_at": datetime.utcnow(),
                }
            }
        )

        # 记录审计日志
        await self._create_audit_log(
            action="reject",
            target_user_id=user_id,
            user_id=admin_id,
            reason=reason,
        )

        logger.warning(f"用户审核被拒绝: admin_id={admin_id}, user_id={user_id}, reason={reason}")

        return await self._get_user_model(user_id)

    async def disable_user(
        self,
        user_id: str,
        admin_id: str,
        reason: Optional[str] = None,
    ) -> UserModel:
        """禁用用户"""
        # 检查用户是否存在
        user = await self.db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise ValueError("用户不存在")

        # 不能禁用自己
        if user_id == admin_id:
            raise ValueError("不能禁用自己的账号")

        # 更新状态
        await self.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "status": UserStatus.DISABLED,
                    "is_active": False,
                    "updated_at": datetime.utcnow(),
                }
            }
        )

        # 记录审计日志
        await self._create_audit_log(
            action="disable",
            target_user_id=user_id,
            user_id=admin_id,
            reason=reason,
        )

        logger.warning(f"用户被禁用: admin_id={admin_id}, user_id={user_id}, reason={reason}")

        return await self._get_user_model(user_id)

    async def enable_user(
        self,
        user_id: str,
        admin_id: str,
    ) -> UserModel:
        """启用用户（恢复被禁用的用户）"""
        # 检查用户是否存在
        user = await self.db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise ValueError("用户不存在")

        # 只能恢复被禁用的用户
        if user.get("status") != UserStatus.DISABLED:
            raise ValueError(f"用户状态为 {user.get('status')}，无法启用")

        # 更新状态
        await self.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "status": UserStatus.ACTIVE,
                    "is_active": True,
                    "updated_at": datetime.utcnow(),
                }
            }
        )

        # 记录审计日志
        await self._create_audit_log(
            action="enable",
            target_user_id=user_id,
            user_id=admin_id,
        )

        return await self._get_user_model(user_id)

    # ==================== 用户管理 ====================

    async def get_user_by_id(
        self,
        user_id: str,
    ) -> UserModel:
        """获取单个用户详情"""
        user = await self.db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise ValueError("用户不存在")
        return UserModel(**user)

    async def create_user(
        self,
        email: str,
        username: str,
        password: str,
        role: Role = Role.USER,
        created_by: Optional[str] = None,
    ) -> UserModel:
        """管理员创建用户"""
        from core.auth.security import password_manager

        # 检查邮箱和用户名是否已存在
        existing = await self.db.users.find_one({
            "$or": [{"email": email}, {"username": username}]
        })
        if existing:
            raise ValueError("用户名或邮箱已存在")

        # 创建用户文档
        user_doc = {
            "email": email,
            "username": username,
            "hashed_password": password_manager.hash_password(password),
            "role": role,
            "status": UserStatus.ACTIVE,  # 管理员创建的用户直接激活
            "is_active": True,
            "is_verified": True,
            "created_by": ObjectId(created_by) if created_by else None,
            "last_login_at": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        result = await self.db.users.insert_one(user_doc)

        # 记录审计日志
        await self._create_audit_log(
            action="create_user",
            target_user_id=str(result.inserted_id),
            user_id=created_by or "system",
        )

        return await self._get_user_model(str(result.inserted_id))

    async def update_user(
        self,
        user_id: str,
        update_data: dict,
    ) -> UserModel:
        """更新用户信息"""
        # 过滤 None 值
        update_data = {k: v for k, v in update_data.items() if v is not None}
        if not update_data:
            return await self._get_user_model(user_id)

        update_data["updated_at"] = datetime.utcnow()

        await self.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_data},
        )

        return await self._get_user_model(user_id)

    async def change_user_role(
        self,
        user_id: str,
        new_role: Role,
        admin_id: str,
    ) -> UserModel:
        """修改用户角色"""
        # 检查用户是否存在
        user = await self.db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise ValueError("用户不存在")

        # 不能修改自己的角色
        if user_id == admin_id:
            raise ValueError("不能修改自己的角色")

        # 更新角色
        await self.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "role": new_role,
                    "updated_at": datetime.utcnow(),
                }
            }
        )

        # 记录审计日志
        await self._create_audit_log(
            action="role_change",
            target_user_id=user_id,
            user_id=admin_id,
        )

        return await self._get_user_model(user_id)

    async def delete_user(
        self,
        user_id: str,
        admin_id: str,
    ) -> bool:
        """删除用户"""
        # 检查用户是否存在
        user = await self.db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise ValueError("用户不存在")

        # 不能删除自己
        if user_id == admin_id:
            raise ValueError("不能删除自己的账号")

        # 删除用户配置
        await self.db.user_preferences.delete_many({"user_id": ObjectId(user_id)})

        # 删除用户
        result = await self.db.users.delete_one({"_id": ObjectId(user_id)})

        # 记录审计日志
        await self._create_audit_log(
            action="delete",
            target_user_id=user_id,
            user_id=admin_id,
        )

        return result.deleted_count > 0

    # ==================== 密码重置（管理员触发）====================

    async def admin_request_password_reset(
        self,
        target_user_id: str,
        admin_id: str,
    ) -> str:
        """管理员触发用户密码重置

        Returns:
            reset_token: 重置令牌
        """
        import json
        import secrets

        from core.db.redis import get_redis

        # 检查用户是否存在
        user = await self.db.users.find_one({"_id": ObjectId(target_user_id)})
        if not user:
            raise ValueError("用户不存在")

        # 生成重置 token
        reset_token = secrets.token_urlsafe(32)
        token_key = f"password_reset:{reset_token}"

        # 存储到 Redis（1小时有效期）
        redis = await get_redis()
        await redis.set(
            token_key,
            json.dumps({"user_id": target_user_id, "triggered_by": admin_id}),
            ex=3600,
        )

        # 开发环境：打印到控制台
        if settings.DEBUG:
            email = user.get("email", "")
            print(f"[Admin Password Reset] Email: {email}, Token: {reset_token}")
            print(f"Reset URL: http://localhost:5173/reset-password?token={reset_token}")

        # TODO: 生产环境发送邮件

        # 记录审计日志
        await self._create_audit_log(
            action="password_reset",
            target_user_id=target_user_id,
            user_id=admin_id,
        )

        return reset_token

    # ==================== 清理任务 ====================

    async def cleanup_rejected_users(self, days: int = 1) -> int:
        """清理被拒绝超过指定天数的用户数据

        Returns:
            清理的用户数量
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # 查找需要删除的用户
        cursor = self.db.users.find({
            "status": UserStatus.REJECTED,
            "reviewed_at": {"$lt": cutoff_date}
        })

        user_ids = []
        async for user in cursor:
            user_ids.append(user["_id"])

        # 删除用户和相关数据
        count = 0
        for user_id in user_ids:
            # 删除用户配置
            await self.db.user_preferences.delete_many({"user_id": user_id})
            # 删除用户
            result = await self.db.users.delete_one({"_id": user_id})
            count += result.deleted_count

        return count

    # ==================== 辅助方法 ====================

    async def _get_user_model(self, user_id: str) -> UserModel:
        """获取用户模型"""
        user = await self.db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise ValueError("用户不存在")
        return UserModel(**user)

    async def _create_audit_log(
        self,
        action: str,
        user_id: str,
        target_user_id: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> None:
        """创建审计日志"""
        log_doc = {
            "user_id": ObjectId(user_id),
            "target_user_id": ObjectId(target_user_id) if target_user_id else None,
            "action": action,
            "reason": reason,
            "created_at": datetime.utcnow(),
        }
        await self.db.audit_logs.insert_one(log_doc)


# 全局服务实例
admin_service = AdminService()
