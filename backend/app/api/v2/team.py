"""Phase 2: Team Management Endpoints"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from pydantic import BaseModel, EmailStr
from datetime import datetime
import uuid

from app.db.base import get_async_session
from app.core.security import get_current_user
from app.models.phase2 import Team, TeamMember, TeamRole

router = APIRouter(prefix="/team", tags=["team"])


class TeamMemberRole(str):
    """Team member roles"""
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class TeamMemberBase(BaseModel):
    """Base team member schema"""
    email: EmailStr
    full_name: str
    role: str  # owner, admin, member, viewer
    department: Optional[str] = None
    phone: Optional[str] = None


class TeamMemberCreate(TeamMemberBase):
    """Create team member"""
    pass


class TeamMemberUpdate(BaseModel):
    """Update team member"""
    full_name: Optional[str] = None
    role: Optional[str] = None
    department: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None


class TeamMemberResponse(TeamMemberBase):
    """Team member response"""
    id: str
    tenant_id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TeamResponse(BaseModel):
    """Team response"""
    id: str
    tenant_id: str
    name: str
    max_members: int = 50
    member_count: int = 0
    members: List[TeamMemberResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


@router.get("", response_model=TeamResponse)
async def get_team(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Get team information for current tenant."""
    try:
        tenant_id = current_user.get("tenant_id")
        if not tenant_id:
            raise HTTPException(status_code=400, detail="Tenant ID not found in user context")

        result = await db.execute(select(Team).where(Team.tenant_id == tenant_id))
        team = result.scalar_one_or_none()

        if not team:
            team_id = str(uuid.uuid4())
            team = Team(id=team_id, tenant_id=tenant_id, name="Default Team", max_members=50)
            db.add(team)
            await db.commit()
            await db.refresh(team)

        members = (
            await db.execute(select(TeamMember).where(TeamMember.tenant_id == tenant_id))
        ).scalars().all()

        return TeamResponse(
            id=team.id,
            tenant_id=team.tenant_id,
            name=team.name,
            max_members=team.max_members,
            member_count=len(members),
            members=[TeamMemberResponse.model_validate(m) for m in members],
            created_at=team.created_at,
            updated_at=team.updated_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/members", response_model=List[TeamMemberResponse])
async def list_team_members(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    role: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """List all team members."""
    try:
        tenant_id = current_user.get("tenant_id")
        if not tenant_id:
            raise HTTPException(status_code=400, detail="Tenant ID not found in user context")

        query = select(TeamMember).where(TeamMember.tenant_id == tenant_id)
        if role:
            query = query.where(TeamMember.role == role)
        if is_active is not None:
            query = query.where(TeamMember.is_active == is_active)

        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/members", response_model=TeamMemberResponse, status_code=status.HTTP_201_CREATED)
async def invite_team_member(
    member: TeamMemberCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Invite a new team member."""
    try:
        tenant_id = current_user.get("tenant_id")
        if not tenant_id:
            raise HTTPException(status_code=400, detail="Tenant ID not found in user context")

        current_role = current_user.get("role", "").lower()
        if current_role not in {"admin", "owner"}:
            raise HTTPException(status_code=403, detail="Only admins can invite team members")

        member_id = str(uuid.uuid4())
        new_member = TeamMember(
            id=member_id,
            tenant_id=tenant_id,
            email=member.email,
            full_name=member.full_name,
            role=TeamRole(member.role),
            department=member.department,
            phone=member.phone,
            is_active=True,
        )
        db.add(new_member)
        await db.commit()
        await db.refresh(new_member)

        # Audit log
        try:
            from app.services.audit_service import log_audit_event
            from app.db.base import get_session_factory

            async with get_session_factory()() as audit_db:
                await log_audit_event(
                    audit_db,
                    tenant_id=tenant_id,
                    actor_id=current_user["id"],
                    actor_type="user",
                    action="invite_team_member",
                    resource_type="team_member",
                    resource_id=member_id,
                    status="success",
                    metadata={"email": member.email, "role": member.role},
                )
                await audit_db.commit()
        except Exception as e:
            import logging
            logging.warning(f"Audit logging failed: {e}")

        return TeamMemberResponse.model_validate(new_member)
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/members/{member_id}", response_model=TeamMemberResponse)
async def get_team_member(
    member_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Get team member by ID."""
    try:
        tenant_id = current_user.get("tenant_id")
        result = await db.execute(
            select(TeamMember).where(
                and_(TeamMember.id == member_id, TeamMember.tenant_id == tenant_id)
            )
        )
        member = result.scalar_one_or_none()
        if not member:
            raise HTTPException(status_code=404, detail="Team member not found")
        return TeamMemberResponse.model_validate(member)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/members/{member_id}", response_model=TeamMemberResponse)
async def update_team_member(
    member_id: str,
    member_update: TeamMemberUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Update a team member."""
    try:
        current_role = current_user.get("role", "").lower()
        if current_role not in {"admin", "owner"}:
            raise HTTPException(status_code=403, detail="Only admins can update team members")

        tenant_id = current_user.get("tenant_id")
        result = await db.execute(
            select(TeamMember).where(
                and_(TeamMember.id == member_id, TeamMember.tenant_id == tenant_id)
            )
        )
        member = result.scalar_one_or_none()
        if not member:
            raise HTTPException(status_code=404, detail="Team member not found")

        update_data = member_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(member, key, value)

        await db.commit()
        await db.refresh(member)
        return TeamMemberResponse.model_validate(member)
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_team_member(
    member_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Remove a team member."""
    try:
        current_role = current_user.get("role", "").lower()
        if current_role not in {"admin", "owner"}:
            raise HTTPException(status_code=403, detail="Only admins can remove team members")

        tenant_id = current_user.get("tenant_id")
        result = await db.execute(
            select(TeamMember).where(
                and_(TeamMember.id == member_id, TeamMember.tenant_id == tenant_id)
            )
        )
        member = result.scalar_one_or_none()
        if not member:
            raise HTTPException(status_code=404, detail="Team member not found")

        await db.delete(member)
        await db.commit()
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
