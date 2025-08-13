# Blender 4.4 - "Debug Output Test" Geometry Nodes Script
# This is a minimal script to diagnose issues with the Group Output node.

# === Blender GN Safety Header (required) =====================================
import bpy
import math

def socket(iface, *, name, in_out, socket_type, desc, default=None, min_val=None, max_val=None):
    """Safely create a new socket, enforcing keyword arguments and setting properties."""
    s = iface.new_socket(name=name, in_out=in_out, socket_type=socket_type, description=desc)
    if default is not None and hasattr(s, 'default_value'):
        try: s.default_value = default
        except TypeError: pass
    if min_val is not None and hasattr(s, 'min_value'):
        try: s.min_value = min_val
        except TypeError: pass
    if max_val is not None and hasattr(s, 'max_value'):
        try: s.max_value = max_val
        except TypeError: pass
    return s

def new_node(nodes, bl_idname, *, location=(0,0)):
    """Create a new node, raising an error if the type is not supported in the current Blender version."""
    if not hasattr(bpy.types, bl_idname):
        raise RuntimeError(f"Unsupported node type: {bl_idname}. Please use a math-based fallback.")
    n = nodes.new(bl_idname)
    n.location = location
    return n

def new_gn_group(name="GN Group"):
    """Create a new, empty Geometry Node group."""
    ng = bpy.data.node_groups.new(name, 'GeometryNodeTree')
    for n in list(ng.nodes):
        ng.nodes.remove(n)
    return ng

def attach_group_modifier(obj, ng, name="GN Modifier"):
    """Attach a node group to an object's GN modifier, creating one if needed."""
    mod = next((m for m in obj.modifiers if m.type == 'NODES'), None)
    if mod is None:
        mod = obj.modifiers.new(name=name, type='NODES')
    mod.node_group = ng
    return mod

# Ensure there is an active object to work with
if bpy.context.active_object is None:
    bpy.ops.mesh.primitive_plane_add()
OBJ = bpy.context.active_object
# === End Safety Header =====================================================

def build_debug_tree(ng):
    """Constructs a minimal node tree with a cube connected to the output."""
    nodes, links, iface = ng.nodes, ng.links, ng.interface

    # 1. Define the output socket on the modifier interface
    socket(iface, name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry', desc="The final output geometry")

    # 2. Create the essential nodes
    n_out = new_node(nodes, 'NodeGroupOutput', location=(200, 0))
    cube = new_node(nodes, 'GeometryNodeMeshCube', location=(0, 0))

    # 3. Connect the cube's mesh output to the group's output socket
    # This is the step that has been failing in other scripts.
    try:
        links.new(cube.outputs['Mesh'], n_out.inputs['Geometry'])
        print("DEBUG: Successfully linked Cube to Group Output.")
    except KeyError:
        print("DEBUG: FAILED to link Cube to Group Output. The 'Geometry' socket was not found on the output node.")
        # As a fallback, let's see what inputs ARE available.
        if hasattr(n_out, 'inputs'):
            print(f"DEBUG: Available inputs on the output node: {[s.name for s in n_out.inputs]}")
        else:
            print("DEBUG: The output node has no 'inputs' attribute at all.")

def setup_and_run():
    """Primary function to set up the scene and run the node tree creation."""
    ng = new_gn_group("Debug Output Test")
    build_debug_tree(ng)
    attach_group_modifier(OBJ, ng, "Debug Test")
    print(f"Created and assigned '{ng.name}' to modifier on object '{OBJ.name}'. Please check the console for debug messages.")

# --- Execute the script ---
setup_and_run()
