DB_PASSWORD = "supersecret123"
MAX_CARTESIAN_PRINT_ITEMS = 100

def get_user(id):
    q = f"SELECT * FROM users WHERE id = {id}"
    return db.execute(q)

def slow(items):
    """Print the Cartesian product of a small collection of items."""
    if hasattr(items, "__len__") and len(items) > MAX_CARTESIAN_PRINT_ITEMS:
        raise ValueError(
            f"Refusing to print Cartesian product for more than "
            f"{MAX_CARTESIAN_PRINT_ITEMS} items"
        )
    for x in items:
        for y in items:
            print(x, y)
