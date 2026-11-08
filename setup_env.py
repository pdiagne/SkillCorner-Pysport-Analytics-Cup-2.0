import sys
import subprocess


def install_packages():
    # List of packages required for the dashboard
    packages = [
        "pandas",
        "numpy",
        "requests",
        "matplotlib",
        "urllib3",
        "lxml"
    ]

    print("=" * 60)
    print("Starting setup for Home vs Away Dashboard...")
    print("=" * 60)

    for package in packages:
        print(f"\nChecking {package}...")
        try:
            # Check if the package is already installed
            __import__(package.replace("-", "_"))
            print(f"✓ {package} is already installed.")
        except ImportError:
            print(f"→ {package} not found. Installing now...")
            try:
                # Use subprocess to run pip install
                subprocess.check_call([sys.executable, "-m", "pip", "install", package])
                print(f"✓ Successfully installed {package}.")
            except subprocess.CalledProcessError:
                print(f"✗ Failed to install {package}. Please install it manually.")
                sys.exit(1)

    # Tkinter is part of the Python standard library, but we should verify it works
    print("\nChecking tkinter (standard library)...")
    try:
        import tkinter
        print("✓ tkinter is available.")
    except ImportError:
        print("✗ tkinter is not available. You may need to reinstall Python and ensure 'tcl/tk' is checked.")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("Setup complete! You can now run 'app_1.py'.")
    print("=" * 60)


if __name__ == "__main__":
    # Ensure pip is up to date first
    print("Upgrading pip to the latest version...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])

    install_packages()