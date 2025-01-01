from setuptools import setup, find_packages

setup(
    name='worldClock',
    version='0.1.0',
    description='A Discord bot for showing world clock.',
    author='Zahzr',
    packages=find_packages(),
    install_requires=[
        'discord.py',
        'python-dotenv',
        'pytz',
        'aiosqlite',
    ],
    entry_points={
        'console_scripts': [
            'worldClock = bot:main',
        ],
    },
)