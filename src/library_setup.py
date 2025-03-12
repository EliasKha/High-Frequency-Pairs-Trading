import os
import shutil
import subprocess

class LibrarySetup:
    def __init__(self, repo_url='https://github.com/philipperemy/FX-1-Minute-Data.git'):
        self.repo_url = repo_url
        self.repo_name = self.repo_url.split('/')[-1].replace('.git', '')
    
    def clone_repo(self):
        subprocess.run(['git', 'clone', self.repo_url], check=True)
    
    def copy_pairs_csv(self):
        source_path = os.path.join(self.repo_name, 'pairs.csv')
        destination_path = 'pairs.csv'
        shutil.copy(source_path, destination_path)
    
    def install_requirements(self):
        os.chdir(self.repo_name)
        subprocess.run(['pip', 'install', '-r', 'requirements.txt'], check=True)
        subprocess.run(['python', 'setup.py', 'install'], check=True)
        os.chdir('..')
    
    def cleanup(self):
        shutil.rmtree(self.repo_name)
    
    def setup(self):
        self.clone_repo()
        self.copy_pairs_csv()
        self.install_requirements()
        self.cleanup()