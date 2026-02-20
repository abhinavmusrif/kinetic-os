import time
from os_controller.windows_controller import WindowsController

def run_demo() -> None:
    print("Starting Windows Controller demo...")
    wc = WindowsController(allow_os_automation=True)
    
    print("Opening Notepad...")
    wc.open_app("notepad")
    time.sleep(2)
    
    print("Focusing Notepad window...")
    wc.window_manager.focus_window("Notepad")
    time.sleep(1)
    
    print("Typing text via OS Controller...")
    wc.type_text("Hello from Antigravity OS Controller!")
    time.sleep(1)
    
    print("Verifying text appeared (Visual Action)...")
    capture = wc.screen_capture.capture_screen()
    if capture:
        analysis = wc.screen_reader.analyze(capture)
        text_found = False
        for el in analysis.get("elements", []):
            if "Hello" in el.get("label", "") or "Antigravity" in el.get("label", ""):
                text_found = True
                print(f"Verified text visually: '{el['label']}' at bbox {el['bbox']}")
                break
                
        if not text_found:
            print("Could not visually verify text. Maybe OCR missed it or window wasn't captured right.")
    else:
        print("Screen capture failed.")

    print("Closing Notepad safely...")
    wc.input_controller.press_hotkey("alt", "f4")
    time.sleep(1)
    # Don't save dialog usually defaults to 'Save', right arrow goes to 'Don't Save'
    wc.input_controller.press_hotkey("right")
    time.sleep(0.5)
    wc.input_controller.press_hotkey("enter")
    print("Demo complete.")

if __name__ == "__main__":
    run_demo()
