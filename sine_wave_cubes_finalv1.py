# Blender 4.4 - "Sine Wave Cubes Effect (Projected)" Geometry Nodes Script
# This is a corrected version. It projects an expanding circle of cubes onto a sphere,
# with a traveling sine wave modulating their height.

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

def build_sine_wave_cubes_tree(ng):
    """Constructs the node tree for the sine wave cubes effect."""
    nodes, links, iface = ng.nodes, ng.links, ng.interface

    # ---- Interface Definition ----
    socket(iface, name="Stage Sphere Radius", in_out='INPUT', socket_type='NodeSocketFloat', desc="Radius of the invisible sphere stage", default=5.0, min_val=0.1, max_val=50.0)
    socket(iface, name="Count", in_out='INPUT', socket_type='NodeSocketInt', desc="Number of cubes in the circle", default=48, min_val=1, max_val=256)
    socket(iface, name="Start Radius", in_out='INPUT', socket_type='NodeSocketFloat', desc="Circle radius at the start", default=1.0, min_val=0.0, max_val=50.0)
    socket(iface, name="End Radius", in_out='INPUT', socket_type='NodeSocketFloat', desc="Circle radius at the end", default=4.5, min_val=0.0, max_val=50.0)
    socket(iface, name="Duration (s)", in_out='INPUT', socket_type='NodeSocketFloat', desc="How long the expansion animation takes", default=5.0, min_val=0.1, max_val=300.0)
    socket(iface, name="Wave Speed", in_out='INPUT', socket_type='NodeSocketFloat', desc="How fast the sine wave travels around the circle", default=3.0, min_val=-50.0, max_val=50.0)
    socket(iface, name="Wave Frequency", in_out='INPUT', socket_type='NodeSocketFloat', desc="Number of wave cycles around the circle", default=4.0, min_val=0.0, max_val=64.0)
    socket(iface, name="Min Height", in_out='INPUT', socket_type='NodeSocketFloat', desc="Cube height at the trough of the wave", default=0.1, min_val=0.01, max_val=10.0)
    socket(iface, name="Max Height", in_out='INPUT', socket_type='NodeSocketFloat', desc="Cube height at the crest of the wave", default=1.5, min_val=0.01, max_val=10.0)
    socket(iface, name="Cube Width", in_out='INPUT', socket_type='NodeSocketFloat', desc="The width (X and Y size) of the cubes", default=0.2, min_val=0.01, max_val=10.0)
    socket(iface, name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry', desc="The final output geometry")

    # ---- Node Graph Construction ----
    n_in = new_node(nodes, 'NodeGroupInput', location=(-1600, 0))
    n_out = new_node(nodes, 'NodeGroupOutput', location=(1400, 100))

    # 1. Time Driver
    time_val = new_node(nodes, 'ShaderNodeValue', location=(-1600, -300))
    time_val.label = "Time (Seconds)"
    safe_time_driver(time_val)

    # 2. Base expanding circle & projection logic
    map_radius = new_node(nodes, 'ShaderNodeMapRange', location=(-1400, 100))
    map_radius.clamp = True
    links.new(time_val.outputs['Value'], map_radius.inputs['Value'])
    links.new(n_in.outputs['Duration (s)'], map_radius.inputs['From Max'])
    links.new(n_in.outputs['Start Radius'], map_radius.inputs['To Min'])
    links.new(n_in.outputs['End Radius'], map_radius.inputs['To Max'])

    circle = new_node(nodes, 'GeometryNodeCurvePrimitiveCircle', location=(-1200, 100))
    links.new(map_radius.outputs['Result'], circle.inputs['Radius'])

    resample = new_node(nodes, 'GeometryNodeResampleCurve', location=(-1000, 100)); resample.mode = 'COUNT'
    links.new(circle.outputs['Curve'], resample.inputs['Curve'])
    links.new(n_in.outputs['Count'], resample.inputs['Count'])

    r_stage_sq = new_node(nodes, 'ShaderNodeMath', location=(-800, 400)); r_stage_sq.operation = 'POWER'
    links.new(n_in.outputs['Stage Sphere Radius'], r_stage_sq.inputs[0]); r_stage_sq.inputs[1].default_value = 2.0
    r_anim_sq = new_node(nodes, 'ShaderNodeMath', location=(-800, 250)); r_anim_sq.operation = 'POWER'
    links.new(map_radius.outputs['Result'], r_anim_sq.inputs[0]); r_anim_sq.inputs[1].default_value = 2.0
    subtract_sq = new_node(nodes, 'ShaderNodeMath', location=(-600, 350)); subtract_sq.operation = 'SUBTRACT'
    links.new(r_stage_sq.outputs['Value'], subtract_sq.inputs[0]); links.new(r_anim_sq.outputs['Value'], subtract_sq.inputs[1])
    z_val = new_node(nodes, 'ShaderNodeMath', location=(-400, 350)); z_val.operation = 'SQRT'
    links.new(subtract_sq.outputs['Value'], z_val.inputs[0])

    circle_pos = new_node(nodes, 'GeometryNodeInputPosition', location=(-600, 100))
    sep_xyz = new_node(nodes, 'ShaderNodeSeparateXYZ', location=(-400, 100))
    links.new(circle_pos.outputs['Position'], sep_xyz.inputs['Vector'])
    projected_pos_vec = new_node(nodes, 'ShaderNodeCombineXYZ', location=(-200, 200))
    links.new(sep_xyz.outputs['X'], projected_pos_vec.inputs['X']); links.new(sep_xyz.outputs['Y'], projected_pos_vec.inputs['Y']); links.new(z_val.outputs['Value'], projected_pos_vec.inputs['Z'])

    set_pos = new_node(nodes, 'GeometryNodeSetPosition', location=(0, 100))
    links.new(resample.outputs['Curve'], set_pos.inputs['Geometry']); links.new(projected_pos_vec.outputs['Vector'], set_pos.inputs['Position'])

    # 3. Calculate Sine Wave for Z-Scale
    idx = new_node(nodes, 'GeometryNodeInputIndex', location=(-600, -200))
    idx_div_count = new_node(nodes, 'ShaderNodeMath', location=(-400, -200)); idx_div_count.operation = 'DIVIDE'
    links.new(idx.outputs['Index'], idx_div_count.inputs[0]); links.new(n_in.outputs['Count'], idx_div_count.inputs[1])
    mul_2pi = new_node(nodes, 'ShaderNodeMath', location=(-200, -200)); mul_2pi.operation = 'MULTIPLY'
    mul_2pi.inputs[1].default_value = 2 * math.pi
    links.new(idx_div_count.outputs['Value'], mul_2pi.inputs[0])
    mul_freq = new_node(nodes, 'ShaderNodeMath', location=(0, -200)); mul_freq.operation = 'MULTIPLY'
    links.new(mul_2pi.outputs['Value'], mul_freq.inputs[0]); links.new(n_in.outputs['Wave Frequency'], mul_freq.inputs[1])

    time_phase = new_node(nodes, 'ShaderNodeMath', location=(0, -350)); time_phase.operation = 'MULTIPLY'
    links.new(time_val.outputs['Value'], time_phase.inputs[0]); links.new(n_in.outputs['Wave Speed'], time_phase.inputs[1])
    add_phase = new_node(nodes, 'ShaderNodeMath', location=(200, -200)); add_phase.operation = 'ADD'
    links.new(mul_freq.outputs['Value'], add_phase.inputs[0]); links.new(time_phase.outputs['Value'], add_phase.inputs[1])

    wave_val = new_node(nodes, 'ShaderNodeMath', location=(400, -200)); wave_val.operation = 'SINE'
    links.new(add_phase.outputs['Value'], wave_val.inputs[0])

    map_height = new_node(nodes, 'ShaderNodeMapRange', location=(600, -200))
    map_height.inputs['From Min'].default_value = -1.0; map_height.inputs['From Max'].default_value = 1.0
    links.new(wave_val.outputs['Value'], map_height.inputs['Value'])
    links.new(n_in.outputs['Min Height'], map_height.inputs['To Min']); links.new(n_in.outputs['Max Height'], map_height.inputs['To Max'])

    # 4. Create Scale and Rotation vectors
    scale_vec = new_node(nodes, 'ShaderNodeCombineXYZ', location=(800, -100))
    links.new(n_in.outputs['Cube Width'], scale_vec.inputs['X']); links.new(n_in.outputs['Cube Width'], scale_vec.inputs['Y'])
    links.new(map_height.outputs['Result'], scale_vec.inputs['Z'])

    surface_normal = new_node(nodes, 'ShaderNodeVectorMath', location=(200, 400)); surface_normal.operation = 'NORMALIZE'
    links.new(projected_pos_vec.outputs['Vector'], surface_normal.inputs[0])
    sep_norm = new_node(nodes, 'ShaderNodeSeparateXYZ', location=(400, 500)); links.new(surface_normal.outputs['Vector'], sep_norm.inputs['Vector'])
    y_rot = new_node(nodes, 'ShaderNodeMath', location=(600, 550)); y_rot.operation = 'ARCCOSINE'
    links.new(sep_norm.outputs['Z'], y_rot.inputs[0])
    z_rot = new_node(nodes, 'ShaderNodeMath', location=(600, 450)); z_rot.operation = 'ARCTAN2'
    links.new(sep_norm.outputs['Y'], z_rot.inputs[0]); links.new(sep_norm.outputs['X'], z_rot.inputs[1])
    rot_vec = new_node(nodes, 'ShaderNodeCombineXYZ', location=(800, 500))
    links.new(y_rot.outputs['Value'], rot_vec.inputs['Y']); links.new(z_rot.outputs['Value'], rot_vec.inputs['Z'])

    # 5. Create Cube Instance and apply transforms
    cube = new_node(nodes, 'GeometryNodeMeshCube', location=(800, 100))

    inst_on_pts = new_node(nodes, 'GeometryNodeInstanceOnPoints', location=(1000, 100))
    links.new(set_pos.outputs['Geometry'], inst_on_pts.inputs['Points'])
    links.new(cube.outputs['Mesh'], inst_on_pts.inputs['Instance'])
    links.new(rot_vec.outputs['Vector'], inst_on_pts.inputs['Rotation'])
    links.new(scale_vec.outputs['Vector'], inst_on_pts.inputs['Scale'])

    # 6. Realize Instances and Output
    realize = new_node(nodes, 'GeometryNodeRealizeInstances', location=(1200, 100))
    links.new(inst_on_pts.outputs['Instances'], realize.inputs['Geometry'])
    links.new(realize.outputs['Geometry'], n_out.inputs['Geometry'])

def setup_and_run():
    """Primary function to set up the scene and run the node tree creation."""
    ng = new_gn_group("Sine Wave Cubes Effect")
    build_sine_wave_cubes_tree(ng)
    attach_group_modifier(OBJ, ng, "Sine Wave Cubes")
    print(f"Created and assigned '{ng.name}' to modifier on object '{OBJ.name}'.")

# --- Execute the script ---
setup_and_run()
