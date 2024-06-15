import psutil
import pygetwindow as gw
import time
import threading
import tkinter as tk
from tkinter import simpledialog, messagebox
import winreg

# Registry path
REG_PATH = r"Software\WindowMonitor"

def create_registry_key():
    """Create registry key if it does not exist."""
    try:
        winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_PATH)
    except Exception as e:
        print(f"Error creating registry key: {e}")

def save_to_registry(profile_name, process_name, window_titles):
    """Save profile to registry."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_WRITE) as key:
            winreg.SetValueEx(key, f"{profile_name}_process", 0, winreg.REG_SZ, process_name)
            winreg.SetValueEx(key, f"{profile_name}_windows", 0, winreg.REG_SZ, ",".join(window_titles))
    except Exception as e:
        print(f"Error saving to registry: {e}")

def load_from_registry(profile_name):
    """Load profile from registry."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_READ) as key:
            process_name = winreg.QueryValueEx(key, f"{profile_name}_process")[0]
            window_titles = winreg.QueryValueEx(key, f"{profile_name}_windows")[0].split(",")
            return process_name, window_titles
    except Exception as e:
        print(f"Error loading from registry: {e}")
        return "", []

def delete_from_registry(profile_name):
    """Delete profile from registry."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_WRITE) as key:
            winreg.DeleteValue(key, f"{profile_name}_process")
            winreg.DeleteValue(key, f"{profile_name}_windows")
    except Exception as e:
        print(f"Error deleting from registry: {e}")

def suspend_process(pid):
    """Suspend the process with the given pid."""
    global p
    p.suspend()

def resume_process(pid):
    """Resume the process with the given pid."""
    global p
    p.resume()

def get_process_pid_by_name(name):
    """Get process ID by name."""
    for proc in psutil.process_iter(['name', 'pid']):
        if proc.info['name'].lower() == name.lower():
            return proc.info['pid']
    return None

def is_window_in_foreground(window_titles):
    """Check if any of the windows with the specified titles are in the foreground."""
    active_window = gw.getActiveWindow()
    if active_window is not None:
        for title in window_titles:
            if title.lower() in active_window.title.lower():
                return True
    return False

def main_loop(process_name, window_titles):
    global monitoring
    pid = get_process_pid_by_name(process_name)
    
    if pid is None:
        print(f"Process {process_name} not found.")
        return

    print(f"Monitoring process {process_name} with PID {pid}.")
    global p
    p = psutil.Process(pid)
    try:
        while monitoring:
            if is_window_in_foreground(window_titles):
                suspend_process(pid)
            else:
                resume_process(pid)
            time.sleep(0.01)
    except KeyboardInterrupt:
        print("Program terminated.")

def save_profile():
    profile_name = simpledialog.askstring("Save Profile", "Enter profile name:")
    if profile_name:
        process_name = process_entry.get()
        window_titles = [title.strip() for title in windows_entry.get().split(",")]
        save_to_registry(profile_name, process_name, window_titles)
        profiles_menu.add_command(label=profile_name, command=lambda: load_profile(profile_name))
        messagebox.showinfo("Save Profile", f"Profile '{profile_name}' saved successfully!")

def load_profile(profile_name):
    global current_profile
    process_name, window_titles = load_from_registry(profile_name)
    process_entry.delete(0, tk.END)
    process_entry.insert(0, process_name)
    windows_entry.delete(0, tk.END)
    windows_entry.insert(0, ",".join(window_titles))
    current_profile = profile_name
    messagebox.showinfo("Load Profile", f"Profile '{profile_name}' loaded successfully!")

def delete_profile():
    global current_profile
    if current_profile:
        delete_from_registry(current_profile)
        profiles_menu.delete(current_profile)
        process_entry.delete(0, tk.END)
        windows_entry.delete(0, tk.END)
        current_profile = None
        messagebox.showinfo("Delete Profile", "Profile deleted successfully!")
    else:
        messagebox.showwarning("Delete Profile", "No profile selected to delete.")

def start_monitoring():
    global monitoring
    monitoring = True
    process_name = process_entry.get()
    window_titles = [title.strip() for title in windows_entry.get().split(",")]
    monitor_thread = threading.Thread(target=main_loop, args=(process_name, window_titles))
    monitor_thread.start()
    start_button.grid_forget()
    stop_button.grid(row=3, column=1, padx=10, pady=5)

def stop_monitoring():
    global monitoring
    monitoring = False
    stop_button.grid_forget()
    start_button.grid(row=3, column=1, padx=10, pady=5)

# Create registry key if it doesn't exist
create_registry_key()

# GUI setup
root = tk.Tk()
root.title("Window Monitor")

tk.Label(root, text="Process Name (e.g. \"deadcells.exe\") :").grid(row=0, column=0, padx=10, pady=5)
process_entry = tk.Entry(root)
process_entry.grid(row=0, column=1, padx=10, pady=5)

tk.Label(root, text="Window Titles ( comma separated for multiple Titles (e.g. \"main.py - Notepad,Windows PowerShell\") ):").grid(row=1, column=0, padx=10, pady=5)
windows_entry = tk.Entry(root)
windows_entry.grid(row=1, column=1, padx=10, pady=5)

tk.Button(root, text="Save Profile", command=save_profile).grid(row=2, column=0, padx=10, pady=5)
start_button = tk.Button(root, text="Start Monitoring", command=start_monitoring)
start_button.grid(row=2, column=1, padx=10, pady=10)
stop_button = tk.Button(root, text="Stop Monitoring", command=stop_monitoring)
delete_button = tk.Button(root, text="Delete Profile", command=delete_profile)
delete_button.grid(row=3, column=0, padx=10, pady=5)

menubar = tk.Menu(root)
root.config(menu=menubar)
profiles_menu = tk.Menu(menubar, tearoff=0)
menubar.add_cascade(label="Profiles", menu=profiles_menu)

current_profile = None

# Load existing profiles
try:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_READ) as key:
        index = 0
        while True:
            try:
                profile_key = winreg.EnumValue(key, index)[0]
                if profile_key.endswith("_process"):
                    profile_name = profile_key[:-8]
                    profiles_menu.add_command(label=profile_name, command=lambda p=profile_name: load_profile(p))
                index += 1
            except OSError:
                break
except Exception as e:
    print(f"Error loading profiles: {e}")

root.mainloop()
