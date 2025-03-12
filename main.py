from src import App
from src import LibrarySetup

library_installed = True

if __name__ == "__main__":
    if not library_installed:
        LibrarySetup().setup()

    app_instance = App()
    app_instance.run()