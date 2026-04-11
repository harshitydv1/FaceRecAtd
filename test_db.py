import sys, os
from PIL import Image
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from core.database import init_db, add_user, get_all_users, deactivate_user, get_today_summary

init_db()

# Insert test user
arr = np.random.rand(128)
add_user("Test Del User", "EMP_DEL", "IT", "employee", arr, "test.jpg")

print("Users before:", len([u for u in get_all_users() if u['is_active']]))
print("Summary before:", get_today_summary())

deactivate_user("EMP_DEL")

print("Users after:", len([u for u in get_all_users() if u['is_active']]))
print("Summary after:", get_today_summary())

