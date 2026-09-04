"""ARIA verification script — checks all modules import correctly."""
import sys
print(f"Python: {sys.version}")
print()

results = []

def check(name, fn):
    try:
        fn()
        results.append((True, name, ""))
        print(f"  [PASS] {name}")
    except Exception as e:
        results.append((False, name, str(e)))
        print(f"  [FAIL] {name}: {e}")

# Config
check("config", lambda: __import__("config").load_config())

# Core modules
check("voice_input",    lambda: __import__("core.voice_input", fromlist=["VoiceInput"]).VoiceInput())
check("voice_output",   lambda: __import__("core.voice_output", fromlist=["VoiceOutput"]).VoiceOutput())
check("ai_brain",       lambda: __import__("core.ai_brain", fromlist=["AIBrain"]).AIBrain(""))
check("hotkey_handler", lambda: __import__("core.hotkey_handler", fromlist=["HotkeyHandler"]).HotkeyHandler())

# Actions
check("app_control",    lambda: __import__("actions.app_control", fromlist=["open_app"]))
check("media_control",  lambda: __import__("actions.media_control", fromlist=["play_pause"]))
check("clipboard",      lambda: __import__("actions.clipboard_control", fromlist=["copy_to_clipboard"]))
check("system_control", lambda: print("  volume:", __import__("actions.system_control", fromlist=["get_volume_level"]).get_volume_level()))
check("web_control",    lambda: __import__("actions.web_control", fromlist=["search_web"]))
check("file_control",   lambda: __import__("actions.file_control", fromlist=["open_folder"]))
check("timer_control",  lambda: __import__("actions.timer_control", fromlist=["TimerManager"]).TimerManager())
check("weather",        lambda: __import__("actions.weather", fromlist=["get_weather"]))
check("screenshot",     lambda: __import__("actions.screenshot", fromlist=["take_screenshot"]))
check("email_control",   lambda: __import__("actions.email_control", fromlist=["compose_email"]))
check("tools_extra",     lambda: __import__("actions.tools_extra", fromlist=["calculate_math"]))
check("n8n_control",     lambda: __import__("actions.n8n_control", fromlist=["query_n8n"]))
check("linkedin_control",lambda: __import__("actions.linkedin_control", fromlist=["post_to_linkedin"]))
check("social_poster",   lambda: __import__("actions.social_poster", fromlist=["schedule_linkedin_post"]))

# UI (skip rendering, just check imports)
check("ui.app_window",  lambda: __import__("ui.app_window", fromlist=["AppWindow"]))

print()
passed = sum(1 for ok, _, _ in results if ok)
failed = sum(1 for ok, _, _ in results if not ok)
print(f"Results: {passed} passed, {failed} failed")
if failed == 0:
    print("ARIA is READY TO LAUNCH!")
else:
    print("Fix the failed modules above before launching.")
