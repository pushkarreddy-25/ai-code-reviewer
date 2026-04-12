DB_PASSWORD = "supersecret123"

def get_user(id):
    q = f"SELECT * FROM users WHERE id = {id}"
    return db.execute(q)

def slow(items):
    for x in items:
        for y in items:
            print(x, y)
