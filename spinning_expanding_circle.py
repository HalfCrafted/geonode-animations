# Blender 4.4 - "Spinning Expanding Circle" Geometry Nodes Script
# Creates a circle of instances that expands over time, with each instance spinning on its own Z-axis.
# The instance geometry is provided via a modifier input, making it easily substitutable.

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


def build_spinning_circle_tree(ng):
    """Constructs the node tree for the spinning, expanding circle effect."""
    nodes, links, iface = ng.nodes, ng.links, ng.interface

    # ---- Interface Definition ----
    # Input for the mesh to be instanced
    socket(iface, name="Instance Geometry", in_out='INPUT', socket_type='NodeSocketGeometry', desc="The mesh to instance on each point of the circle")

    # Animation and Layout Parameters
    p_count = socket(iface, name="Count", in_out='INPUT', socket_type='NodeSocketInt', desc="Number of instances in the circle", default=12, min_val=1, max_val=256)
    p_start_rad = socket(iface, name="Start Radius", in_out='INPUT', socket_type='NodeSocketFloat', desc="Radius of the circle at the start of the animation", default=1.0, min_val=0.0, max_val=50.0)
    p_end_rad = socket(iface, name="End Radius", in_out='INPUT', socket_type='NodeSocketFloat', desc="Radius of the circle at the end of the animation", default=5.0, min_val=0.0, max_val=50.0)
    p_duration = socket(iface, name="Duration (s)", in_out='INPUT', socket_type='NodeSocketFloat', desc="How long the expansion animation takes in seconds", default=5.0, min_val=0.1, max_val=300.0)
    p_spin_speed = socket(iface, name="Spin Speed", in_out='INPUT', socket_type='NodeSocketFloat', desc="How fast each instance spins on its Z-axis (radians/sec)", default=2.0, min_val=-50.0, max_val=50.0)
    p_scale = socket(iface, name="Instance Scale", in_out='INPUT', socket_type='NodeSocketFloat', desc="Uniform scale of each instance", default=0.4, min_val=0.0, max_val=10.0)

    # Output Geometry
    socket(iface, name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry', desc="The final output geometry")

    # ---- Node Graph Construction ----
    n_in = new_node(nodes, 'NodeGroupInput', location=(-1200, 0))
    n_out = new_node(nodes, 'NodeGroupOutput', location=(600, 0))

    # 1. Time Driver
    time_val = new_node(nodes, 'ShaderNodeValue', location=(-1200, -300))
    time_val.label = "Time (Seconds)"
    safe_time_driver(time_val) # Use the safe driver helper

    # 2. Calculate Animated Radius (Map Range)
    map_radius = new_node(nodes, 'ShaderNodeMapRange', location=(-1000, 100))
    map_radius.clamp = True
    links.new(time_val.outputs['Value'], map_radius.inputs['Value'])
    links.new(n_in.outputs['Duration (s)'], map_radius.inputs['From Max'])
    links.new(n_in.outputs['Start Radius'], map_radius.inputs['To Min'])
    links.new(n_in.outputs['End Radius'], map_radius.inputs['To Max'])

    # 3. Create the Base Circle
    circle = new_node(nodes, 'GeometryNodeCurvePrimitiveCircle', location=(-800, 100))
    circle.inputs['Resolution'].default_value = 128
    links.new(map_radius.outputs['Result'], circle.inputs['Radius'])

    # 4. Resample Circle to get points for instancing
    resample = new_node(nodes, 'GeometryNodeResampleCurve', location=(-600, 100))
    resample.mode = 'COUNT'
    links.new(circle.outputs['Curve'], resample.inputs['Curve'])
    links.new(n_in.outputs['Count'], resample.inputs['Count'])

    # 5. Calculate Instance Rotation
    spin_angle_mult = new_node(nodes, 'ShaderNodeMath', location=(-600, -200))
    spin_angle_mult.operation = 'MULTIPLY'
    links.new(time_val.outputs['Value'], spin_angle_mult.inputs[0])
    links.new(n_in.outputs['Spin Speed'], spin_angle_mult.inputs[1])

    spin_vector = new_node(nodes, 'ShaderNodeCombineXYZ', location=(-400, -200))
    links.new(spin_angle_mult.outputs['Value'], spin_vector.inputs['Z']) # Rotate around Z

    # 6. Instance Geometry on Points
    inst_on_pts = new_node(nodes, 'GeometryNodeInstanceOnPoints', location=(-200, 100))
    links.new(resample.outputs['Curve'], inst_on_pts.inputs['Points'])
    links.new(n_in.outputs['Instance Geometry'], inst_on_pts.inputs['Instance'])
    links.new(spin_vector.outputs['Vector'], inst_on_pts.inputs['Rotation'])

    # Create a vector for uniform scaling
    scale_vec = new_node(nodes, 'ShaderNodeCombineXYZ', location=(-400, -50))
    links.new(n_in.outputs['Instance Scale'], scale_vec.inputs['X'])
    links.new(n_in.outputs['Instance Scale'], scale_vec.inputs['Y'])
    links.new(n_in.outputs['Instance Scale'], scale_vec.inputs['Z'])
    links.new(scale_vec.outputs['Vector'], inst_on_pts.inputs['Scale'])

    # 7. Realize Instances and Output
    realize = new_node(nodes, 'GeometryNodeRealizeInstances', location=(200, 100))
    links.new(inst_on_pts.outputs['Instances'], realize.inputs['Geometry'])
    links.new(realize.outputs['Geometry'], n_out.inputs['Geometry'])


def setup_and_run():
    """Primary function to set up the scene and run the node tree creation."""
    ng = new_gn_group("Spinning Expanding Circle")
    build_spinning_circle_tree(ng)
    mod = attach_group_modifier(OBJ, ng, "Spinning Circle")

    # As a helpful starting point, if the instance input is not connected, create a default cube and link it.
    group_input_node = next((n for n in ng.nodes if n.type == 'GROUP_INPUT'), None)
    if group_input_node and not group_input_node.outputs['Instance Geometry'].is_linked:
        # Create a new object with a cube mesh
        bpy.ops.mesh.primitive_cube_add(size=1, enter_editmode=False, align='WORLD', location=(0, 0, 0))
        cube_obj = bpy.context.active_object
        cube_obj.name = "InstanceCube"
        # Hide the original cube from the viewport and render
        cube_obj.hide_set(True)
        cube_obj.hide_render = True
        
        # Use an Object Info node to bring it into the GN tree
        obj_info_node = ng.nodes.new(type='GeometryNodeObjectInfo')
        obj_info_node.location = (-1500, 200)
        obj_info_node.transform_space = 'RELATIVE'
        obj_info_node.inputs['Object'].default_value = cube_obj
        
        # Link the object's geometry to the main input
        ng.links.new(obj_info_node.outputs['Geometry'], group_input_node.outputs['Instance Geometry'])

    print(f"Created and assigned '{ng.name}' to modifier '{mod.name}' on object '{OBJ.name}'.")
    print("A default 'InstanceCube' has been created and linked to the modifier.")


# --- Execute the script ---
setup_and_run()
