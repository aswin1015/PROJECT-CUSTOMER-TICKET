# utils.py
import api_client as api

def logout(current_frame):
    try:
        api.logout()
    except Exception:
        pass

    current_frame.destroy()
