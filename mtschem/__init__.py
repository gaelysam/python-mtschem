# Python library to handle Minetest schematics, by Gaël de Sailly, Nov 10 2018.
# Inspired by python-minetest library by LeMagnesium: https://github.com/LeMagnesium/python-minetest/blob/3d81909/libminetest/schematics.py
# Using NumPy for speed and memory efficiency (more adapted to huge schematics)

import numpy as np
import zlib
from io import BytesIO

bulk_dtype = np.dtype([("node", ">u2"), ("prob", "u1"), ("force", "?"), ("param2", "u1")])

class Schem:
	def __init__(self, *args, **kwargs):
		if len(args) >= 1:
			if isinstance(args[0], str):
				self.load(args[0])
			else:
				if isinstance(args[0], tuple):
					shape = args
				else:
					shape = tuple(args[:3])
				self.version = 4
				self.yprobs = np.zeros(shape[1], dtype="u1")
				self.nodes = ["air"]
				self.data = np.zeros(shape, dtype=bulk_dtype)

		if 'version' in kwargs:
			self.version = kwargs['version']
		if 'yprobs' in kwargs:
			self.yprobs = kwargs['yprobs']
		if 'nodes' in kwargs:
			self.nodes = kwargs['nodes']
		if 'data' in kwargs:
			self.data = kwargs['data']

	def load(self, filename):
		f = open(filename, "rb")

		if f.read(4) != b"MTSM":
			print("WARNING: Signature 'MTSM' not recognized!")

		self.version = np.fromstring(f.read(2), dtype=">u2")[0]
		size = tuple(np.fromstring(f.read(6), dtype=">u2"))
		volume = int(size[0])*int(size[1])*int(size[2])
		print(size)
		rev_size = tuple(reversed(size)) # Reversed shape tuple, to handle the schematic file in which data are stored as Z[Y[X]]
		self.yprobs = np.fromstring(f.read(size[1]), dtype="u1")

		nodecount = np.fromstring(f.read(2), dtype=">u2")[0]
		self.nodes = []
		for node in range(nodecount):
			namelength = np.fromstring(f.read(2), dtype=">u2")[0]
			self.nodes.append(f.read(namelength).decode("utf-8"))
		bulk = BytesIO(zlib.decompress(f.read()))
		f.close() # We have read all

		data = np.zeros(rev_size, dtype=bulk_dtype)

		data["node"] = np.fromstring(bulk.read(volume*2), dtype=">u2").reshape(rev_size)
		data["force"], data["prob"] = np.divmod(np.fromstring(bulk.read(volume), dtype="u1").reshape(rev_size), 128)
		data["param2"] = np.fromstring(bulk.read(volume), dtype="u1").reshape(rev_size)

		self.data = data.swapaxes(0, 2) # data axis order is Z[Y[X]], we want X[Y[Z]]

	def save(self, filename, compression=9):
		self.cleanup_nodelist()

		f = open(filename, "wb")

		f.write(b"MTSM")

		f.write(np.uint16(self.version).newbyteorder(">").tobytes())
		size = self.data.shape
		f.write(np.array(size, dtype=">u2").tobytes())

		f.write(np.resize(self.yprobs, size[1]).tobytes()) # the yprobs list's size must be equal to the vertical size of the schematic ; if not, resize it.

		nodecount = len(self.nodes)
		f.write(np.uint16(nodecount).newbyteorder(">").tobytes())
		for node in self.nodes:
			namelength = len(node)
			f.write(np.uint16(namelength).newbyteorder(">").tobytes())
			f.write(node.encode("utf-8"))

		data = self.data.swapaxes(0, 2) # get MTS's axes order again

		bulk = BytesIO()

		bulk.write(data["node"].tobytes())
		bulk.write((data["force"] * 128 + data["prob"]).astype("u1").tobytes())
		bulk.write(data["param2"].tobytes())

		f.write(zlib.compress(bulk.getbuffer(), compression))
		f.close()

	def cleanup_nodelist(self):
		existing_nodes = np.unique(self.data["node"])
		existing_nodes.sort()

		new_nodelist = [self.nodes[i] for i in existing_nodes]
		
		transform_list = np.zeros(len(self.nodes), dtype=">u2")
		duplicates = 0
		update_array = False
		for new_i, old_i in enumerate(existing_nodes):
			i = new_i - duplicates
			if new_nodelist[i] in new_nodelist[:i]: # If this node is a duplicate
				transform_list[old_i] = new_nodelist.index(new_nodelist[i])
				new_nodelist.pop(i)
				duplicates += 1 # Keep count of removed duplicates to offset
				continue
			transform_list[old_i] = i
			if old_i != i:
				update_array = True

		self.nodes = new_nodelist
		if update_array:
			self.data["node"] = transform_list[self.data["node"]]

	def __getitem__(self, slices):
		data = self.data[slices].copy()
		nodes = self.nodes[:]
		if isinstance(slices, tuple) and len(slices) >= 2:
			yprobs = self.yprobs[slices[1]].copy()
		else:
			yprobs = self.yprobs.copy()

		return Schem(data=data, nodes=nodes, yprobs=yprobs, version=self.version)
