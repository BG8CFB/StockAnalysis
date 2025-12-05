from typing import Optional
from datetime import datetime, timedelta
from bson import ObjectId
from fastapi import HTTPException, status

from core.db.mongodb import mongodb
from core.auth.dependencies import verify_password, get_password_hash, create_access_token
from core.auth.models import UserCreate, User
from core.events.bus import event_bus
from core.events.schemas import EventTypes, UserRegisteredEvent, UserLoginEvent

from .models import UserProfileUpdate, PasswordChange


class UserService:
    """用户服务类"""

    def __init__(self):
        self.db = mongodb.get_database()
        self.collection = self.db.users

    async def create_user(self, user_data: UserCreate) -> User:
        """创建新用户"""
        # 检查邮箱是否已存在
        existing_user = await self.collection.find_one({"email": user_data.email})
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # 检查用户名是否已存在
        existing_username = await self.collection.find_one({"username": user_data.username})
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )

        # 创建用户文档
        user_doc = {
            "email": user_data.email,
            "username": user_data.username,
            "full_name": user_data.full_name,
            "hashed_password": get_password_hash(user_data.password),
            "is_active": True,
            "is_superuser": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "last_login": None
        }

        # 插入数据库
        result = await self.collection.insert_one(user_doc)
        user_doc["_id"] = result.inserted_id

        # 发布用户注册事件
        await event_bus.publish(
            EventTypes.USER_REGISTERED,
            {
                "user_id": str(result.inserted_id),
                "email": user_data.email,
                "username": user_data.username
            },
            source_module="user_management"
        )

        # 转换为User模型
        return User(
            id=str(result.inserted_id),
            email=user_data.email,
            username=user_data.username,
            full_name=user_data.full_name,
            is_active=True,
            is_superuser=False,
            created_at=user_doc["created_at"],
            updated_at=user_doc["updated_at"],
            last_login=None
        )

    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """验证用户凭据"""
        user_doc = await self.collection.find_one({"email": email})
        if not user_doc:
            return None

        if not verify_password(password, user_doc["hashed_password"]):
            return None

        if not user_doc.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User account is inactive"
            )

        # 更新最后登录时间
        await self.collection.update_one(
            {"_id": user_doc["_id"]},
            {"$set": {"last_login": datetime.utcnow()}}
        )

        # 发布登录事件
        await event_bus.publish(
            EventTypes.USER_LOGIN,
            {
                "user_id": str(user_doc["_id"]),
                "email": user_doc["email"]
            },
            source_module="user_management"
        )

        # 转换为User模型
        return User(
            id=str(user_doc["_id"]),
            email=user_doc["email"],
            username=user_doc["username"],
            full_name=user_doc.get("full_name"),
            is_active=user_doc.get("is_active", True),
            is_superuser=user_doc.get("is_superuser", False),
            created_at=user_doc.get("created_at", datetime.utcnow()),
            updated_at=user_doc.get("updated_at", datetime.utcnow()),
            last_login=datetime.utcnow()
        )

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """根据ID获取用户"""
        try:
            object_id = ObjectId(user_id)
        except:
            return None

        user_doc = await self.collection.find_one({"_id": object_id})
        if not user_doc:
            return None

        return User(
            id=str(user_doc["_id"]),
            email=user_doc["email"],
            username=user_doc["username"],
            full_name=user_doc.get("full_name"),
            is_active=user_doc.get("is_active", True),
            is_superuser=user_doc.get("is_superuser", False),
            created_at=user_doc.get("created_at", datetime.utcnow()),
            updated_at=user_doc.get("updated_at", datetime.utcnow()),
            last_login=user_doc.get("last_login")
        )

    async def update_user_profile(self, user_id: str, update_data: UserProfileUpdate) -> Optional[User]:
        """更新用户资料"""
        try:
            object_id = ObjectId(user_id)
        except:
            return None

        # 构建更新数据
        update_doc = {}
        if update_data.username is not None:
            # 检查用户名是否已被其他用户使用
            existing = await self.collection.find_one({
                "username": update_data.username,
                "_id": {"$ne": object_id}
            })
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already taken"
                )
            update_doc["username"] = update_data.username

        if update_data.email is not None:
            # 检查邮箱是否已被其他用户使用
            existing = await self.collection.find_one({
                "email": update_data.email,
                "_id": {"$ne": object_id}
            })
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
            update_doc["email"] = update_data.email

        if update_data.full_name is not None:
            update_doc["full_name"] = update_data.full_name

        if update_doc:
            update_doc["updated_at"] = datetime.utcnow()

            result = await self.collection.update_one(
                {"_id": object_id},
                {"$set": update_doc}
            )

            if result.modified_count == 0:
                return None

        return await self.get_user_by_id(user_id)

    async def change_password(self, user_id: str, password_data: PasswordChange) -> bool:
        """修改用户密码"""
        try:
            object_id = ObjectId(user_id)
        except:
            return False

        user_doc = await self.collection.find_one({"_id": object_id})
        if not user_doc:
            return False

        # 验证当前密码
        if not verify_password(password_data.current_password, user_doc["hashed_password"]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )

        # 更新密码
        new_hashed_password = get_password_hash(password_data.new_password)
        result = await self.collection.update_one(
            {"_id": object_id},
            {
                "$set": {
                    "hashed_password": new_hashed_password,
                    "updated_at": datetime.utcnow()
                }
            }
        )

        return result.modified_count > 0

    async def login_user(self, email: str, password: str) -> tuple[str, User]:
        """用户登录，返回token和用户信息"""
        user = await self.authenticate_user(email, password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )

        # 创建访问令牌
        access_token_expires = timedelta(minutes=30)
        access_token = create_access_token(
            data={"sub": user.id, "email": user.email},
            expires_delta=access_token_expires
        )

        return access_token, user


# 创建服务实例
user_service = UserService()