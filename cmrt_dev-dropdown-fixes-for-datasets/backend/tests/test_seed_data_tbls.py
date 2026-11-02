"""
Test seed data for permissions
"""
from uuid import uuid4
from datetime import datetime
from typing import List


def get_test_permissions_data() -> List[dict]:
    """Get test permission data."""
    return [
        {
            "id": uuid4(),
            "name": "create_any",
            "description": "Create any resource",
            "created_on": datetime.utcnow(),
        },
        {
            "id": uuid4(),
            "name": "read_any",
            "description": "Read any resource",
            "created_on": datetime.utcnow(),
        },
        {
            "id": uuid4(),
            "name": "update_any",
            "description": "Update any resource",
            "created_on": datetime.utcnow(),
        },
        {
            "id": uuid4(),
            "name": "delete_any",
            "description": "Delete any resource",
            "created_on": datetime.utcnow(),
        },
        {
            "id": uuid4(),
            "name": "read_own",
            "description": "Read own resource",
            "created_on": datetime.utcnow(),
        },
    ]

def get_test_roles_data() -> List[dict]:
    """Get test role data."""
    return [
        {
            "id": uuid4(),
            "name": "Admin",
            "description": "Administrator",
            "is_active": True,
            "created_on": datetime.utcnow(),
        },
        {
            "id": uuid4(),
            "name": "Editor",
            "description": "Editor",
            "is_active": True,
            "created_on": datetime.utcnow(),
        },
        {
            "id": uuid4(),
            "name": "Viewer",
            "description": "Viewer",
            "is_active": True,
            "created_on": datetime.utcnow(),
        },
    ]


def get_test_role_permissions_data(roles_data: List[dict] = None, permissions_data: List[dict] = None) -> List[dict]:
    """Get test role-permission relationship data.
    
    If roles_data and permissions_data are provided, uses those IDs.
    Otherwise generates sample relationships.
    """
    if roles_data is None:
        roles_data = get_test_roles_data()
    if permissions_data is None:
        permissions_data = get_test_permissions_data()
    
    admin_role = roles_data[0]  # Admin
    editor_role = roles_data[1]  # Editor
    viewer_role = roles_data[2]  # Viewer
    
    create_perm = permissions_data[0]  # create_any
    read_perm = permissions_data[1]  # read_any
    update_perm = permissions_data[2]  # update_any
    delete_perm = permissions_data[3]  # delete_any
    read_own_perm = permissions_data[4]  # read_own
    
    return [
        {
            "id": uuid4(),
            "role_id": admin_role["id"],
            "permission_id": create_perm["id"],
            "created_on": datetime.utcnow(),
        },
        {
            "id": uuid4(),
            "role_id": admin_role["id"],
            "permission_id": read_perm["id"],
            "created_on": datetime.utcnow(),
        },
        {
            "id": uuid4(),
            "role_id": admin_role["id"],
            "permission_id": update_perm["id"],
            "created_on": datetime.utcnow(),
        },
        {
            "id": uuid4(),
            "role_id": admin_role["id"],
            "permission_id": delete_perm["id"],
            "created_on": datetime.utcnow(),
        },
        {
            "id": uuid4(),
            "role_id": editor_role["id"],
            "permission_id": read_perm["id"],
            "created_on": datetime.utcnow(),
        },
        {
            "id": uuid4(),
            "role_id": editor_role["id"],
            "permission_id": update_perm["id"],
            "created_on": datetime.utcnow(),
        },
        {
            "id": uuid4(),
            "role_id": viewer_role["id"],
            "permission_id": read_perm["id"],
            "created_on": datetime.utcnow(),
        },
        {
            "id": uuid4(),
            "role_id": viewer_role["id"],
            "permission_id": read_own_perm["id"],
            "created_on": datetime.utcnow(),
        },
    ]


def get_test_user_roles_data(users_data: List[dict] = None, roles_data: List[dict] = None) -> List[dict]:
    """Get test user-role relationship data.
    
    If users_data and roles_data are provided, uses those IDs.
    Otherwise generates sample relationships.
    """
    if users_data is None:
        users_data = get_test_users_data()
    if roles_data is None:
        roles_data = get_test_roles_data()
    
    user1 = users_data[0]  # user1@example.com
    user2 = users_data[1]  # user2@example.com
    user3 = users_data[2]  # user3@example.com (inactive)
    
    admin_role = roles_data[0]  # Admin
    editor_role = roles_data[1]  # Editor
    viewer_role = roles_data[2]  # Viewer
    
    return [
        {
            "id": uuid4(),
            "user_id": user1["id"],
            "role_id": admin_role["id"],
            "scope_type": None,
            "scope_id": None,
            "is_active": True,
            "created_on": datetime.utcnow(),
        },
        {
            "id": uuid4(),
            "user_id": user2["id"],
            "role_id": editor_role["id"],
            "scope_type": None,
            "scope_id": None,
            "is_active": True,
            "created_on": datetime.utcnow(),
        },
        {
            "id": uuid4(),
            "user_id": user3["id"],
            "role_id": viewer_role["id"],
            "scope_type": None,
            "scope_id": None,
            "is_active": False,
            "created_on": datetime.utcnow(),
        },
    ]


def get_test_users_data() -> List[dict]:
    """Get test user data."""
    return [
        {
            "id": uuid4(),
            "email": "user1@example.com",
            "username": "user1",
            "first_name": "User",
            "last_name": "One",
            "is_active": True,
            "created_on": datetime.utcnow(),
        },
        {
            "id": uuid4(),
            "email": "user2@example.com",
            "username": "user2",
            "first_name": "User",
            "last_name": "Two",
            "is_active": True,
            "created_on": datetime.utcnow(),
        },
        {
            "id": uuid4(),
            "email": "user3@example.com",
            "username": "user3",
            "first_name": "User",
            "last_name": "Three",
            "is_active": False,
            "created_on": datetime.utcnow(),
        },
    ]
