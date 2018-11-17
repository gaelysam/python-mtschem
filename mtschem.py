# Python library to handle Minetest schematics, by Gaël de Sailly, Nov 10 2018.
# Inspired by python-minetest library by LeMagnesium: https://github.com/LeMagnesium/python-minetest/blob/3d81909/libminetest/schematics.py
# Using NumPy for speed and memory efficiency (more adapted to huge schematics)

# To import the library:
#     import mtschem

# To load a schematic:
#     my_schem = Schem("path/to/my_schem.mts")

# The data are stored in my_schem.data in the form of a X*Y*Z array of structured elements.
# To get the shape of the schematic, as a tuple:
#     shape = my_schem.data.shape
# To get the volume:
#     volume = my_schem.data.size

# To get the element at position (3,5,7):
#     element = my_schem.data[3,5,7]

# Each element has 4 fields:
#     - element["node"] is the node ID (rank on the node list, see below)
#     - element["prob"] is its probability (0-127)
#     - element["force"] boolean indicating whether to force replacement of existing nodes when the schematic is placed
#     - element["param2"] param2 of the node

# To get an array of node IDs:
#     node_ids = my_schem.data["node"]
# Also works for prob, force and param2.

# The data array can be freely modified, as long as you keep the structure with the 4 named fields. Values and array size can be changed.

# Y-Slice probabilities:
#     my_schem.yprobs[6] is the probability to get slice at y=6 generated (0-127)
# If you use specific values for yprobs, make sure the size of this array follows the Y size of the data schematic. If you always use 127, you can neglect this.

# Get the list of the existing nodes:
#     node_list = my_schem.nodes

# Use that list to get the node name:
#     node_name = node_list[element["node"]]
# Keep the node name list up-to-date if you add new nodes to the data.

# To export the modified schematic:
#     my_schem.save("path/to/output_schem.mts")

import numpy as np
import zlib
from io import BytesIO

bulk_dtype = np.dtype([("node", ">u2"), ("prob", "u1"), ("force", "?"), ("param2", "u1")])

class Schem:
	def __init__(self, filename):
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
		data["prob"], data["force"] = np.divmod(np.fromstring(bulk.read(volume), dtype="u1").reshape(rev_size), 2)
		data["param2"] = np.fromstring(bulk.read(volume), dtype="u1").reshape(rev_size)

		self.data = data.swapaxes(0, 2) # data axis order is Z[Y[X]], we want X[Y[Z]]

	def save(self, filename, compression=9):
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

		self.cleanup_nodelist()

		data = self.data.swapaxes(0, 2) # get MTS's axes order again

		bulk = BytesIO()

		bulk.write(data["node"].tobytes())
		bulk.write((data["prob"]*2 + data["force"]).astype("u1").tobytes())
		bulk.write(data["param2"].tobytes())

		f.write(zlib.compress(bulk.getbuffer(), compression))
		f.close()

	def cleanup_nodelist(self):
		existing_nodes = np.unique(self.data["node"])
		existing_nodes.sort()

		new_nodelist = [self.nodes[i] for i in existing_nodes]
		
		transform_list = np.zeros(len(self.nodes), dtype=">u2")
		duplicates = 0
		for new_i, old_i in enumerate(existing_nodes):
			i = new_i - duplicates
			if new_nodelist[i] in new_nodelist[:i]: # If this node is a duplicate
				transform_list[old_i] = new_nodelist.index(new_nodelist[i])
				new_nodelist.pop(i)
				duplicates += 1 # Keep count of removed duplicates to offset
				continue
			transform_list[old_i] = i

		self.nodes = new_nodelist
		self.data["node"] = transform_list[self.data["node"]]
