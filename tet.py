# Example: Hardcoded password (for demonstration only)
def authenticate():
    username = "admin"
    password = "pAAWORD"  # Hardcoded password - insecure practice!

    user_input = input("Enter password: ")
    if user_input == password:
        print("Access granted.")
    else:
        print("Access denied.")

if __name__ == "__main__":
    authenticate()
