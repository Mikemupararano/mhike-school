from fastapi import HTTPException, status

from app.models.user import User, UserRole, UserStatus


class PermissionService:
    @staticmethod
    def ensure_same_school(current_user: User, resource_school_id: int | None) -> None:
        """
        Platform admins may access across schools.
        All other users are restricted to their own school.
        """
        if current_user.is_platform_admin:
            return

        if current_user.school_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Current user is not assigned to a school.",
            )

        if resource_school_id is None or current_user.school_id != resource_school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cross-school access denied.",
            )

    @staticmethod
    def ensure_school_admin_or_platform_admin(current_user: User) -> None:
        if not (current_user.is_school_admin or current_user.is_platform_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="School admin access required.",
            )

    @staticmethod
    def ensure_school_staff_or_platform_admin(current_user: User) -> None:
        """
        School staff includes school admins and teachers.
        Platform admins are also allowed.
        """
        if not (
            current_user.is_school_admin
            or current_user.is_teacher
            or current_user.is_platform_admin
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="School staff access required.",
            )

    @staticmethod
    def ensure_can_teach(current_user: User) -> None:
        """
        Teaching actions are allowed for teachers, school admins,
        and platform admins.
        """
        if not (current_user.can_teach or current_user.is_platform_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Teaching access required.",
            )

    @staticmethod
    def ensure_active_user(current_user: User) -> None:
        if not current_user.is_active or current_user.status != UserStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive.",
            )

    @staticmethod
    def ensure_user_belongs_to_school(user: User) -> None:
        """
        For this phase of the product:
        - school_admin, teacher, student must belong to a school
        - platform_admin must not belong to a school
        """
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
    def ensure_can_manage_school_user(current_user: User, target_user: User) -> None:
        """
        School admins can manage users in their own school.
        Platform admins can manage any user.
        """
        PermissionService.ensure_school_admin_or_platform_admin(current_user)

        if current_user.is_platform_admin:
            return

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
        """
        Prevent removing/deactivating/anonymising the final active school admin.
        """
        if not target_user.is_school_admin:
            return

        if target_user.school_id is None:
            return

        if active_school_admin_count <= 1 and target_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Each school must have at least one active school admin.",
            )

    @staticmethod
    def ensure_can_request_erasure(target_user: User) -> None:
        """
        Basic guard for GDPR workflow entry.
        """
        if target_user.status == UserStatus.ANONYMISED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User has already been anonymised.",
            )

    @staticmethod
    def ensure_can_anonymise(target_user: User) -> None:
        """
        Basic guard before anonymisation.
        """
        if target_user.status == UserStatus.ANONYMISED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User has already been anonymised.",
            )
