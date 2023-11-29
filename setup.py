
from setuptools import setup, find_packages


from pathlib import Path
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()


setup(
    name='lockfolder',
    long_description=long_description,
    long_description_content_type='text/markdown',
    version='1.0.1',
    license='MIT',
    author="Lion Kimbro",
    author_email='lionkimbro@gmail.com',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    url='https://github.com/LionKimbro/lockfolder',
    keywords='mutex lock locking guid',
    install_requires=[
          'psutil',
      ],

)

