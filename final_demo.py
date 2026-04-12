import os

# Bug 1: Hardcoded secret
DB_PASSWORD = "admin1234secret"

# Bug 2: SQL Injection  
def get_user(user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"
    return db.execute(query)

# Bug 3: Nested loop O(n2)
def find_pairs(items):
    result = []
    for x in items:
        for y in items:
            result.append((x, y))
    return result

# Bug 4: Bare except
def risky():
    try:
        do_something()
    except:
        pass

print("debug")# retrigger
