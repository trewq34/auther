from setuptools import setup, find_namespace_packages

setup(
    name="auther",
    version="0.0.3",
    packages=[package for package in find_namespace_packages('.') if 'auther' in package],
    install_requires=[
        "Click",
        'requests',
        'boto3',
        'bs4',
        'pyppeteer',
        'asyncio'
    ],
    entry_points="""
        [console_scripts]
        auther=auther.cli:main
    """,
)