"""Setup."""

from setuptools import setup, find_packages

setup(
    name="scoff",
    version="0.2",
    packages=find_packages(),
    package_dir={"": "."},
    install_requires=[],
    author="Bruno Morais",
    author_email="brunosmmm@gmail.com",
    description="Simple COmpiler Framework",
    scripts=[],
)
