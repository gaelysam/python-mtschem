#!/usr/bin/env python3
from setuptools import setup

setup(
	name="mtschem",
	version="0.1",
	author="Gaël de Sailly",
	author_email="gael-de-sailly@netc.eu",
	packages=['mtschem'],
	install_requires=['numpy'],
	license="GPLv2",
	description="Provides Input/Output for Minetest schematics",
)
