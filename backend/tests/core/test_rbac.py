"""
测试 RBAC 权限系统
"""

from core.auth.rbac import (
    Permission,
    Role,
    get_role_level,
    get_role_permissions,
    has_all_permissions,
    has_any_permission,
    has_permission,
    is_higher_role,
)


class TestRole:
    """角色枚举测试"""

    def test_role_values(self) -> None:
        assert Role.GUEST.value == "GUEST"
        assert Role.USER.value == "USER"
        assert Role.ADMIN.value == "ADMIN"
        assert Role.SUPER_ADMIN.value == "SUPER_ADMIN"

    def test_role_is_string(self) -> None:
        assert isinstance(Role.USER, str)
        assert Role.USER == "USER"


class TestPermission:
    """权限枚举测试"""

    def test_permission_format(self) -> None:
        assert ":" in Permission.USER_CREATE.value
        assert Permission.USER_CREATE.value == "user:create"

    def test_public_access_exists(self) -> None:
        assert Permission.PUBLIC_ACCESS.value == "public:access"


class TestRolePermissions:
    """角色权限映射测试"""

    def test_guest_has_minimal_permissions(self) -> None:
        perms = get_role_permissions(Role.GUEST)
        assert Permission.PUBLIC_ACCESS in perms
        assert Permission.USER_CREATE not in perms

    def test_user_has_basic_permissions(self) -> None:
        perms = get_role_permissions(Role.USER)
        assert Permission.PUBLIC_ACCESS in perms
        assert Permission.USER_READ in perms
        assert Permission.USER_UPDATE in perms
        assert Permission.USER_DELETE not in perms

    def test_admin_has_management_permissions(self) -> None:
        perms = get_role_permissions(Role.ADMIN)
        assert Permission.USER_CREATE in perms
        assert Permission.USER_DELETE in perms
        assert Permission.USER_APPROVE in perms
        assert Permission.SYSTEM_CONFIG in perms

    def test_super_admin_has_all_permissions(self) -> None:
        perms = get_role_permissions(Role.SUPER_ADMIN)
        all_perms = set(Permission.__members__.values())
        assert perms == all_perms

    def test_permission_escalation_pattern(self) -> None:
        """权限递增模式：GUEST < USER < ADMIN < SUPER_ADMIN"""
        guest_perms = get_role_permissions(Role.GUEST)
        user_perms = get_role_permissions(Role.USER)
        admin_perms = get_role_permissions(Role.ADMIN)
        super_perms = get_role_permissions(Role.SUPER_ADMIN)
        assert guest_perms < user_perms < admin_perms <= super_perms


class TestHasPermission:
    """权限检查函数测试"""

    def test_has_permission_true(self) -> None:
        assert has_permission(Role.ADMIN, Permission.USER_CREATE) is True

    def test_has_permission_false(self) -> None:
        assert has_permission(Role.GUEST, Permission.USER_CREATE) is False

    def test_has_any_permission_true(self) -> None:
        perms = {Permission.USER_CREATE, Permission.USER_DELETE}
        assert has_any_permission(Role.ADMIN, perms) is True

    def test_has_any_permission_false(self) -> None:
        perms = {Permission.USER_CREATE, Permission.USER_DELETE}
        assert has_any_permission(Role.GUEST, perms) is False

    def test_has_all_permissions_true(self) -> None:
        perms = {Permission.USER_READ, Permission.USER_UPDATE}
        assert has_all_permissions(Role.USER, perms) is True

    def test_has_all_permissions_false(self) -> None:
        perms = {Permission.USER_READ, Permission.USER_DELETE}
        assert has_all_permissions(Role.USER, perms) is False


class TestRoleHierarchy:
    """角色层级测试"""

    def test_role_levels(self) -> None:
        assert get_role_level(Role.GUEST) == 0
        assert get_role_level(Role.USER) == 1
        assert get_role_level(Role.ADMIN) == 2
        assert get_role_level(Role.SUPER_ADMIN) == 3

    def test_is_higher_role(self) -> None:
        assert is_higher_role(Role.ADMIN, Role.USER) is True
        assert is_higher_role(Role.USER, Role.ADMIN) is False
        assert is_higher_role(Role.ADMIN, Role.ADMIN) is False
