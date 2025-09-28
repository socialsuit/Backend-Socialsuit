from setuptools import setup, find_packages

setup(
    name="social_suit",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi",
        "uvicorn",
        "sqlmodel",
        "pydantic",
    ],
)