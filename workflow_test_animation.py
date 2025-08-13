# Blender 4.4 - "Workflow Test Animation" Geometry Nodes Script
# This script is a clean-room implementation to verify the end-to-end workflow.
# It creates a circle of instances that expands over time, with each instance spinning.

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

def build_workflow_test_tree(ng):
    """Constructs the node tree for the test animation."""
    nodes, links, iface = ng.nodes, ng.links, ng.interface

    # ---- 1. Interface Definition ----
    socket(iface, name="Instance Geometry", in_out='INPUT', socket_type='NodeSocketGeometry', desc="The mesh to instance")
    socket(iface, name="Count", in_out='INPUT', socket_type='NodeSocketInt', desc="Number of instances", default=10, min_val=1, max_val=500)
    socket(iface, name="Start Radius", in_out='INPUT', socket_type='NodeSocketFloat', desc="Start radius of the circle", default=0.5, min_val=0.0, max_val=20.0)
    socket(iface, name="End Radius", in_out='INPUT', socket_type='NodeSocketFloat', desc="End radius of the circle", default=3.0, min_val=0.0, max_val=20.0)
    socket(iface, name="Duration (s)", in_out='INPUT', socket_type='NodeSocketFloat', desc="Animation duration in seconds", default=4.0, min_val=0.1, max_val=100.0)
    socket(iface, name="Spin Speed", in_out='INPUT', socket_type='NodeSocketFloat', desc="Instance spin speed (rad/s)", default=1.0, min_val=-20.0, max_val=20.0)
    socket(iface, name="Instance Scale", in_out='INPUT', socket_type='NodeSocketFloat', desc="Scale of instances", default=0.3, min_val=0.0, max_val=10.0)
    socket(iface, name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry', desc="Final output geometry")

    # ---- 2. Node Graph Construction ----
    n_in = new_node(nodes, 'NodeGroupInput', location=(-1200, 0))
    n_out = new_node(nodes, 'NodeGroupOutput', location=(400, 0))

    # Time driver
    time_val = new_node(nodes, 'ShaderNodeValue', location=(-1200, -300)); time_val.label = "Time (s)"
    safe_time_driver(time_val)

    # Animated radius
    map_radius = new_node(nodes, 'ShaderNodeMapRange', location=(-1000, 100)); map_radius.clamp = True
    links.new(time_val.outputs['Value'], map_radius.inputs['Value'])
    links.new(n_in.outputs['Duration (s)'], map_radius.inputs['From Max'])
    links.new(n_in.outputs['Start Radius'], map_radius.inputs['To Min'])
    links.new(n_in.outputs['End Radius'], map_radius.inputs['To Max'])

    # Base circle for points
    circle = new_node(nodes, 'GeometryNodeCurvePrimitiveCircle', location=(-800, 100))
    links.new(map_radius.outputs['Result'], circle.inputs['Radius'])

    resample = new_node(nodes, 'GeometryNodeResampleCurve', location=(-600, 100)); resample.mode = 'COUNT'
    links.new(circle.outputs['Curve'], resample.inputs['Curve'])
    links.new(n_in.outputs['Count'], resample.inputs['Count'])

    # Instance rotation
    spin_angle = new_node(nodes, 'ShaderNodeMath', location=(-600, -200)); spin_angle.operation = 'MULTIPLY'
    links.new(time_val.outputs['Value'], spin_angle.inputs[0])
    links.new(n_in.outputs['Spin Speed'], spin_angle.inputs[1])
    spin_vector = new_node(nodes, 'ShaderNodeCombineXYZ', location=(-400, -200))
    links.new(spin_angle.outputs['Value'], spin_vector.inputs['Z'])

    # Instance scale
    scale_vec = new_node(nodes, 'ShaderNodeVectorMath', location=(-400, -50)); scale_vec.operation = 'SCALE'
    scale_vec.inputs['Vector'].default_value = (1, 1, 1)
    links.new(n_in.outputs['Instance Scale'], scale_vec.inputs['Scale'])

    # Instance on points
    inst_on_pts = new_node(nodes, 'GeometryNodeInstanceOnPoints', location=(-200, 100))
    links.new(resample.outputs['Curve'], inst_on_pts.inputs['Points'])
    links.new(n_in.outputs['Instance Geometry'], inst_on_pts.inputs['Instance'])
    links.new(spin_vector.outputs['Vector'], inst_on_pts.inputs['Rotation'])
    links.new(scale_vec.outputs['Vector'], inst_on_pts.inputs['Scale'])

    # Final output
    realize = new_node(nodes, 'GeometryNodeRealizeInstances', location=(0, 100))
    links.new(inst_on_pts.outputs['Instances'], realize.inputs['Geometry'])
    links.new(realize.outputs['Geometry'], n_out.inputs['Geometry'])

def setup_and_run():
    """Primary function to set up the scene and run the node tree creation."""
    print("--- Starting Workflow Test Script ---")
    
    # Ensure we start with a clean slate
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)

    # Create the main object
    obj = ensure_active_object()
    obj.name = "TestObject"

    # Create and build the node group
    ng = new_gn_group("WorkflowTestTree")
    build_workflow_test_tree(ng)
    
    # Attach the modifier
    mod = attach_group_modifier(obj, ng, "WorkflowTestModifier")

    # Create and link a default instance object (a simple cube)
    group_input_node = next((n for n in ng.nodes if n.type == 'GROUP_INPUT'), None)
    if group_input_node and not group_input_node.outputs['Instance Geometry'].is_linked:
        bpy.ops.mesh.primitive_cube_add(size=1, enter_editmode=False, align='WORLD', location=(0, 0, 0))
        instance_obj = bpy.context.active_object
        instance_obj.name = "InstanceCube"
        instance_obj.hide_set(True)
        instance_obj.hide_render = True
        
        obj_info_node = ng.nodes.new(type='GeometryNodeObjectInfo')
        obj_info_node.location = (-1400, 200)
        obj_info_node.transform_space = 'RELATIVE'
        obj_info_node.inputs['Object'].default_value = instance_obj
        
        ng.links.new(obj_info_node.outputs['Geometry'], group_input_node.outputs['Instance Geometry'])

    print(f"Successfully created and assigned '{ng.name}' to modifier '{mod.name}' on object '{obj.name}'.")
    print("--- Workflow Test Script Finished ---")

# --- Execute the script ---
if __name__ == "__main__":
    setup_and_run()
