#!/usr/bin/env python3
"""CLI helper to create or import users into the local SQLite user DB."""
import argparse
import getpass

from users import create_user, import_password_hash, list_users


def main():
    parser = argparse.ArgumentParser(
        description="Create or import users into app user DB"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_create = sub.add_parser("create", help="Create user with plaintext password")
    p_create.add_argument("username")
    p_create.add_argument("--name")
    p_create.add_argument("--email")
    p_create.add_argument("--phone")
    p_create.add_argument("--role", default="user")

    p_import = sub.add_parser("import", help="Import a precomputed pbkdf2 hash")
    p_import.add_argument("username")
    p_import.add_argument("hash")
    p_import.add_argument("--name")
    p_import.add_argument("--email")
    p_import.add_argument("--phone")
    p_import.add_argument("--role", default="user")

    sub.add_parser("list", help="List users")

    args = parser.parse_args()
    if args.cmd == "create":
        pwd = getpass.getpass("Password: ")
        pwd2 = getpass.getpass("Confirm password: ")
        if pwd != pwd2:
            print("Passwords do not match")
            return
        user = create_user(
            args.username,
            password=pwd,
            name=args.name,
            email=args.email,
            phone=args.phone,
            role=args.role,
        )
        print("Created user:", user)
    elif args.cmd == "import":
        user = import_password_hash(
            args.username,
            args.hash,
            name=args.name,
            email=args.email,
            phone=args.phone,
            role=args.role,
        )
        print("Imported user:", user)
    elif args.cmd == "list":
        for u in list_users():
            print(u)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
