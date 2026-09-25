"""
Migrate project-scoped editor/viewer roles to stage-scoped roles.

PROJECT_EDITOR and PROJECT_VIEWER previously granted access to the
whole project.

They are migrated to equivalent STAGE-scoped assignments for every
currently enabled stage.

Rules
-----
- PROJECT_ADMIN remains project-scoped.
- BUSINESS_CASE / DESIGN / CONSTRUCTION are migrated only when their
  ProjectStageConfig is currently enabled.
- RECURRING is migrated only for projects whose project_class is
  RECURRING.
- Disabled historical stage instances are not granted access.
- Existing stage assignments are preserved/reactivated through the
  unique user/role/scope constraint.
- Old PROJECT_EDITOR / PROJECT_VIEWER assignments are deactivated.
- SUPER_ADMIN is not changed.
"""

from alembic import op
import sqlalchemy as sa


revision = "207e9e8c8806"
down_revision = "pics01_add_acceptance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # PROJECT_EDITOR
    #
    # Convert each active project-scoped editor assignment into
    # stage-scoped editor assignments for every currently enabled stage.
    #
    # For BUSINESS_CASE / DESIGN / CONSTRUCTION, enabled state comes
    # from project_stage_config.
    #
    # RECURRING has no ProjectStageConfig row, so it is enabled when
    # the project itself is of class RECURRING.
    # ------------------------------------------------------------------

    op.execute(
        sa.text(
            """
            INSERT INTO user_roles (
                id,
                user_id,
                role_id,
                scope_type,
                scope_id,
                is_active,
                created_on,
                updated_on
            )
            SELECT
                gen_random_uuid(),
                ur.user_id,
                ur.role_id,
                'STAGE',
                psi.id,
                TRUE,
                NOW(),
                NOW()
            FROM user_roles ur
            JOIN roles r
              ON r.id = ur.role_id
            JOIN project_stage_instances psi
              ON psi.project_id = ur.scope_id
            JOIN project p
              ON p.id = psi.project_id
            WHERE ur.scope_type = 'PROJECT'
              AND ur.is_active = TRUE
              AND r.name = 'PROJECT_EDITOR'
              AND (
                    (
                        psi.stage::text IN (
                            'BUSINESS_CASE',
                            'DESIGN',
                            'CONSTRUCTION'
                        )
                        AND EXISTS (
                            SELECT 1
                            FROM project_stage_config psc
                            WHERE psc.project_id = psi.project_id
                              AND psc.stage::text = psi.stage::text
                              AND psc.enabled = TRUE
                        )
                    )
                    OR
                    (
                        psi.stage::text = 'RECURRING'
                        AND p.project_class::text = 'RECURRING'
                    )
              )
            ON CONFLICT (
                user_id,
                role_id,
                scope_type,
                scope_id
            ) WHERE scope_id IS NOT NULL
            DO UPDATE SET
                is_active = TRUE,
                updated_on = NOW()
            """
        )
    )

    # ------------------------------------------------------------------
    # PROJECT_VIEWER
    #
    # Same conversion as PROJECT_EDITOR.
    # ------------------------------------------------------------------

    op.execute(
        sa.text(
            """
            INSERT INTO user_roles (
                id,
                user_id,
                role_id,
                scope_type,
                scope_id,
                is_active,
                created_on,
                updated_on
            )
            SELECT
                gen_random_uuid(),
                ur.user_id,
                ur.role_id,
                'STAGE',
                psi.id,
                TRUE,
                NOW(),
                NOW()
            FROM user_roles ur
            JOIN roles r
              ON r.id = ur.role_id
            JOIN project_stage_instances psi
              ON psi.project_id = ur.scope_id
            JOIN project p
              ON p.id = psi.project_id
            WHERE ur.scope_type = 'PROJECT'
              AND ur.is_active = TRUE
              AND r.name = 'PROJECT_VIEWER'
              AND (
                    (
                        psi.stage::text IN (
                            'BUSINESS_CASE',
                            'DESIGN',
                            'CONSTRUCTION'
                        )
                        AND EXISTS (
                            SELECT 1
                            FROM project_stage_config psc
                            WHERE psc.project_id = psi.project_id
                              AND psc.stage::text = psi.stage::text
                              AND psc.enabled = TRUE
                        )
                    )
                    OR
                    (
                        psi.stage::text = 'RECURRING'
                        AND p.project_class::text = 'RECURRING'
                    )
              )
            ON CONFLICT (
                user_id,
                role_id,
                scope_type,
                scope_id
            ) WHERE scope_id IS NOT NULL
            DO UPDATE SET
                is_active = TRUE,
                updated_on = NOW()
            """
        )
    )

    # ------------------------------------------------------------------
    # Deactivate the old project-scoped editor/viewer assignments.
    #
    # PROJECT_ADMIN is deliberately untouched.
    #
    # This also removes access for any old project-scoped editor/viewer
    # assignment belonging to a project that has no currently enabled
    # stage. Such a user should no longer have project membership.
    # ------------------------------------------------------------------

    op.execute(
        sa.text(
            """
            UPDATE user_roles ur
            SET
                is_active = FALSE,
                updated_on = NOW()
            FROM roles r
            WHERE ur.role_id = r.id
              AND ur.scope_type = 'PROJECT'
              AND ur.is_active = TRUE
              AND r.name IN (
                  'PROJECT_EDITOR',
                  'PROJECT_VIEWER'
              )
            """
        )
    )


# def downgrade() -> None:
#     # ------------------------------------------------------------------
#     # Recreate PROJECT_EDITOR / PROJECT_VIEWER project-scoped access
#     # from active stage-scoped assignments.
#     #
#     # Each role is handled independently.
#     #
#     # Therefore, if a user has:
#     #   - EDITOR on DESIGN
#     #   - VIEWER on CONSTRUCTION
#     #
#     # the downgrade recreates BOTH project-level roles.
#     #
#     # This is the closest representation of the old project-scoped
#     # model because the old model did not retain stage-level detail.
#     # ------------------------------------------------------------------

#     op.execute(
#         sa.text(
#             """
#             INSERT INTO user_roles (
#                 id,
#                 user_id,
#                 role_id,
#                 scope_type,
#                 scope_id,
#                 is_active,
#                 created_on,
#                 updated_on
#             )
#             SELECT DISTINCT
#                 gen_random_uuid(),
#                 ur.user_id,
#                 r.id,
#                 'PROJECT',
#                 psi.project_id,
#                 TRUE,
#                 NOW(),
#                 NOW()
#             FROM user_roles ur
#             JOIN roles r
#               ON r.id = ur.role_id
#             JOIN project_stage_instances psi
#               ON psi.id = ur.scope_id
#             WHERE ur.scope_type = 'STAGE'
#               AND ur.is_active = TRUE
#               AND r.name IN (
#                   'PROJECT_EDITOR',
#                   'PROJECT_VIEWER'
#               )
#             ON CONFLICT (
#                 user_id,
#                 role_id,
#                 scope_type,
#                 scope_id
#             )
#             DO UPDATE SET
#                 is_active = TRUE,
#                 updated_on = NOW()
#             """
#         )
#     )

#     # ------------------------------------------------------------------
#     # Remove stage-scoped editor/viewer assignments.
#     #
#     # After downgrade, editor/viewer access must once again be
#     # represented at PROJECT scope.
#     #
#     # PROJECT_ADMIN and all unrelated stage roles are untouched.
#     # ------------------------------------------------------------------

#     op.execute(
#         sa.text(
#             """
#             UPDATE user_roles ur
#             SET
#                 is_active = FALSE,
#                 updated_on = NOW()
#             FROM roles r
#             WHERE ur.role_id = r.id
#               AND ur.scope_type = 'STAGE'
#               AND ur.is_active = TRUE
#               AND r.name IN (
#                   'PROJECT_EDITOR',
#                   'PROJECT_VIEWER'
#               )
#             """
#         )
#     )


def downgrade() -> None:
    """ 
    This migration intentionally does not attempt to reverse the stage-role
    conversion.

    The upgrade converts project-scoped PROJECT_EDITOR / PROJECT_VIEWER
    assignments into stage-scoped assignments. After the migration, stage
    assignments may also be created or modified intentionally by users.

    Without a migration-specific marker, it is impossible to distinguish:
    - stage assignments created by this migration
    - stage assignments created intentionally after the migration

    Automatically converting all active stage assignments back to project
    scope would therefore risk restoring access that was intentionally
    removed or changing intentionally granular stage permissions.

    A downgrade should be performed through a dedicated, reviewed data
    migration if rollback is ever required.
    """
    pass

