from setuptools import setup, find_namespace_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="auther",
    version="0.0.6",
    author="Kamran Ali",
    author_email="auther@trewq34.com",
    description="Command line tool for AWS CLI authentication",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/trewq34/auther",
    project_urls={
        "Bug Tracker": "https://github.com/trewq34/auther/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    packages=[package for package in find_namespace_packages('.') if 'auther' in package],
    install_requires=[
        "typer",
        'requests',
        'boto3',
        'bs4',
        'pyppeteer',
        'asyncio'
    ],
    entry_points="""
        [console_scripts]
        auther=auther.cli:app
    """,
)