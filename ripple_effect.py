# Blender 4.4 - "Procedural Ripple Effect" Geometry Nodes Script
# Creates a plane mesh that deforms to simulate ripples radiating from the center.

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

def build_ripple_tree(ng):
    """Constructs the node tree for the procedural ripple effect."""
    nodes, links, iface = ng.nodes, ng.links, ng.interface

    # ---- 1. Interface Definition ----
    socket(iface, name="Grid Size", in_out='INPUT', socket_type='NodeSocketFloat', desc="Overall size of the water plane", default=10.0, min_val=1.0, max_val=200.0)
    socket(iface, name="Grid Resolution", in_out='INPUT', socket_type='NodeSocketInt', desc="Number of vertices in the grid (more is smoother)", default=128, min_val=16, max_val=1024)
    socket(iface, name="Wave Speed", in_out='INPUT', socket_type='NodeSocketFloat', desc="How fast the ripples travel outwards", default=3.0, min_val=0.0, max_val=50.0)
    socket(iface, name="Wave Frequency", in_out='INPUT', socket_type='NodeSocketFloat', desc="The spatial frequency of the ripples (more is tighter)", default=5.0, min_val=0.1, max_val=100.0)
    socket(iface, name="Wave Amplitude", in_out='INPUT', socket_type='NodeSocketFloat', desc="The height of the ripples", default=0.1, min_val=0.0, max_val=10.0)
    socket(iface, name="Time Speed", in_out='INPUT', socket_type='NodeSocketFloat', desc="Multiplier for the global animation speed", default=1.0, min_val=0.0, max_val=10.0)
    socket(iface, name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry', desc="Final displaced geometry")

    # ---- 2. Node Graph Construction ----
    n_in = new_node(nodes, 'NodeGroupInput', location=(-1600, 0))
    n_out = new_node(nodes, 'NodeGroupOutput', location=(400, 0))

    # Base Grid
    grid = new_node(nodes, 'GeometryNodeMeshGrid', location=(-1400, 200))
    links.new(n_in.outputs['Grid Size'], grid.inputs['Size X'])
    links.new(n_in.outputs['Grid Size'], grid.inputs['Size Y'])
    links.new(n_in.outputs['Grid Resolution'], grid.inputs['Vertices X'])
    links.new(n_in.outputs['Grid Resolution'], grid.inputs['Vertices Y'])

    # Time Driver
    time_val = new_node(nodes, 'ShaderNodeValue', location=(-1600, -400)); time_val.label = "Time (s)"
    safe_time_driver(time_val)
    
    time_speed_mult = new_node(nodes, 'ShaderNodeMath', location=(-1400, -400)); time_speed_mult.operation = 'MULTIPLY'
    links.new(time_val.outputs['Value'], time_speed_mult.inputs[0])
    links.new(n_in.outputs['Time Speed'], time_speed_mult.inputs[1])

    # Calculate distance from center for each point
    pos = new_node(nodes, 'GeometryNodeInputPosition', location=(-1200, -100))
    dist_from_center = new_node(nodes, 'ShaderNodeVectorMath', location=(-1000, -100)); dist_from_center.operation = 'LENGTH'
    links.new(pos.outputs['Position'], dist_from_center.inputs[0])

    # --- Wave Calculation: sin((distance - time * speed) * frequency) * amplitude ---
    
    # 1. time * speed
    time_offset = new_node(nodes, 'ShaderNodeMath', location=(-800, -200)); time_offset.operation = 'MULTIPLY'
    links.new(time_speed_mult.outputs['Value'], time_offset.inputs[0])
    links.new(n_in.outputs['Wave Speed'], time_offset.inputs[1])

    # 2. distance - time_offset
    radial_pos = new_node(nodes, 'ShaderNodeMath', location=(-600, -100)); radial_pos.operation = 'SUBTRACT'
    links.new(dist_from_center.outputs['Value'], radial_pos.inputs[0])
    links.new(time_offset.outputs['Value'], radial_pos.inputs[1])

    # 3. radial_pos * frequency
    wave_input_freq = new_node(nodes, 'ShaderNodeMath', location=(-400, -100)); wave_input_freq.operation = 'MULTIPLY'
    links.new(radial_pos.outputs['Value'], wave_input_freq.inputs[0])
    links.new(n_in.outputs['Wave Frequency'], wave_input_freq.inputs[1])

    # 4. sin(wave_input_freq)
    sine_wave = new_node(nodes, 'ShaderNodeMath', location=(-200, -100)); sine_wave.operation = 'SINE'
    links.new(wave_input_freq.outputs['Value'], sine_wave.inputs[0])

    # 5. sine_wave * amplitude
    displacement_z = new_node(nodes, 'ShaderNodeMath', location=(0, -100)); displacement_z.operation = 'MULTIPLY'
    links.new(sine_wave.outputs['Value'], displacement_z.inputs[0])
    links.new(n_in.outputs['Wave Amplitude'], displacement_z.inputs[1])

    # --- Apply Displacement ---
    displacement_vector = new_node(nodes, 'ShaderNodeCombineXYZ', location=(0, 100))
    links.new(displacement_z.outputs['Value'], displacement_vector.inputs['Z'])

    set_pos = new_node(nodes, 'GeometryNodeSetPosition', location=(200, 200))
    links.new(grid.outputs['Mesh'], set_pos.inputs['Geometry'])
    links.new(displacement_vector.outputs['Vector'], set_pos.inputs['Offset'])

    # Final Output
    links.new(set_pos.outputs['Geometry'], n_out.inputs['Geometry'])


def setup_and_run():
    """Primary function to set up the scene and run the node tree creation."""
    print("--- Starting Procedural Ripple Effect Script ---")
    
    # Ensure we start with a clean slate
    if bpy.context.scene.objects:
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)

    # Create the main object
    obj = ensure_active_object()
    obj.name = "RippleSurface"

    # Create and build the node group
    ng = new_gn_group("ProceduralRippleEffect")
    build_ripple_tree(ng)
    
    # Attach the modifier
    mod = attach_group_modifier(obj, ng, "RippleEffectModifier")

    print(f"Successfully created and assigned '{ng.name}' to modifier '{mod.name}' on object '{obj.name}'.")
    print("--- Procedural Ripple Effect Script Finished ---")

# --- Execute the script ---
if __name__ == "__main__":
    setup_and_run()
