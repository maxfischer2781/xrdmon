#!/usr/bin/env python
import os
from setuptools import setup, find_packages

repo_base_dir = os.path.abspath(os.path.dirname(__file__))
# pull in the packages metadata
package_about = {}
with open(os.path.join(repo_base_dir, "xrdmonlib", "__about__.py")) as about_file:
    exec(about_file.read(), package_about)

if __name__ == '__main__':
    setup(
        name=package_about['__title__'],
        version=package_about['__version__'],
        description=package_about['__summary__'],
        author=package_about['__author__'],
        author_email=package_about['__email__'],
        url=package_about['__url__'],
        packages=find_packages(),
        # autogenerated executable
        entry_points={
            'console_scripts': [
                'xrdmon = xrdmonlib.interface:app_main',
            ],
        },
        # dependencies
        install_requires=['apmon', 'chainlet>=0.9', 'filelock'],
        # metadata for package seach
        classifiers=[
            'Development Status :: 5 - Production/Stable',
            'Intended Audience :: Developers',
            'Intended Audience :: Science/Research',
            'Intended Audience :: System Administrators',
            'Topic :: System :: Monitoring',
            'Programming Language :: Python :: 2',
            'Programming Language :: Python :: 2.6',
            'Programming Language :: Python :: 2.7',
            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: 3.2',
            'Programming Language :: Python :: 3.3',
            'Programming Language :: Python :: 3.4',
            'Programming Language :: Python :: 3.5',
            'Programming Language :: Python :: 3.6',
        ],
        keywords='monitoring monalisa apmon hep',
    )
