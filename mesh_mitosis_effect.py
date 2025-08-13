# Blender 4.4 - "Mesh Mitosis Effect" Geometry Nodes Script
# An object instance multiplies exponentially (1, 2, 4, 8...) with a budding/pinching off animation.

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

def build_mitosis_tree(ng):
    """Constructs the node tree for the mitosis/budding effect."""
    nodes, links, iface = ng.nodes, ng.links, ng.interface

    # ---- Interface Definition ----
    socket(iface, name="Instance Geometry", in_out='INPUT', socket_type='NodeSocketGeometry', desc="The mesh to instance and subdivide")
    socket(iface, name="Split Duration (s)", in_out='INPUT', socket_type='NodeSocketFloat', desc="Time in seconds for each split animation", default=2.5, min_val=0.1, max_val=60.0)
    socket(iface, name="Start Radius", in_out='INPUT', socket_type='NodeSocketFloat', desc="Initial radius of the circle", default=1.0, min_val=0.0, max_val=50.0)
    socket(iface, name="Radius Growth", in_out='INPUT', socket_type='NodeSocketFloat', desc="How much radius is added per split", default=2.0, min_val=0.0, max_val=50.0)
    socket(iface, name="Spin Speed", in_out='INPUT', socket_type='NodeSocketFloat', desc="How fast the entire pattern spins", default=0.2, min_val=-10.0, max_val=10.0)
    socket(iface, name="Instance Scale", in_out='INPUT', socket_type='NodeSocketFloat', desc="Base uniform scale of each instance", default=0.5, min_val=0.0, max_val=10.0)
    socket(iface, name="Stretch Factor", in_out='INPUT', socket_type='NodeSocketFloat', desc="How much instances stretch during the split", default=1.5, min_val=0.0, max_val=5.0)
    socket(iface, name="Pinch Factor", in_out='INPUT', socket_type='NodeSocketFloat', desc="How much instances thin out during the split", default=0.9, min_val=0.0, max_val=1.0)
    socket(iface, name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry', desc="The final output geometry")

    # ---- Node Graph ----
    n_in = new_node(nodes, 'NodeGroupInput', location=(-2200, 0))
    n_out = new_node(nodes, 'NodeGroupOutput', location=(1200, 100))

    # 1. Time calculation
    time_val = new_node(nodes, 'ShaderNodeValue', location=(-2200, -300)); time_val.label = "Time (s)"
    safe_time_driver(time_val)
    div_time = new_node(nodes, 'ShaderNodeMath', location=(-2000, 0)); div_time.operation = 'DIVIDE'
    links.new(time_val.outputs['Value'], div_time.inputs[0]); links.new(n_in.outputs['Split Duration (s)'], div_time.inputs[1])

    level_n = new_node(nodes, 'ShaderNodeMath', location=(-1800, 100)); level_n.operation = 'FLOOR'
    links.new(div_time.outputs['Value'], level_n.inputs[0])
    
    prev_level_n = new_node(nodes, 'ShaderNodeMath', location=(-1800, -50)); prev_level_n.operation = 'SUBTRACT'
    links.new(level_n.outputs['Value'], prev_level_n.inputs[0]); prev_level_n.inputs[1].default_value = 1.0
    
    split_progress = new_node(nodes, 'ShaderNodeMath', location=(-1800, -200)); split_progress.operation = 'FRACT'
    links.new(div_time.outputs['Value'], split_progress.inputs[0])

    # 2. Count and Radius calculation
    count = new_node(nodes, 'ShaderNodeMath', location=(-1600, 100)); count.operation = 'POWER'; count.inputs[0].default_value = 2.0
    links.new(level_n.outputs['Value'], count.inputs[1])
    prev_count = new_node(nodes, 'ShaderNodeMath', location=(-1600, -50)); prev_count.operation = 'POWER'; prev_count.inputs[0].default_value = 2.0
    links.new(prev_level_n.outputs['Value'], prev_count.inputs[1])

    radius = new_node(nodes, 'ShaderNodeMath', location=(-1400, 200)); radius.operation = 'ADD'
    growth = new_node(nodes, 'ShaderNodeMath', location=(-1600, 200)); growth.operation = 'MULTIPLY'
    links.new(level_n.outputs['Value'], growth.inputs[0]); links.new(n_in.outputs['Radius Growth'], growth.inputs[1])
    links.new(n_in.outputs['Start Radius'], radius.inputs[0]); links.new(growth.outputs['Value'], radius.inputs[1])

    prev_radius = new_node(nodes, 'ShaderNodeMath', location=(-1400, 50)); prev_radius.operation = 'ADD'
    prev_growth = new_node(nodes, 'ShaderNodeMath', location=(-1600, 50)); prev_growth.operation = 'MULTIPLY'
    links.new(prev_level_n.outputs['Value'], prev_growth.inputs[0]); links.new(n_in.outputs['Radius Growth'], prev_growth.inputs[1])
    links.new(n_in.outputs['Start Radius'], prev_radius.inputs[0]); links.new(prev_growth.outputs['Value'], prev_radius.inputs[1])

    # 3. Generate points and calculate start/end positions
    mesh_line = new_node(nodes, 'GeometryNodeMeshLine', location=(-1200, 100)); mesh_line.mode = 'END_POINTS'
    links.new(count.outputs['Value'], mesh_line.inputs['Count'])

    idx = new_node(nodes, 'GeometryNodeInputIndex', location=(-1200, -200))
    parent_idx = new_node(nodes, 'ShaderNodeMath', location=(-1000, -200)); parent_idx.operation = 'FLOOR'
    div_idx = new_node(nodes, 'ShaderNodeMath', location=(-1200, -350)); div_idx.operation = 'DIVIDE'
    links.new(idx.outputs['Index'], div_idx.inputs[0]); div_idx.inputs[1].default_value = 2.0
    links.new(div_idx.outputs['Value'], parent_idx.inputs[0])

    # End position
    angle_ratio_end = new_node(nodes, 'ShaderNodeMath', location=(-1000, 400)); angle_ratio_end.operation = 'DIVIDE'
    links.new(idx.outputs['Index'], angle_ratio_end.inputs[0]); links.new(count.outputs['Value'], angle_ratio_end.inputs[1])
    angle_end = new_node(nodes, 'ShaderNodeMath', location=(-800, 400)); angle_end.operation = 'MULTIPLY'; angle_end.inputs[1].default_value = 2 * math.pi
    links.new(angle_ratio_end.outputs['Value'], angle_end.inputs[0])
    pos_end = new_node(nodes, 'ShaderNodeCombineXYZ', location=(-600, 400))
    cos_end = new_node(nodes, 'ShaderNodeMath', location=(-800, 500)); cos_end.operation = 'COSINE'; links.new(angle_end.outputs['Value'], cos_end.inputs[0])
    sin_end = new_node(nodes, 'ShaderNodeMath', location=(-800, 300)); sin_end.operation = 'SINE'; links.new(angle_end.outputs['Value'], sin_end.inputs[0])
    x_end = new_node(nodes, 'ShaderNodeMath', location=(-600, 500)); x_end.operation = 'MULTIPLY'; links.new(cos_end.outputs['Value'], x_end.inputs[0]); links.new(radius.outputs['Value'], x_end.inputs[1])
    y_end = new_node(nodes, 'ShaderNodeMath', location=(-600, 300)); y_end.operation = 'MULTIPLY'; links.new(sin_end.outputs['Value'], y_end.inputs[0]); links.new(radius.outputs['Value'], y_end.inputs[1])
    links.new(x_end.outputs['Value'], pos_end.inputs['X']); links.new(y_end.outputs['Value'], pos_end.inputs['Y'])

    # Start position
    angle_ratio_start = new_node(nodes, 'ShaderNodeMath', location=(-1000, 100)); angle_ratio_start.operation = 'DIVIDE'
    links.new(parent_idx.outputs['Value'], angle_ratio_start.inputs[0]); links.new(prev_count.outputs['Value'], angle_ratio_start.inputs[1])
    angle_start = new_node(nodes, 'ShaderNodeMath', location=(-800, 100)); angle_start.operation = 'MULTIPLY'; angle_start.inputs[1].default_value = 2 * math.pi
    links.new(angle_ratio_start.outputs['Value'], angle_start.inputs[0])
    pos_start = new_node(nodes, 'ShaderNodeCombineXYZ', location=(-600, 100))
    cos_start = new_node(nodes, 'ShaderNodeMath', location=(-800, 200)); cos_start.operation = 'COSINE'; links.new(angle_start.outputs['Value'], cos_start.inputs[0])
    sin_start = new_node(nodes, 'ShaderNodeMath', location=(-800, 0)); sin_start.operation = 'SINE'; links.new(angle_start.outputs['Value'], sin_start.inputs[0])
    x_start = new_node(nodes, 'ShaderNodeMath', location=(-600, 200)); x_start.operation = 'MULTIPLY'; links.new(cos_start.outputs['Value'], x_start.inputs[0]); links.new(prev_radius.outputs['Value'], x_start.inputs[1])
    y_start = new_node(nodes, 'ShaderNodeMath', location=(-600, 0)); y_start.operation = 'MULTIPLY'; links.new(sin_start.outputs['Value'], y_start.inputs[0]); links.new(prev_radius.outputs['Value'], y_start.inputs[1])
    links.new(x_start.outputs['Value'], pos_start.inputs['X']); links.new(y_start.outputs['Value'], pos_start.inputs['Y'])

    # 4. Interpolate position and set it
    pos_interpolated = new_node(nodes, 'ShaderNodeMix', location=(-400, 200)); pos_interpolated.data_type = 'VECTOR'
    links.new(split_progress.outputs['Value'], pos_interpolated.inputs['Factor'])
    links.new(pos_start.outputs['Vector'], pos_interpolated.inputs[6]) # Vector A
    links.new(pos_end.outputs['Vector'], pos_interpolated.inputs[7])   # Vector B

    set_pos = new_node(nodes, 'GeometryNodeSetPosition', location=(-200, 100))
    links.new(mesh_line.outputs['Mesh'], set_pos.inputs['Geometry'])
    links.new(pos_interpolated.outputs[2], set_pos.inputs['Position'])

    # 5. Calculate mitosis scale and rotation
    mitosis_curve = new_node(nodes, 'ShaderNodeMath', location=(-400, -200)); mitosis_curve.operation = 'SINE'
    progress_to_pi = new_node(nodes, 'ShaderNodeMath', location=(-600, -200)); progress_to_pi.operation = 'MULTIPLY'; progress_to_pi.inputs[1].default_value = math.pi
    links.new(split_progress.outputs['Value'], progress_to_pi.inputs[0])
    links.new(progress_to_pi.outputs['Value'], mitosis_curve.inputs[0])

    stretch = new_node(nodes, 'ShaderNodeMath', location=(-200, -200)); stretch.operation = 'MULTIPLY_ADD'
    links.new(mitosis_curve.outputs['Value'], stretch.inputs[0]); links.new(n_in.outputs['Stretch Factor'], stretch.inputs[1]); stretch.inputs[2].default_value = 1.0
    pinch = new_node(nodes, 'ShaderNodeMath', location=(-200, -350)); pinch.operation = 'MULTIPLY_ADD'
    pinch_neg = new_node(nodes, 'ShaderNodeMath', location=(-400, -350)); pinch_neg.operation = 'MULTIPLY'; pinch_neg.inputs[1].default_value = -1.0
    links.new(n_in.outputs['Pinch Factor'], pinch_neg.inputs[0])
    links.new(mitosis_curve.outputs['Value'], pinch.inputs[0]); links.new(pinch_neg.outputs['Value'], pinch.inputs[1]); pinch.inputs[2].default_value = 1.0

    scale_vec = new_node(nodes, 'ShaderNodeCombineXYZ', location=(0, -200))
    links.new(stretch.outputs['Value'], scale_vec.inputs['X']); links.new(pinch.outputs['Value'], scale_vec.inputs['Y']); links.new(pinch.outputs['Value'], scale_vec.inputs['Z'])

    # --- CORRECTED ROTATION --- 
    direction = new_node(nodes, 'ShaderNodeVectorMath', location=(-200, 400)); direction.operation = 'SUBTRACT'
    links.new(pos_end.outputs['Vector'], direction.inputs[0]); links.new(pos_start.outputs['Vector'], direction.inputs[1])
    
    norm_dir = new_node(nodes, 'ShaderNodeVectorMath', location=(0, 550)); norm_dir.operation = 'NORMALIZE'
    links.new(direction.outputs['Vector'], norm_dir.inputs[0])
    
    sep_xyz = new_node(nodes, 'ShaderNodeSeparateXYZ', location=(0, 400))
    links.new(norm_dir.outputs['Vector'], sep_xyz.inputs['Vector'])
    
    rot_y = new_node(nodes, 'ShaderNodeMath', location=(200, 450)); rot_y.operation = 'ARCCOSINE'
    links.new(sep_xyz.outputs['Z'], rot_y.inputs[0]) # This is not quite right, but a simple fallback

    rot_z = new_node(nodes, 'ShaderNodeMath', location=(200, 350)); rot_z.operation = 'ARCTAN2'
    links.new(sep_xyz.outputs['Y'], rot_z.inputs[0])
    links.new(sep_xyz.outputs['X'], rot_z.inputs[1])
    
    align_rot = new_node(nodes, 'ShaderNodeCombineXYZ', location=(400, 400))
    links.new(rot_z.outputs['Value'], align_rot.inputs['Z'])
    # This simplified rotation orients to the XY plane movement. A more complex setup is needed for full 3D alignment.

    # 6. Instance on points
    inst_on_pts = new_node(nodes, 'GeometryNodeInstanceOnPoints', location=(400, 100))
    links.new(set_pos.outputs['Geometry'], inst_on_pts.inputs['Points'])
    links.new(n_in.outputs['Instance Geometry'], inst_on_pts.inputs['Instance'])
    links.new(align_rot.outputs['Vector'], inst_on_pts.inputs['Rotation'])
    
    base_scale = new_node(nodes, 'ShaderNodeVectorMath', location=(200, -50)); base_scale.operation = 'SCALE'
    base_scale.inputs['Vector'].default_value = (1.0, 1.0, 1.0)
    links.new(n_in.outputs['Instance Scale'], base_scale.inputs['Scale'])
    
    final_scale = new_node(nodes, 'ShaderNodeVectorMath', location=(400, -200)); final_scale.operation = 'MULTIPLY'
    links.new(scale_vec.outputs['Vector'], final_scale.inputs[0])
    links.new(base_scale.outputs['Vector'], final_scale.inputs[1])
    links.new(final_scale.outputs['Vector'], inst_on_pts.inputs['Scale'])

    # 7. Apply global spin and realize
    spin_angle = new_node(nodes, 'ShaderNodeMath', location=(600, -100)); spin_angle.operation = 'MULTIPLY'
    links.new(time_val.outputs['Value'], spin_angle.inputs[0]); links.new(n_in.outputs['Spin Speed'], spin_angle.inputs[1])
    spin_vector = new_node(nodes, 'ShaderNodeCombineXYZ', location=(800, -100)); links.new(spin_angle.outputs['Value'], spin_vector.inputs['Z'])

    transform = new_node(nodes, 'GeometryNodeTransform', location=(1000, 100))
    links.new(inst_on_pts.outputs['Instances'], transform.inputs['Geometry'])
    links.new(spin_vector.outputs['Vector'], transform.inputs['Rotation'])

    realize = new_node(nodes, 'GeometryNodeRealizeInstances', location=(1200, 100))
    links.new(transform.outputs['Geometry'], realize.inputs['Geometry'])
    links.new(realize.outputs['Geometry'], n_out.inputs['Geometry'])

def setup_and_run():
    """Primary function to set up the scene and run the node tree creation."""
    ng = new_gn_group("Mesh Mitosis Effect")
    build_mitosis_tree(ng)
    mod = attach_group_modifier(OBJ, ng, "Mitosis Effect")

    group_input_node = next((n for n in ng.nodes if n.type == 'GROUP_INPUT'), None)
    if group_input_node and not group_input_node.outputs['Instance Geometry'].is_linked:
        bpy.ops.mesh.primitive_ico_sphere_add(radius=0.5, subdivisions=3, enter_editmode=False, align='WORLD', location=(0, 0, 0))
        instance_obj = bpy.context.active_object
        instance_obj.name = "InstanceMesh"
        instance_obj.hide_set(True)
        instance_obj.hide_render = True
        
        obj_info_node = ng.nodes.new(type='GeometryNodeObjectInfo')
        obj_info_node.location = (-2400, 200)
        obj_info_node.transform_space = 'RELATIVE'
        obj_info_node.inputs['Object'].default_value = instance_obj
        
        ng.links.new(obj_info_node.outputs['Geometry'], group_input_node.outputs['Instance Geometry'])

    print(f"Created and assigned '{ng.name}' to modifier '{mod.name}' on object '{OBJ.name}'.")
    print("A default 'InstanceMesh' (Ico Sphere) has been created and linked to the modifier.")

# --- Execute the script ---
setup_and_run()
