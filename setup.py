import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="mlmprovisions", # Replace with your own username
    version="0.1.8",
    author="Belda",
    author_email="jakub.belescak@centrum.cz",
    description="Reusable Django app to track provisions for affiliate partners. Includes tools for multi-level marketing provisions.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/belda/mlmprovisions",
    packages=['mlmtools'],
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.4',
    install_requires = [
        "django",
        "django-floppyforms",
        "django-treenode"
    ]
)