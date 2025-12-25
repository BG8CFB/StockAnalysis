"""
基于角色的访问控制 (RBAC) 工具
"""
from enum import Enum
from typing import Set

from fastapi import HTTPException, status


class Role(str, Enum):
    """用户角色枚举"""
    GUEST = "GUEST"           # 访客（未登录）
    USER = "USER"             # 普通用户
    ADMIN = "ADMIN"           # 管理员
    SUPER_ADMIN = "SUPER_ADMIN"  # 超级管理员


class Permission(str, Enum):
    """权限枚举"""
    # 用户管理
    USER_CREATE = "user:create"
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    USER_MANAGE_ROLES = "user:manage_roles"
    USER_APPROVE = "user:approve"
    USER_DISABLE = "user:disable"
    USER_RESET_PASSWORD = "user:reset_password"

    # 系统管理
    SYSTEM_CONFIG = "system:config"
    SYSTEM_MONITOR = "system:monitor"
    SYSTEM_INITIALIZE = "system:initialize"

    # 审计日志
    AUDIT_READ = "audit:read"
    AUDIT_DELETE = "audit:delete"

    # 公共权限
    PUBLIC_ACCESS = "public:access"


# 角色权限映射
ROLE_PERMISSIONS: dict[Role, Set[Permission]] = {
    Role.GUEST: {
        Permission.PUBLIC_ACCESS,
    },
    Role.USER: {
        Permission.PUBLIC_ACCESS,
        Permission.USER_READ,      # 只能读自己的
        Permission.USER_UPDATE,    # 只能更新自己的
    },
    Role.ADMIN: {
        Permission.PUBLIC_ACCESS,
        Permission.USER_READ,           # 可以读所有用户
        Permission.USER_UPDATE,         # 可以更新所有用户
        Permission.USER_CREATE,
        Permission.USER_DELETE,
        Permission.USER_APPROVE,        # 审核用户
        Permission.USER_DISABLE,        # 禁用/启用用户
        Permission.USER_RESET_PASSWORD, # 触发密码重置
        Permission.AUDIT_READ,          # 查看审计日志
        Permission.SYSTEM_CONFIG,
        Permission.SYSTEM_MONITOR,
    },
    Role.SUPER_ADMIN: {
        # 超级管理员拥有所有权限
        *Permission.__members__.values(),
    }
}


def get_role_permissions(role: Role) -> Set[Permission]:
    """获取角色的所有权限"""
    return ROLE_PERMISSIONS.get(role, set())


def has_permission(role: Role, permission: Permission) -> bool:
    """检查角色是否拥有指定权限"""
    return permission in get_role_permissions(role)


def has_any_permission(role: Role, permissions: Set[Permission]) -> bool:
    """检查角色是否拥有任一指定权限"""
    role_permissions = get_role_permissions(role)
    return not permissions.isdisjoint(role_permissions)


def has_all_permissions(role: Role, permissions: Set[Permission]) -> bool:
    """检查角色是否拥有所有指定权限"""
    role_permissions = get_role_permissions(role)
    return permissions.issubset(role_permissions)


def require_permission(permission: Permission):
    """权限检查装饰器工厂"""
    from functools import wraps

    from core.auth.models import UserModel

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 从依赖注入获取当前用户
            user: UserModel = kwargs.get("current_user")
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="未认证"
                )

            user_role = Role(user.role)
            if not has_permission(user_role, permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"需要权限: {permission.value}"
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_role(*roles: Role):
    """角色检查装饰器工厂"""
    from functools import wraps

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            from core.auth.models import UserModel
            user: UserModel = kwargs.get("current_user")
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="未认证"
                )

            user_role = Role(user.role)
            if user_role not in roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"需要角色: {', '.join(r.value for r in roles)}"
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator


# 角色层级（用于权限继承）
ROLE_HIERARCHY = {
    Role.SUPER_ADMIN: 3,
    Role.ADMIN: 2,
    Role.USER: 1,
    Role.GUEST: 0,
}


def get_role_level(role: Role) -> int:
    """获取角色等级"""
    return ROLE_HIERARCHY.get(role, 0)


def is_higher_role(role1: Role, role2: Role) -> bool:
    """检查 role1 是否比 role2 等级更高"""
    return get_role_level(role1) > get_role_level(role2)
