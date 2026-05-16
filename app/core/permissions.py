from fastapi import HTTPException, status

from app.models.user import User, UserRole, UserStatus


class PermissionService:
    @staticmethod
    def ensure_active_user(current_user: User) -> None:
        if not current_user.is_active or current_user.status != UserStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive.",
            )

    @staticmethod
    def ensure_has_role(current_user: User, role: UserRole | str) -> None:
        if not current_user.has_role(role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied.",
            )

    @staticmethod
    def ensure_has_any_role(
        current_user: User,
        roles: list[UserRole | str] | set[UserRole | str],
    ) -> None:
        if not current_user.has_any_role(roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied.",
            )

    @staticmethod
    def ensure_same_school(
        current_user: User,
        resource_school_id: int | None,
    ) -> None:
        if current_user.is_platform_admin:
            return

        if current_user.school_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Current user is not assigned to a school.",
            )

        if resource_school_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Resource is not assigned to a school.",
            )

        if current_user.school_id != resource_school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cross-school access denied.",
            )

    @staticmethod
    def ensure_platform_admin(current_user: User) -> None:
        if not current_user.is_platform_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Platform admin access required.",
            )

    @staticmethod
    def ensure_school_admin(current_user: User) -> None:
        if not current_user.is_school_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="School admin access required.",
            )

    @staticmethod
    def ensure_teacher(current_user: User) -> None:
        if not current_user.is_teacher:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Teacher access required.",
            )

    @staticmethod
    def ensure_student(current_user: User) -> None:
        if not current_user.is_student:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Student access required.",
            )

    @staticmethod
    def ensure_school_admin_or_platform_admin(current_user: User) -> None:
        PermissionService.ensure_has_any_role(
            current_user,
            {
                UserRole.PLATFORM_ADMIN,
                UserRole.SCHOOL_ADMIN,
            },
        )

    @staticmethod
    def ensure_school_staff_or_platform_admin(current_user: User) -> None:
        PermissionService.ensure_has_any_role(
            current_user,
            {
                UserRole.PLATFORM_ADMIN,
                UserRole.SCHOOL_ADMIN,
                UserRole.TEACHER,
            },
        )

    @staticmethod
    def ensure_school_admin_or_teacher(current_user: User) -> None:
        PermissionService.ensure_has_any_role(
            current_user,
            {
                UserRole.PLATFORM_ADMIN,
                UserRole.SCHOOL_ADMIN,
                UserRole.TEACHER,
            },
        )

    @staticmethod
    def ensure_can_teach(current_user: User) -> None:
        PermissionService.ensure_has_any_role(
            current_user,
            {
                UserRole.PLATFORM_ADMIN,
                UserRole.SCHOOL_ADMIN,
                UserRole.TEACHER,
            },
        )

    @staticmethod
    def ensure_user_belongs_to_school(user: User) -> None:
        if user.is_platform_admin:
            if user.school_id is not None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Platform admin cannot belong to a school.",
                )
            return

        if user.school_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="School users must belong to a school.",
            )

    @staticmethod
    def ensure_can_manage_school_user(
        current_user: User,
        target_user: User,
    ) -> None:
        PermissionService.ensure_school_admin_or_platform_admin(current_user)

        if current_user.is_platform_admin:
            return

        if current_user.school_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Current user is not assigned to a school.",
            )

        if target_user.school_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Target user is not assigned to a school.",
            )

        if current_user.school_id != target_user.school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot manage users outside your school.",
            )

    @staticmethod
    def ensure_not_last_school_admin(
        target_user: User,
        active_school_admin_count: int,
    ) -> None:
        if not target_user.is_school_admin:
            return

        if target_user.school_id is None:
            return

        if target_user.is_active and target_user.status == UserStatus.ACTIVE:
            if active_school_admin_count <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Each school must have at least one active school admin.",
                )

    @staticmethod
    def ensure_can_request_erasure(target_user: User) -> None:
        if target_user.status == UserStatus.ANONYMISED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User has already been anonymised.",
            )

        if target_user.status == UserStatus.PENDING_ERASURE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already pending erasure.",
            )

    @staticmethod
    def ensure_can_anonymise(target_user: User) -> None:
        if target_user.status == UserStatus.ANONYMISED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User has already been anonymised.",
            )

        if target_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Active users must be deactivated before anonymisation.",
            )
