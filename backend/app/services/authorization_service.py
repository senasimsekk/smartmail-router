ROLE_POLICIES = {
    "admin": {
        "label": "Admin",
        "department": None,
        "permissions": [
            "import_email",
            "process_email",
            "upload_attachment",
            "approve_routing",
            "route_email",
            "correct_routing",
            "create_feedback",
            "view_dashboard",
            "view_training_data",
        ],
    },
    "operator": {
        "label": "Operatör",
        "department": None,
        "permissions": [
            "import_email",
            "process_email",
            "upload_attachment",
            "approve_routing",
            "route_email",
            "correct_routing",
            "create_feedback",
            "view_dashboard",
            "view_training_data",
        ],
    },
    "department_user": {
        "label": "Birim Kullanıcısı",
        "department": "İlgili Uzman Daire",
        "permissions": [
            "view_dashboard",
            "view_training_data",
        ],
    },
    "viewer": {
        "label": "İzleyici",
        "department": None,
        "permissions": [
            "view_dashboard",
        ],
    },
}


def get_available_roles() -> list[dict]:
    return [
        {
            "role": role,
            "label": policy["label"],
            "department": policy["department"],
            "permissions": policy["permissions"],
        }
        for role, policy in ROLE_POLICIES.items()
    ]


def role_has_permission(role: str, permission: str) -> bool:
    policy = ROLE_POLICIES.get(role)

    if not policy:
        return False

    return permission in policy["permissions"]
