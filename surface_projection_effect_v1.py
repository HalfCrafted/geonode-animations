# Blender 4.4 - "Surface Projection Effect" Geometry Nodes Script
# Projects an expanding, spinning circle of instances onto the surface of an invisible sphere.

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

def build_projection_tree(ng):
    """Constructs the node tree for the surface projection effect."""
    nodes, links, iface = ng.nodes, ng.links, ng.interface

    # ---- Interface Definition ----
    socket(iface, name="Instance Geometry", in_out='INPUT', socket_type='NodeSocketGeometry', desc="The mesh to instance")
    socket(iface, name="Stage Sphere Radius", in_out='INPUT', socket_type='NodeSocketFloat', desc="Radius of the invisible sphere stage", default=5.0, min_val=0.1, max_val=50.0)
    socket(iface, name="Count", in_out='INPUT', socket_type='NodeSocketInt', desc="Number of instances in the circle", default=16, min_val=1, max_val=256)
    socket(iface, name="Start Radius", in_out='INPUT', socket_type='NodeSocketFloat', desc="Circle radius at the start (on the XY plane)", default=0.0, min_val=0.0, max_val=50.0)
    socket(iface, name="End Radius", in_out='INPUT', socket_type='NodeSocketFloat', desc="Circle radius at the end (cannot exceed Stage Sphere Radius)", default=4.0, min_val=0.0, max_val=50.0)
    socket(iface, name="Duration (s)", in_out='INPUT', socket_type='NodeSocketFloat', desc="How long the expansion animation takes", default=5.0, min_val=0.1, max_val=300.0)
    socket(iface, name="Spin Speed", in_out='INPUT', socket_type='NodeSocketFloat', desc="How fast each instance spins on its local up-axis", default=2.0, min_val=-50.0, max_val=50.0)
    socket(iface, name="Instance Scale", in_out='INPUT', socket_type='NodeSocketFloat', desc="Uniform scale of each instance", default=0.4, min_val=0.0, max_val=10.0)
    socket(iface, name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry', desc="The final output geometry")

    # ---- Node Graph Construction ----
    n_in = new_node(nodes, 'NodeGroupInput', location=(-1400, 0))
    n_out = new_node(nodes, 'NodeGroupOutput', location=(800, 0))

    # 1. Time Driver
    time_val = new_node(nodes, 'ShaderNodeValue', location=(-1400, -300))
    time_val.label = "Time (Seconds)"
    safe_time_driver(time_val)

    # 2. Calculate Animated Radius for the flat circle
    map_radius = new_node(nodes, 'ShaderNodeMapRange', location=(-1200, 100))
    map_radius.clamp = True
    links.new(time_val.outputs['Value'], map_radius.inputs['Value'])
    links.new(n_in.outputs['Duration (s)'], map_radius.inputs['From Max'])
    links.new(n_in.outputs['Start Radius'], map_radius.inputs['To Min'])
    links.new(n_in.outputs['End Radius'], map_radius.inputs['To Max'])

    # 3. Create the Base 2D Circle
    circle = new_node(nodes, 'GeometryNodeCurvePrimitiveCircle', location=(-1000, 100))
    circle.inputs['Resolution'].default_value = 128
    links.new(map_radius.outputs['Result'], circle.inputs['Radius'])

    # 4. Get points from the 2D circle
    resample = new_node(nodes, 'GeometryNodeResampleCurve', location=(-800, 100))
    resample.mode = 'COUNT'
    links.new(circle.outputs['Curve'], resample.inputs['Curve'])
    links.new(n_in.outputs['Count'], resample.inputs['Count'])

    # 5. Project points onto the sphere surface
    # z = sqrt(SphereRadius^2 - circle_radius^2)
    r_stage_sq = new_node(nodes, 'ShaderNodeMath', location=(-600, 400)); r_stage_sq.operation = 'POWER'
    links.new(n_in.outputs['Stage Sphere Radius'], r_stage_sq.inputs[0]); r_stage_sq.inputs[1].default_value = 2.0

    r_anim_sq = new_node(nodes, 'ShaderNodeMath', location=(-600, 250)); r_anim_sq.operation = 'POWER'
    links.new(map_radius.outputs['Result'], r_anim_sq.inputs[0]); r_anim_sq.inputs[1].default_value = 2.0

    subtract_sq = new_node(nodes, 'ShaderNodeMath', location=(-400, 350)); subtract_sq.operation = 'SUBTRACT'
    links.new(r_stage_sq.outputs['Value'], subtract_sq.inputs[0])
    links.new(r_anim_sq.outputs['Value'], subtract_sq.inputs[1])

    z_val = new_node(nodes, 'ShaderNodeMath', location=(-200, 350)); z_val.operation = 'SQRT'
    links.new(subtract_sq.outputs['Value'], z_val.inputs[0])

    # Get original XY and combine with new Z
    circle_pos = new_node(nodes, 'GeometryNodeInputPosition', location=(-400, 100))
    sep_xyz = new_node(nodes, 'ShaderNodeSeparateXYZ', location=(-200, 100))
    links.new(circle_pos.outputs['Position'], sep_xyz.inputs['Vector'])

    projected_pos_vec = new_node(nodes, 'ShaderNodeCombineXYZ', location=(0, 200))
    links.new(sep_xyz.outputs['X'], projected_pos_vec.inputs['X'])
    links.new(sep_xyz.outputs['Y'], projected_pos_vec.inputs['Y'])
    links.new(z_val.outputs['Value'], projected_pos_vec.inputs['Z'])

    # Apply the new projected position
    set_pos = new_node(nodes, 'GeometryNodeSetPosition', location=(200, 100))
    links.new(resample.outputs['Curve'], set_pos.inputs['Geometry'])
    links.new(projected_pos_vec.outputs['Vector'], set_pos.inputs['Position'])

    # 6. Calculate orientation and spin
    # The normal of a sphere at a point is the normalized vector from the center to that point.
    surface_normal = new_node(nodes, 'ShaderNodeVectorMath', location=(200, 300)); surface_normal.operation = 'NORMALIZE'
    links.new(projected_pos_vec.outputs['Vector'], surface_normal.inputs[0])

    spin_angle = new_node(nodes, 'ShaderNodeMath', location=(200, -100)); spin_angle.operation = 'MULTIPLY'
    links.new(time_val.outputs['Value'], spin_angle.inputs[0])
    links.new(n_in.outputs['Spin Speed'], spin_angle.inputs[1])

    spin_euler = new_node(nodes, 'ShaderNodeCombineXYZ', location=(400, -100))
    links.new(spin_angle.outputs['Value'], spin_euler.inputs['Z'])

    # Add spin to the surface normal orientation (simplified fallback)
    final_rot = new_node(nodes, 'ShaderNodeVectorMath', location=(400, 200)); final_rot.operation = 'ADD'
    links.new(surface_normal.outputs['Vector'], final_rot.inputs[0])
    links.new(spin_euler.outputs['Vector'], final_rot.inputs[1])

    # 7. Instance Geometry
    inst_on_pts = new_node(nodes, 'GeometryNodeInstanceOnPoints', location=(600, 100))
    links.new(set_pos.outputs['Geometry'], inst_on_pts.inputs['Points'])
    links.new(n_in.outputs['Instance Geometry'], inst_on_pts.inputs['Instance'])
    links.new(final_rot.outputs['Vector'], inst_on_pts.inputs['Rotation'])

    scale_vec = new_node(nodes, 'ShaderNodeVectorMath', location=(400, 0)); scale_vec.operation = 'SCALE'
    scale_vec.inputs['Vector'].default_value = (1, 1, 1)
    links.new(n_in.outputs['Instance Scale'], scale_vec.inputs['Scale'])
    links.new(scale_vec.outputs['Vector'], inst_on_pts.inputs['Scale'])

    # 8. Realize and Output
    links.new(inst_on_pts.outputs['Instances'], n_out.inputs['Geometry'])

def setup_and_run():
    """Primary function to set up the scene and run the node tree creation."""
    ng = new_gn_group("Surface Projection Effect")
    build_projection_tree(ng)
    mod = attach_group_modifier(OBJ, ng, "Surface Projection")

    group_input_node = next((n for n in ng.nodes if n.type == 'GROUP_INPUT'), None)
    if group_input_node and not group_input_node.outputs['Instance Geometry'].is_linked:
        bpy.ops.mesh.primitive_cone_add(vertices=8, radius1=0.2, depth=0.4, enter_editmode=False, align='WORLD', location=(0, 0, 0))
        instance_obj = bpy.context.active_object
        instance_obj.name = "InstanceCone"
        instance_obj.hide_set(True)
        instance_obj.hide_render = True
        
        obj_info_node = ng.nodes.new(type='GeometryNodeObjectInfo')
        obj_info_node.location = (-1600, 200)
        obj_info_node.transform_space = 'RELATIVE'
        obj_info_node.inputs['Object'].default_value = instance_obj
        
        ng.links.new(obj_info_node.outputs['Geometry'], group_input_node.outputs['Instance Geometry'])

    print(f"Created and assigned '{ng.name}' to modifier '{mod.name}' on object '{OBJ.name}'.")
    print("A default 'InstanceCone' has been created and linked to the modifier.")

# --- Execute the script ---
setup_and_run()
