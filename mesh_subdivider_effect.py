# Blender 4.4 - "Exponential Mesh Subdivider" Geometry Nodes Script
# An object instance multiplies exponentially (1, 2, 4, 8...) in a spinning, expanding circle.

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

def build_subdivider_tree(ng):
    """Constructs the node tree for the exponential subdivider effect."""
    nodes, links, iface = ng.nodes, ng.links, ng.interface

    # ---- Interface Definition ----
    socket(iface, name="Instance Geometry", in_out='INPUT', socket_type='NodeSocketGeometry', desc="The mesh to instance and subdivide")
    socket(iface, name="Split Duration (s)", in_out='INPUT', socket_type='NodeSocketFloat', desc="Time in seconds between each subdivision event", default=2.0, min_val=0.1, max_val=60.0)
    socket(iface, name="Start Radius", in_out='INPUT', socket_type='NodeSocketFloat', desc="Radius of the circle before the first split", default=0.0, min_val=0.0, max_val=50.0)
    socket(iface, name="Radius Growth", in_out='INPUT', socket_type='NodeSocketFloat', desc="How much the radius expands after each split", default=1.5, min_val=0.0, max_val=50.0)
    socket(iface, name="Spin Speed", in_out='INPUT', socket_type='NodeSocketFloat', desc="How fast the entire pattern spins (radians/sec)", default=0.5, min_val=-10.0, max_val=10.0)
    socket(iface, name="Instance Scale", in_out='INPUT', socket_type='NodeSocketFloat', desc="Uniform scale of each instance", default=0.8, min_val=0.0, max_val=10.0)
    socket(iface, name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry', desc="The final output geometry")

    # ---- Node Graph Construction ----
    n_in = new_node(nodes, 'NodeGroupInput', location=(-1600, 0))
    n_out = new_node(nodes, 'NodeGroupOutput', location=(800, 100))

    # 1. Time Driver
    time_val = new_node(nodes, 'ShaderNodeValue', location=(-1600, -300)); time_val.label = "Time (s)"
    safe_time_driver(time_val)

    # 2. Calculate subdivision level (N) and instance count (2^N)
    # N = floor(time / duration)
    level_n = new_node(nodes, 'ShaderNodeMath', location=(-1400, 0)); level_n.operation = 'FLOOR'
    div_time = new_node(nodes, 'ShaderNodeMath', location=(-1600, 100)); div_time.operation = 'DIVIDE'
    links.new(time_val.outputs['Value'], div_time.inputs[0])
    links.new(n_in.outputs['Split Duration (s)'], div_time.inputs[1])
    links.new(div_time.outputs['Value'], level_n.inputs[0])

    # Count = 2^N
    instance_count = new_node(nodes, 'ShaderNodeMath', location=(-1200, 0)); instance_count.operation = 'POWER'
    instance_count.inputs[0].default_value = 2.0
    links.new(level_n.outputs['Value'], instance_count.inputs[1])

    # 3. Calculate animated radius
    # Radius = StartRadius + (N * RadiusGrowth)
    radius_growth = new_node(nodes, 'ShaderNodeMath', location=(-1200, 150)); radius_growth.operation = 'MULTIPLY'
    links.new(level_n.outputs['Value'], radius_growth.inputs[0])
    links.new(n_in.outputs['Radius Growth'], radius_growth.inputs[1])

    animated_radius = new_node(nodes, 'ShaderNodeMath', location=(-1000, 150)); animated_radius.operation = 'ADD'
    links.new(n_in.outputs['Start Radius'], animated_radius.inputs[0])
    links.new(radius_growth.outputs['Value'], animated_radius.inputs[1])

    # 4. Create the base circle for instancing
    circle = new_node(nodes, 'GeometryNodeCurvePrimitiveCircle', location=(-800, 100))
    links.new(animated_radius.outputs['Value'], circle.inputs['Radius'])

    resample = new_node(nodes, 'GeometryNodeResampleCurve', location=(-600, 100)); resample.mode = 'COUNT'
    links.new(circle.outputs['Curve'], resample.inputs['Curve'])
    links.new(instance_count.outputs['Value'], resample.inputs['Count'])

    # 5. Create the main spinning transform for the whole system
    spin_angle = new_node(nodes, 'ShaderNodeMath', location=(-400, -200)); spin_angle.operation = 'MULTIPLY'
    links.new(time_val.outputs['Value'], spin_angle.inputs[0])
    links.new(n_in.outputs['Spin Speed'], spin_angle.inputs[1])

    spin_vector = new_node(nodes, 'ShaderNodeCombineXYZ', location=(-200, -200))
    links.new(spin_angle.outputs['Value'], spin_vector.inputs['Z'])

    # 6. Instance Geometry on Points
    inst_on_pts = new_node(nodes, 'GeometryNodeInstanceOnPoints', location=(-200, 100))
    links.new(resample.outputs['Curve'], inst_on_pts.inputs['Points'])
    links.new(n_in.outputs['Instance Geometry'], inst_on_pts.inputs['Instance'])

    scale_vec = new_node(nodes, 'ShaderNodeCombineXYZ', location=(-400, 0))
    links.new(n_in.outputs['Instance Scale'], scale_vec.inputs['X'])
    links.new(n_in.outputs['Instance Scale'], scale_vec.inputs['Y'])
    links.new(n_in.outputs['Instance Scale'], scale_vec.inputs['Z'])
    links.new(scale_vec.outputs['Vector'], inst_on_pts.inputs['Scale'])

    # 7. Apply main spin and realize instances
    transform = new_node(nodes, 'GeometryNodeTransform', location=(200, 100))
    links.new(inst_on_pts.outputs['Instances'], transform.inputs['Geometry'])
    links.new(spin_vector.outputs['Vector'], transform.inputs['Rotation'])

    realize = new_node(nodes, 'GeometryNodeRealizeInstances', location=(400, 100))
    links.new(transform.outputs['Geometry'], realize.inputs['Geometry'])
    links.new(realize.outputs['Geometry'], n_out.inputs['Geometry'])


def setup_and_run():
    """Primary function to set up the scene and run the node tree creation."""
    ng = new_gn_group("Exponential Mesh Subdivider")
    build_subdivider_tree(ng)
    mod = attach_group_modifier(OBJ, ng, "Mesh Subdivider")

    # Create a default instance object if the input is not connected
    group_input_node = next((n for n in ng.nodes if n.type == 'GROUP_INPUT'), None)
    if group_input_node and not group_input_node.outputs['Instance Geometry'].is_linked:
        bpy.ops.mesh.primitive_ico_sphere_add(radius=0.5, subdivisions=2, enter_editmode=False, align='WORLD', location=(0, 0, 0))
        instance_obj = bpy.context.active_object
        instance_obj.name = "InstanceMesh"
        instance_obj.hide_set(True)
        instance_obj.hide_render = True
        
        obj_info_node = ng.nodes.new(type='GeometryNodeObjectInfo')
        obj_info_node.location = (-1800, 200)
        obj_info_node.transform_space = 'RELATIVE'
        obj_info_node.inputs['Object'].default_value = instance_obj
        
        ng.links.new(obj_info_node.outputs['Geometry'], group_input_node.outputs['Instance Geometry'])

    print(f"Created and assigned '{ng.name}' to modifier '{mod.name}' on object '{OBJ.name}'.")
    print("A default 'InstanceMesh' (Ico Sphere) has been created and linked to the modifier.")

# --- Execute the script ---
setup_and_run()
