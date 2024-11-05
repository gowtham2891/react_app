import autogen
from openai import OpenAI
from autogen.coding import LocalCommandLineCodeExecutor
from pathlib import Path
import subprocess
import webbrowser
import time
import os
import json
import socket

# Setting up the code executor
workdir = Path(r"C:\Users\Pranjal\Videos\vlm\coding")
workdir.mkdir(exist_ok=True)

# Initialize LocalCommandLineCodeExecutor with execution policies
code_executor = LocalCommandLineCodeExecutor(
    work_dir=workdir,
    timeout=18000000000
)

def check_dependencies():
    """Check if package.json exists and all dependencies are installed"""
    package_json_path = workdir / "package.json"
    node_modules_path = workdir / "node_modules"
    
    if not package_json_path.exists():
        return False
        
    if not node_modules_path.exists():
        return False
        
    try:
        # Read package.json
        with open(package_json_path, 'r') as f:
            package_data = json.load(f)
            
        # Check if all dependencies are installed
        for dep_type in ['dependencies', 'devDependencies']:
            if dep_type in package_data:
                for dep in package_data[dep_type]:
                    dep_path = node_modules_path / dep
                    if not dep_path.exists():
                        return False
        return True
    except Exception as e:
        print(f"Error checking dependencies: {e}")
        return False

def install_missing_dependencies():
    """Install only missing dependencies"""
    try:
        package_json_path = workdir / "package.json"
        if not package_json_path.exists():
            print("Installing base React application...")
            subprocess.run(
                "npx create-vite@latest . --template react-ts -- --yes",
                shell=True,
                cwd=workdir,
                check=True
            )
        
        # Check node_modules
        if not (workdir / "node_modules").exists():
            print("Installing dependencies...")
            subprocess.run(
                "npm install",
                shell=True,
                cwd=workdir,
                check=True
            )
        else:
            print("Dependencies already installed, skipping installation.")
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error installing dependencies: {e}")
        return False

def is_port_in_use(port):
    """Check if a port is in use on Windows"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('localhost', port))
            return False
        except socket.error:
            return True

def start_dev_server():
    """Start the development server"""
    try:
        # Check if port 5173 is in use
        if is_port_in_use(5173):
            print("Development server is already running")
            webbrowser.open('http://localhost:5173')
            return None
        
        # Port is free, start the server
        print("Starting development server...")
        process = subprocess.Popen(
            "npm run dev",
            shell=True,
            cwd=workdir,
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
        
        # Wait for server to start
        time.sleep(3)
        
        # Open the default browser
        webbrowser.open('http://localhost:5173')
        
        return process
    except Exception as e:
        print(f"Error starting development server: {e}")
        return None

def main():
    config_list = autogen.config_list_from_json(
        env_or_file=r"C:\Users\Pranjal\Videos\vlm\OAI_CONFIG_LIST.json"
    )

    assistant = autogen.AssistantAgent(
        name="Coder",
        system_message="""
        Always,And must to save the code in a file before executing it, put # filename: <filename> inside the code block as the first line. Don't include multiple code blocks in one response. Do not ask users to copy and paste the result. Instead, use 'print' function for the output when relevant. Check the execution result returned by the user.
        If the result indicates there is an error, fix the error, save the code in a file before executing it, put # filename: <filename> inside the code block as the first line and output the code again. Suggest the full code instead of partial code or code changes.
    1. When you need to collect info, use the code to output the info you need, for example, browse or search the web, download/read a file, print the content of a webpage or a file, get the current date/time, check the operating system. After sufficient info is printed and the task is ready to be solved based on your language skill, you can solve the task by yourself.
    2. When you need to perform some task with code, use the code to perform the task and output the result. Finish the task smartly.
When using code, you must indicate the script type in the code block. The user cannot provide any other feedback or perform any other action beyond executing the code you suggest. The user can't modify your code. So do not suggest incomplete code which requires users to modify. Don't use a code block if it's not intended to be executed by the user.
When you find an answer, verify the answer carefully. Include verifiable evidence in your response if possible.
Reply "TERMINATE" in the end when everything is done.
    """,
        max_consecutive_auto_reply=1,
        human_input_mode="NEVER",
        is_termination_msg=lambda msg: "exitcode: 0" in msg.get("content"),
        llm_config={
            "config_list": config_list
        }
    )

    user_proxy = autogen.UserProxyAgent(
        name="CodeExecutor",
        system_message="Executor.Execute the code written by the coder, set up javascript-React environment because code is a React component written in JavaScript.",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=1,
        is_termination_msg=lambda msg: "exitcode: 0" in msg.get("content"),
        code_execution_config={
            "last_n_messages": 3,
            "executor": code_executor,
            "language_map": {
                "javascript": "node",
                "js": "node",
                "typescript": "ts-node",
                "ts": "ts-node"
            }
        }
    )

    # Check and install only missing dependencies
    if not check_dependencies():
        if not install_missing_dependencies():
            print("Failed to set up React environment")
            return
    else:
        print("All dependencies are already installed")

    # Start chat and code generation
    user_proxy.initiate_chat(
        assistant,
        message=input("INPUT HERE")
    )

    # Start development server
    server_process = start_dev_server()
    if server_process:
        try:
            # Keep the server running until user interrupts
            server_process.wait()
        except KeyboardInterrupt:
            server_process.terminate()
            print("\nDevelopment server stopped")

if __name__ == "__main__":
    main()