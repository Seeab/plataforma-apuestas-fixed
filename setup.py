from setuptools import setup, find_packages

setup(
    name="plataforma-apuestas",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "Flask>=2.3.0",
        "pandas>=1.5.0", 
        "numpy>=1.21.0",
        "gunicorn>=20.0.0"
    ],
    python_requires=">=3.7",
)