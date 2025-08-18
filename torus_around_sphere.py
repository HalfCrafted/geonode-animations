# Blender 4.4 - "Torus Wave Effect" Geometry Nodes Script
# Creates a single torus that travels from pole to pole on the surface of a virtual sphere.

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

# Ensure there is an active object to work with
if bpy.context.active_object is None:
    bpy.ops.mesh.primitive_plane_add()
OBJ = bpy.context.active_object
# === End Safety Header =====================================================

def build_torus_wave_tree(ng):
    """Constructs the node tree for the torus wave effect."""
    nodes, links, iface = ng.nodes, ng.links, ng.interface

    # ---- Interface Definition ----
    socket(iface, name="Sphere Radius", in_out='INPUT', socket_type='NodeSocketFloat', desc="Radius of the invisible sphere stage", default=5.0, min_val=0.1, max_val=50.0)
    socket(iface, name="Duration (s)", in_out='INPUT', socket_type='NodeSocketFloat', desc="How long the pole-to-pole animation takes", default=5.0, min_val=0.1, max_val=300.0)
    socket(iface, name="Torus Thickness", in_out='INPUT', socket_type='NodeSocketFloat', desc="The thickness (minor radius) of the torus ring", default=0.2, min_val=0.01, max_val=10.0)
    socket(iface, name="Path Resolution", in_out='INPUT', socket_type='NodeSocketInt', desc="Resolution of the main path circle (more is smoother)", default=128, min_val=3, max_val=512)
    socket(iface, name="Torus Resolution", in_out='INPUT', socket_type='NodeSocketInt', desc="Resolution of the torus profile (how smooth the tube is)", default=32, min_val=3, max_val=256)
    socket(iface, name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry', desc="The final torus geometry")

    # ---- Node Graph Construction ----
    n_in = new_node(nodes, 'NodeGroupInput', location=(-1200, 0))
    n_out = new_node(nodes, 'NodeGroupOutput', location=(400, 100))

    # 1. Time Driver
    time_val = new_node(nodes, 'ShaderNodeValue', location=(-1200, -300))
    time_val.label = "Time (Seconds)"
    safe_time_driver(time_val)

    # 2. Map time to a pole-to-pole angle (0 to PI)
    map_angle = new_node(nodes, 'ShaderNodeMapRange', location=(-1000, 100))
    map_angle.clamp = True
    map_angle.inputs['To Max'].default_value = math.pi
    links.new(time_val.outputs['Value'], map_angle.inputs['Value'])
    links.new(n_in.outputs['Duration (s)'], map_angle.inputs['From Max'])
    phi_angle = map_angle.outputs['Result']

    # 3. Calculate ring radius and height from angle (Spherical Coordinates)
    sin_phi = new_node(nodes, 'ShaderNodeMath', location=(-800, 200)); sin_phi.operation = 'SINE'
    links.new(phi_angle, sin_phi.inputs[0])
    ring_radius = new_node(nodes, 'ShaderNodeMath', location=(-600, 200)); ring_radius.operation = 'MULTIPLY'
    links.new(n_in.outputs['Sphere Radius'], ring_radius.inputs[0])
    links.new(sin_phi.outputs['Value'], ring_radius.inputs[1])

    cos_phi = new_node(nodes, 'ShaderNodeMath', location=(-800, 0)); cos_phi.operation = 'COSINE'
    links.new(phi_angle, cos_phi.inputs[0])
    ring_height_z = new_node(nodes, 'ShaderNodeMath', location=(-600, 0)); ring_height_z.operation = 'MULTIPLY'
    links.new(n_in.outputs['Sphere Radius'], ring_height_z.inputs[0])
    links.new(cos_phi.outputs['Value'], ring_height_z.inputs[1])

    # 4. Create the main path curve and move it to the correct height
    path_circle = new_node(nodes, 'GeometryNodeCurvePrimitiveCircle', location=(-400, 200))
    links.new(n_in.outputs['Path Resolution'], path_circle.inputs['Resolution'])
    links.new(ring_radius.outputs['Value'], path_circle.inputs['Radius'])

    height_vector = new_node(nodes, 'ShaderNodeCombineXYZ', location=(-200, 0))
    links.new(ring_height_z.outputs['Value'], height_vector.inputs['Z'])

    set_pos = new_node(nodes, 'GeometryNodeSetPosition', location=(0, 100))
    links.new(path_circle.outputs['Curve'], set_pos.inputs['Geometry'])
    links.new(height_vector.outputs['Vector'], set_pos.inputs['Offset'])

    # 5. Create the profile curve for the torus thickness
    profile_circle = new_node(nodes, 'GeometryNodeCurvePrimitiveCircle', location=(0, -100))
    links.new(n_in.outputs['Torus Resolution'], profile_circle.inputs['Resolution'])
    links.new(n_in.outputs['Torus Thickness'], profile_circle.inputs['Radius'])

    # 6. Convert the path curve to a mesh (the torus)
    curve_to_mesh = new_node(nodes, 'GeometryNodeCurveToMesh', location=(200, 100))
    links.new(set_pos.outputs['Geometry'], curve_to_mesh.inputs['Curve'])
    links.new(profile_circle.outputs['Curve'], curve_to_mesh.inputs['Profile Curve'])

    # 7. Output the final geometry
    links.new(curve_to_mesh.outputs['Mesh'], n_out.inputs['Geometry'])

def setup_and_run():
    """Primary function to set up the scene and run the node tree creation."""
    ng = new_gn_group("Torus Wave Effect")
    build_torus_wave_tree(ng)
    attach_group_modifier(OBJ, ng, "Torus Wave")
    print(f"Created and assigned '{ng.name}' to modifier on object '{OBJ.name}'.")

# --- Execute the script ---
setup_and_run()
