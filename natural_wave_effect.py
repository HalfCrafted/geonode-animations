# Blender 4.4 - "Natural Wave Effect" Geometry Nodes Script
# Creates a plane mesh that deforms using a 4D noise texture to simulate natural water surfaces.

# === Blender GN Safety Header (from analyzed best practices) =================
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

def safe_time_driver(value_node, expr="frame/24"):
    """Create a time driver on a Value node, removing any old ones to prevent duplicates."""
    try:
        value_node.outputs[0].driver_remove('default_value')
    except Exception:
        pass
    d = value_node.outputs[0].driver_add('default_value')
    d.driver.expression = expr
    return d

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

def ensure_active_object():
    """Ensures there is an active object, creating a plane if necessary."""
    if bpy.context.active_object is None:
        bpy.ops.mesh.primitive_plane_add()
    return bpy.context.active_object
# === End Safety Header =====================================================

def build_natural_wave_tree(ng):
    """Constructs the node tree for the natural wave effect using a noise texture."""
    nodes, links, iface = ng.nodes, ng.links, ng.interface

    # ---- 1. Interface Definition ----
    socket(iface, name="Grid Size", in_out='INPUT', socket_type='NodeSocketFloat', desc="Overall size of the water plane", default=10.0, min_val=1.0, max_val=200.0)
    socket(iface, name="Grid Resolution", in_out='INPUT', socket_type='NodeSocketInt', desc="Number of vertices in the grid", default=128, min_val=16, max_val=1024)
    socket(iface, name="Wave Height", in_out='INPUT', socket_type='NodeSocketFloat', desc="The maximum height of the waves", default=0.2, min_val=0.0, max_val=10.0)
    socket(iface, name="Noise Scale", in_out='INPUT', socket_type='NodeSocketFloat', desc="The scale of the noise pattern (larger value = smaller waves)", default=1.5, min_val=0.1, max_val=100.0)
    socket(iface, name="Noise Detail", in_out='INPUT', socket_type='NodeSocketFloat', desc="The level of detail in the noise pattern", default=4.0, min_val=0.0, max_val=16.0)
    socket(iface, name="Evolution Speed", in_out='INPUT', socket_type='NodeSocketFloat', desc="How fast the wave pattern changes over time", default=0.5, min_val=0.0, max_val=10.0)
    socket(iface, name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry', desc="Final displaced geometry")

    # ---- 2. Node Graph Construction ----
    n_in = new_node(nodes, 'NodeGroupInput', location=(-1400, 0))
    n_out = new_node(nodes, 'NodeGroupOutput', location=(400, 0))

    # Base Grid
    grid = new_node(nodes, 'GeometryNodeMeshGrid', location=(-1200, 200))
    links.new(n_in.outputs['Grid Size'], grid.inputs['Size X'])
    links.new(n_in.outputs['Grid Size'], grid.inputs['Size Y'])
    links.new(n_in.outputs['Grid Resolution'], grid.inputs['Vertices X'])
    links.new(n_in.outputs['Grid Resolution'], grid.inputs['Vertices Y'])

    # Time Driver for noise evolution
    time_val = new_node(nodes, 'ShaderNodeValue', location=(-1400, -400)); time_val.label = "Time (s)"
    safe_time_driver(time_val)
    
    evolution = new_node(nodes, 'ShaderNodeMath', location=(-1200, -400)); evolution.operation = 'MULTIPLY'
    links.new(time_val.outputs['Value'], evolution.inputs[0])
    links.new(n_in.outputs['Evolution Speed'], evolution.inputs[1])

    # --- Noise-based Displacement ---
    pos = new_node(nodes, 'GeometryNodeInputPosition', location=(-1000, -100))

    # 4D Noise Texture
    noise_tex = new_node(nodes, 'ShaderNodeTexNoise', location=(-800, 0))
    noise_tex.noise_dimensions = '4D'
    links.new(pos.outputs['Position'], noise_tex.inputs['Vector'])
    links.new(evolution.outputs['Value'], noise_tex.inputs['W'])
    links.new(n_in.outputs['Noise Scale'], noise_tex.inputs['Scale'])
    links.new(n_in.outputs['Noise Detail'], noise_tex.inputs['Detail'])

    # Map noise output from [0, 1] to [-1, 1] to have waves go up and down
    map_range = new_node(nodes, 'ShaderNodeMapRange', location=(-600, 0))
    map_range.inputs['To Min'].default_value = -1.0
    map_range.inputs['To Max'].default_value = 1.0
    links.new(noise_tex.outputs['Fac'], map_range.inputs['Value'])

    # Apply amplitude
    displacement_z = new_node(nodes, 'ShaderNodeMath', location=(-400, 0)); displacement_z.operation = 'MULTIPLY'
    links.new(map_range.outputs['Result'], displacement_z.inputs[0])
    links.new(n_in.outputs['Wave Height'], displacement_z.inputs[1])

    # --- Apply Displacement ---
    displacement_vector = new_node(nodes, 'ShaderNodeCombineXYZ', location=(-200, 100))
    links.new(displacement_z.outputs['Value'], displacement_vector.inputs['Z'])

    set_pos = new_node(nodes, 'GeometryNodeSetPosition', location=(0, 200))
    links.new(grid.outputs['Mesh'], set_pos.inputs['Geometry'])
    links.new(displacement_vector.outputs['Vector'], set_pos.inputs['Offset'])

    # Final Output
    links.new(set_pos.outputs['Geometry'], n_out.inputs['Geometry'])


def setup_and_run():
    """Primary function to set up the scene and run the node tree creation."""
    print("--- Starting Natural Wave Effect Script ---")
    
    if bpy.context.scene.objects:
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)

    obj = ensure_active_object()
    obj.name = "NaturalWaveSurface"

    ng = new_gn_group("NaturalWaveEffect")
    build_natural_wave_tree(ng)
    
    mod = attach_group_modifier(obj, ng, "NaturalWaveModifier")

    print(f"Successfully created and assigned '{ng.name}' to modifier '{mod.name}' on object '{obj.name}'.")
    print("--- Natural Wave Effect Script Finished ---")

if __name__ == "__main__":
    setup_and_run()
