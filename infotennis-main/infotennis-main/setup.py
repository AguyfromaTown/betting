from setuptools import find_packages, setup

setup(
    name='infotennis',
    version='1.0.1',
    description='Module for scraping and processing ATP data.',
    url='https://github.com/glad94/infotennis',
    author='Gerald Lim',
    author_email='lgjg1994@gmail.com',
    packages=find_packages(),
    install_requires=['pandas','matplotlib','numpy','requests','beautifulsoup4','cryptography','selenium',\
                        'webdriver-manager','pyyaml','pymysql','func-timeout',]
)
