"""Role-Based Access Control system with enterprise permission management."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class Action(str, Enum):
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    MANAGE = "manage"
    SUPERVISE = "supervise"


class Resource(str, Enum):
    TENDER = "tender"
    DOCUMENT = "document"
    USER = "user"
    ORGANIZATION = "organization"
    SYSTEM = "system"
    REPORT = "report"


class Scope(str, Enum):
    OWN = "own"
    TEAM = "team"
    ORGANIZATION = "organization"
    GLOBAL = "global"


@dataclass
class Permission:
    action: Action
    resource: Resource
    condition: Optional[str] = None
    constraints: Optional[Dict[str, Any]] = None


@dataclass
class Role:
    id: str
    name: str
    description: str
    level: int
    permissions: List[Permission] = field(default_factory=list)


@dataclass
class UserRole:
    user_id: str
    tenant_id: str
    role_id: str
    department: Optional[str] = None
    zone: Optional[str] = None
    granted_at: datetime = field(default_factory=datetime.utcnow)
    granted_by: str = ""
    expires_at: Optional[datetime] = None
    is_active: bool = True


@dataclass
class RBACPolicy:
    id: str
    name: str
    description: str
    rules: List[Dict[str, Any]] = field(default_factory=list)
    is_active: bool = True


class RBACService:
    def __init__(self):
        self._roles: Dict[str, Role] = {}
        self._user_roles: Dict[str, List[UserRole]] = {}
        self._policies: Dict[str, RBACPolicy] = {}
        self._initialize_defaults()

    def _initialize_defaults(self) -> None:
        roles = [
            Role("super-admin", "Super Administrator", "Full system access", 10, [
                Permission(Action.MANAGE, Resource.SYSTEM),
                Permission(Action.MANAGE, Resource.USER),
                Permission(Action.MANAGE, Resource.ORGANIZATION),
                Permission(Action.MANAGE, Resource.TENDER),
                Permission(Action.MANAGE, Resource.DOCUMENT),
                Permission(Action.READ, Resource.REPORT),
                Permission(Action.WRITE, Resource.REPORT),
            ]),
            Role("tenant-admin", "Tenant Administrator", "Administrative access within tenant", 9, [
                Permission(Action.MANAGE, Resource.ORGANIZATION),
                Permission(Action.MANAGE, Resource.USER),
                Permission(Action.READ, Resource.TENDER),
                Permission(Action.WRITE, Resource.TENDER),
                Permission(Action.MANAGE, Resource.DOCUMENT),
                Permission(Action.READ, Resource.REPORT),
                Permission(Action.WRITE, Resource.REPORT),
                Permission(Action.SUPERVISE, Resource.TENDER),
            ]),
            Role("compliance-officer", "Compliance Officer", "PPR compliance verification", 8, [
                Permission(Action.READ, Resource.TENDER),
                Permission(Action.WRITE, Resource.TENDER, condition="hasPPRCompliance"),
                Permission(Action.MANAGE, Resource.DOCUMENT, condition="canUploadComplianceDocs"),
                Permission(Action.READ, Resource.REPORT),
                Permission(Action.WRITE, Resource.REPORT),
            ]),
            Role("bid-analyst", "Bid Analyst", "Tender analysis and evaluation", 7, [
                Permission(Action.READ, Resource.TENDER),
                Permission(Action.WRITE, Resource.TENDER),
                Permission(Action.READ, Resource.REPORT),
                Permission(Action.WRITE, Resource.REPORT),
                Permission(Action.EXECUTE, Resource.TENDER, constraints={"scope": Scope.OWN}),
            ]),
            Role("senior-engineer", "Senior Engineer", "Technical review and verification", 6, [
                Permission(Action.READ, Resource.TENDER),
                Permission(Action.WRITE, Resource.TENDER),
                Permission(Action.READ, Resource.REPORT),
                Permission(Action.EXECUTE, Resource.TENDER, constraints={"department": "engineering"}),
            ]),
            Role("engineer", "Engineer", "Technical execution", 5, [
                Permission(Action.READ, Resource.TENDER),
                Permission(Action.EXECUTE, Resource.TENDER, constraints={"scope": Scope.OWN, "department": "engineering"}),
                Permission(Action.READ, Resource.REPORT, constraints={"scope": Scope.OWN}),
            ]),
            Role("viewer", "Viewer", "Read-only access", 1, [
                Permission(Action.READ, Resource.TENDER),
                Permission(Action.READ, Resource.REPORT),
            ]),
        ]
        for role in roles:
            self._roles[role.id] = role

        self._policies["default-tenant"] = RBACPolicy(
            "default-tenant", "Default Tenant Policy", "Standard tenant access control",
            rules=[{"role_id": "tenant-admin", "action": "read", "resource": "tender", "order": 1}],
        )
        self._policies["ppr-compliance"] = RBACPolicy(
            "ppr-compliance", "PPR Compliance Policy", "Compliance verification controls",
            rules=[
                {"role_id": "compliance-officer", "action": "write", "resource": "tender", "condition": "hasPPRComplianceVerification", "order": 1},
                {"role_id": "compliance-officer", "action": "read", "resource": "report", "constraints": {"scope": "organization", "department": "compliance"}, "order": 2},
            ],
        )

    def get_role(self, role_id: str) -> Optional[Role]:
        return self._roles.get(role_id)

    def assign_role(self, user_id: str, tenant_id: str, role_id: str, granted_by: str = "", expires_at: Optional[datetime] = None) -> bool:
        if role_id not in self._roles:
            return False
        user_role = UserRole(user_id=user_id, tenant_id=tenant_id, role_id=role_id, granted_by=granted_by, expires_at=expires_at)
        self._user_roles.setdefault(user_id, []).append(user_role)
        return True

    def remove_role(self, user_id: str, role_id: str) -> bool:
        roles = self._user_roles.get(user_id, [])
        for i, ur in enumerate(roles):
            if ur.role_id == role_id:
                roles.pop(i)
                return True
        return False

    def get_user_roles(self, user_id: str) -> List[UserRole]:
        return self._user_roles.get(user_id, [])

    def get_user_permissions(self, user_id: str, tenant_id: Optional[str] = None) -> List[Permission]:
        permissions: Set[Permission] = set()
        for ur in self.get_user_roles(user_id):
            if tenant_id and ur.tenant_id != tenant_id:
                continue
            if not ur.is_active or (ur.expires_at and ur.expires_at < datetime.utcnow()):
                continue
            role = self._roles.get(ur.role_id)
            if role:
                for p in role.permissions:
                    permissions.add(p)
        return list(permissions)

    def can(self, user_id: str, action: Action, resource: Resource, context: Optional[Dict[str, Any]] = None) -> bool:
        for ur in self.get_user_roles(user_id):
            role = self._roles.get(ur.role_id)
            if not role:
                continue
            for perm in role.permissions:
                if perm.action != action or perm.resource != resource:
                    continue
                if self._evaluate(perm, context):
                    return True
        return False

    def _evaluate(self, perm: Permission, context: Optional[Dict[str, Any]]) -> bool:
        if not context:
            return True
        if perm.constraints:
            scope = perm.constraints.get("scope")
            if scope == Scope.OWN and context.get("user_id") != context.get("target_user_id"):
                return False
            if scope == Scope.TEAM and context.get("user_id") not in context.get("team_members", []):
                return False
            dept = perm.constraints.get("department")
            if dept and context.get("department") != dept:
                return False
        if perm.condition:
            return self._evaluate_condition(perm.condition, context)
        return True

    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        checks = {
            "hasPPRCompliance": lambda: True,
            "canUploadComplianceDocs": lambda: True,
            "hasPPRComplianceVerification": lambda: True,
        }
        return checks.get(condition, lambda: True)()


rbac_service = RBACService()
