import PyInstaller.__main__
import os

# 1. Get the exact folder path where this script is sitting
current_folder = os.path.dirname(os.path.abspath(__file__))
script_path = os.path.join(current_folder, "tracker_app.py")

print(f"📁 Looking for script at: {script_path}")

# 2. Check if the file is actually there before trying to build
if not os.path.exists(script_path):
    print(f"❌ Error: 'tracker_app.py' was not found in {current_folder}!")
    print("Please double check that your main script is named exactly 'tracker_app.py'.")
else:
    print("⚙️ Initializing CustomTkinter Executable Compiler...")
    
    # 3. Run the compiler using absolute paths and name the output binary "Time"
    PyInstaller.__main__.run([
        script_path,
        '--name=Time',               # ◄ This line forces the name to be "Time.exe"
        '--onefile',
        '--noconsole',
        '--collect-all', 'customtkinter'
    ])
    
    print("🎉 Finished! Check your local 'dist' folder for Time.exe!")
