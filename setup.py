from setuptools import setup

setup(
    name="auther",
    version="0.1",
    packages=["auther"],
    install_requires=[
        "Click",
    ],
    entry_points="""
        [console_scripts]
        auther=auther.cli:main
    """,
)