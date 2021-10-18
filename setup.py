from setuptools import setup, find_packages

setup(
    name="vidarrtools",
    version=open(path.join(path.dirname(__file__), 'VERSION')).read().strip(),
    description="Tools for use with Vidarr",
    author="Andre Masella",
    author_email="andre.masella@oicr.on.ca",
    python_requires=">=3.7.0",
    packages=find_packages(exclude=["test"]),
    entry_points={"console_scripts": ["wdl2vidarr = vidarr.wdl:main"]},
    install_requires=[
        "miniwdl>=0.9.0",
        "requests>=2.22.0"
    ],
    scripts=["scripts/vidarr-build"],
    setup_requires=["pytest-runner"],
    tests_require=["pytest"],
    test_suite="test",
    extras_require={
        "develop": ["pytest>=5.2.2", "pytest-runner>=5.2"]
    },
)
