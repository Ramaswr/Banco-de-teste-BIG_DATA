#!/usr/bin/env python3
import getpass
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import auth

def main():
    if len(sys.argv) >= 2:
        username = sys.argv[1]
    else:
        username = input("username: ")
    password = getpass.getpass("password: ")
    password2 = getpass.getpass("confirm password: ")
    if password != password2:
        print("passwords do not match")
        return
    try:
        auth.create_user(username, password)
        print("user created at", auth.DB_PATH)
    except Exception as e:
        print("error:", e)

if __name__ == "__main__":
    main()