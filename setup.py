from cx_Freeze import setup, Executable

setup(
    name="AITyper",
    version="1.0",
    description="CustomTkinter App",
    executables=[Executable("app.py")],
)