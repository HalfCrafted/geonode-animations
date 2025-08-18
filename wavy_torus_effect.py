# Blender 4.4 - "Wavy Torus Effect" Geometry Nodes Script
# Creates a horizontal torus that expands, with a sine wave displacing it for a wavy effect.

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

def build_wavy_torus_tree(ng):
    """Constructs the node tree for the wavy torus effect."""
    nodes, links, iface = ng.nodes, ng.links, ng.interface

    # ---- 1. Interface Definition ----
    socket(iface, name="Start Radius", in_out='INPUT', socket_type='NodeSocketFloat', desc="Major radius at the start", default=0.5, min_val=0.0, max_val=50.0)
    socket(iface, name="End Radius", in_out='INPUT', socket_type='NodeSocketFloat', desc="Major radius at the end", default=5.0, min_val=0.0, max_val=50.0)
    socket(iface, name="Duration (s)", in_out='INPUT', socket_type='NodeSocketFloat', desc="Time for the expansion", default=4.0, min_val=0.1, max_val=100.0)
    socket(iface, name="Torus Thickness", in_out='INPUT', socket_type='NodeSocketFloat', desc="Thickness of the torus ring", default=0.25, min_val=0.01, max_val=10.0)
    socket(iface, name="Path Resolution", in_out='INPUT', socket_type='NodeSocketInt', desc="Resolution of the main path", default=128, min_val=3, max_val=512)
    socket(iface, name="Profile Resolution", in_out='INPUT', socket_type='NodeSocketInt', desc="Resolution of the profile", default=32, min_val=3, max_val=256)
    socket(iface, name="Wave Amplitude", in_out='INPUT', socket_type='NodeSocketFloat', desc="Height of the wave displacement", default=0.5, min_val=0.0, max_val=10.0)
    socket(iface, name="Wave Frequency", in_out='INPUT', socket_type='NodeSocketFloat', desc="Number of waves around the torus", default=8.0, min_val=0.0, max_val=64.0)
    socket(iface, name="Wave Speed", in_out='INPUT', socket_type='NodeSocketFloat', desc="Speed of the wave animation", default=2.0, min_val=-20.0, max_val=20.0)
    socket(iface, name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry', desc="Final output geometry")

    # ---- 2. Node Graph Construction ----
    n_in = new_node(nodes, 'NodeGroupInput', location=(-1600, 0))
    n_out = new_node(nodes, 'NodeGroupOutput', location=(800, 100))

    # Time driver
    time_val = new_node(nodes, 'ShaderNodeValue', location=(-1600, -300)); time_val.label = "Time (s)"
    safe_time_driver(time_val)

    # Animate the major radius
    map_radius = new_node(nodes, 'ShaderNodeMapRange', location=(-1400, 100)); map_radius.clamp = True
    links.new(time_val.outputs['Value'], map_radius.inputs['Value'])
    links.new(n_in.outputs['Duration (s)'], map_radius.inputs['From Max'])
    links.new(n_in.outputs['Start Radius'], map_radius.inputs['To Min'])
    links.new(n_in.outputs['End Radius'], map_radius.inputs['To Max'])

    # Create the main horizontal path circle
    path_circle = new_node(nodes, 'GeometryNodeCurvePrimitiveCircle', location=(-1200, 100))
    links.new(n_in.outputs['Path Resolution'], path_circle.inputs['Resolution'])
    links.new(map_radius.outputs['Result'], path_circle.inputs['Radius'])

    # --- Sine Wave Displacement ---
    set_pos = new_node(nodes, 'GeometryNodeSetPosition', location=(-1000, 100))
    links.new(path_circle.outputs['Curve'], set_pos.inputs['Geometry'])

    spline_param = new_node(nodes, 'GeometryNodeSplineParameter', location=(-1600, 400))
    
    # Wave Angle = (Factor * 2PI * Frequency) + (Time * Speed)
    factor_to_rad = new_node(nodes, 'ShaderNodeMath', location=(-1400, 400)); factor_to_rad.operation = 'MULTIPLY'; factor_to_rad.inputs[1].default_value = 2 * math.pi
    links.new(spline_param.outputs['Factor'], factor_to_rad.inputs[0])

    freq_mult = new_node(nodes, 'ShaderNodeMath', location=(-1200, 400)); freq_mult.operation = 'MULTIPLY'
    links.new(factor_to_rad.outputs['Value'], freq_mult.inputs[0])
    links.new(n_in.outputs['Wave Frequency'], freq_mult.inputs[1])

    time_mult = new_node(nodes, 'ShaderNodeMath', location=(-1200, 250)); time_mult.operation = 'MULTIPLY'
    links.new(time_val.outputs['Value'], time_mult.inputs[0])
    links.new(n_in.outputs['Wave Speed'], time_mult.inputs[1])

    add_phase = new_node(nodes, 'ShaderNodeMath', location=(-1000, 350)); add_phase.operation = 'ADD'
    links.new(freq_mult.outputs['Value'], add_phase.inputs[0])
    links.new(time_mult.outputs['Value'], add_phase.inputs[1])

    # Final Wave Value = sin(Wave Angle) * Amplitude
    wave_sine = new_node(nodes, 'ShaderNodeMath', location=(-800, 350)); wave_sine.operation = 'SINE'
    links.new(add_phase.outputs['Value'], wave_sine.inputs[0])

    wave_amp = new_node(nodes, 'ShaderNodeMath', location=(-600, 350)); wave_amp.operation = 'MULTIPLY'
    links.new(wave_sine.outputs['Value'], wave_amp.inputs[0])
    links.new(n_in.outputs['Wave Amplitude'], wave_amp.inputs[1])

    # Create Z-axis displacement vector and apply it
    disp_vec = new_node(nodes, 'ShaderNodeCombineXYZ', location=(-800, 100))
    links.new(wave_amp.outputs['Value'], disp_vec.inputs['Z'])
    links.new(disp_vec.outputs['Vector'], set_pos.inputs['Offset'])
    # --- End Sine Wave ---

    # Create the profile circle for the torus thickness
    profile_circle = new_node(nodes, 'GeometryNodeCurvePrimitiveCircle', location=(-800, -100))
    links.new(n_in.outputs['Profile Resolution'], profile_circle.inputs['Resolution'])
    links.new(n_in.outputs['Torus Thickness'], profile_circle.inputs['Radius'])

    # Create the torus mesh
    curve_to_mesh = new_node(nodes, 'GeometryNodeCurveToMesh', location=(-600, 100))
    links.new(set_pos.outputs['Geometry'], curve_to_mesh.inputs['Curve'])
    links.new(profile_circle.outputs['Curve'], curve_to_mesh.inputs['Profile Curve'])

    # Final output
    links.new(curve_to_mesh.outputs['Mesh'], n_out.inputs['Geometry'])

def setup_and_run():
    """Primary function to set up the scene and run the node tree creation."""
    print("--- Starting Wavy Torus Script ---")
    
    if bpy.context.scene.objects:
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)

    obj = ensure_active_object()
    obj.name = "WavyTorusObject"

    ng = new_gn_group("WavyTorusTree")
    build_wavy_torus_tree(ng)
    
    mod = attach_group_modifier(obj, ng, "WavyTorusModifier")

    print(f"Successfully created and assigned '{ng.name}' to modifier '{mod.name}' on object '{obj.name}'.")
    print("--- Wavy Torus Script Finished ---")

if __name__ == "__main__":
    setup_and_run()
