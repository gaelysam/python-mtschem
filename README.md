# mtschem
Python Library providing Input/Output for Minetest Schematics (.mts), converting them into a Numpy array.
Code by Gaël de Sailly, loosely based on [python-minetest](https://github.com/LeMagnesium/python-minetest/blob/3d81909/libminetest/schematics.py) by LeMagnesium. License: GPLv2.

## Installation
Download from GitHub:
- using `git`: `git clone https://github.com/Gael-de-Sailly/python-mtschem.git`
- or download directly the [zip archive](https://github.com/Gael-de-Sailly/python-mtschem/archive/master.zip).

Then, using the command line, place yourself in `python-mtschem` directory.
Install:
```
python3 setup.py install
```
You may need the administrator rights.

## Basic use
### Import the library
```python3
import mtschem
```

### Load a schematic
```python3
my_schem = Schem("path/to/my_schem.mts")
```

### `data` array
The data are stored in `my_schem.data` in the form of a X×Y×Z array of structured elements.
To get the shape and the volume:
```python3
shape = my_schem.data.shape # 3-tuple
volume = my_schem.data.size
```

To get the element at position (3,5,7):
```python3
element = my_schem.data[3,5,7]
```

Each element has 4 fields:
```python3
node = element["node"] # node ID (rank on the node list, see below)
prob = element["prob"] # probability (0-127)
force = element["force"] # whether to force replacement of existing nodes when the schematic is placed (boolean)
param2 = element["param2"] # param2 of the node
```

To get an array of node IDs:
```python3
node_ids = my_schem.data["node"]
```
Also works for `prob`, `force` and `param2`.

The data array can be freely modified, as long as you keep the structure with the 4 named fields. Values and array size can be changed.

### Y-Slice probabilities
They are stored in `my_schem.yprobs` in the form of a 1D list of size Y.
```python3
prob_at_6 = my_schem.yprobs[6] # is the probability to get slice at y=6 generated (0-127)
```
If you use specific values for yprobs, make sure the size of this array follows the Y size of the data schematic. If you always use 127, you can neglect this.

### Node list
The node list is stored in `myschem.nodes`. Their order define the node ID. To get the node name of `element`:
```python3
node_name = my_schem.nodes[element["node"]]
```
To get the ID of a node:
```python3
c_lawn = my_schem.nodes.index("default:dirt_with_grass")
```
Keep the node name list up-to-date if you add new nodes to the data.

### Saving
To export the modified schematic:
```python3
my_schem.save("path/to/output_schem.mts")
```

## Useful tricks
### Replacing a node
To replace every occurence of a node, you don't need to modify the `data` array, just tweak the node list.
```python3
def replace_dirt_by_stone(schem):
    c_dirt = schem.nodes.index("default:dirt")
    schem.nodes[c_dirt] = "default:stone"
```
Of course this may introduce a duplicate in the node list. Duplicates are automatically fixed on saving, so you generally don't need to bother with that. However if you want to fix them manually, add this:
```python3
    schem.cleanup_nodelist()
```
This removes duplicates and unused nodes in the node list, and updates the array if necessary.

### Counting the quantity of a node
This needs to make use of Numpy's `count_nonzero` function.
```python3
import numpy as np
def count_node(schem, nodename):
    id = schem.nodes.index(nodename)
    return np.count_nonzero(schem.data["node"] == id)
```

### Find the list of nodes present in a given part of the schematic
Using the Numpy function `unique` to give the list of existing values in an array.
```python3
import numpy as np
def list_nodes_in(schem, minp, maxp): # minp and maxp 3-tuples
    part = schem.data["node"][
            minp[0]:maxp[0]+1,
            minp[1]:maxp[1]+1,
            minp[2]:maxp[2]+1,
    ]
    id_list = np.unique(part)
    node_list = []
    for id in id_list:
        node_list.append(schem.nodes[id])
    return node_list
```
