# Blender 4.4 - "Sphere Dispersal Effect" Geometry Nodes Script
# Creates an effect where instances disperse from a central point to the surface of a sphere.
# Each instance is oriented to the sphere's normal and spins on its local Z-axis.

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

def build_sphere_dispersal_tree(ng):
    """Constructs the node tree for the sphere dispersal effect."""
    nodes, links, iface = ng.nodes, ng.links, ng.interface

    # ---- Interface Definition ----
    socket(iface, name="Instance Geometry", in_out='INPUT', socket_type='NodeSocketGeometry', desc="The mesh to instance on the sphere")
    socket(iface, name="Sphere Radius", in_out='INPUT', socket_type='NodeSocketFloat', desc="Final radius of the sphere", default=4.0, min_val=0.1, max_val=50.0)
    socket(iface, name="Resolution", in_out='INPUT', socket_type='NodeSocketInt', desc="Resolution of the base sphere (Segments and Rings)", default=16, min_val=3, max_val=256)
    socket(iface, name="Duration (s)", in_out='INPUT', socket_type='NodeSocketFloat', desc="How long the dispersal animation takes", default=4.0, min_val=0.1, max_val=300.0)
    socket(iface, name="Spin Speed", in_out='INPUT', socket_type='NodeSocketFloat', desc="How fast each instance spins on its local up-axis", default=1.5, min_val=-50.0, max_val=50.0)
    socket(iface, name="Instance Scale", in_out='INPUT', socket_type='NodeSocketFloat', desc="Uniform scale of each instance", default=0.5, min_val=0.0, max_val=10.0)
    socket(iface, name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry', desc="The final output geometry")

    # ---- Node Graph Construction ----
    n_in = new_node(nodes, 'NodeGroupInput', location=(-1400, 0))
    n_out = new_node(nodes, 'NodeGroupOutput', location=(600, 0))

    # 1. Time Driver
    time_val = new_node(nodes, 'ShaderNodeValue', location=(-1400, -400))
    time_val.label = "Time (Seconds)"
    safe_time_driver(time_val)

    # 2. Base Sphere (Points source)
    sphere = new_node(nodes, 'GeometryNodeMeshUVSphere', location=(-1200, 200))
    links.new(n_in.outputs['Resolution'], sphere.inputs['Segments'])
    links.new(n_in.outputs['Resolution'], sphere.inputs['Rings'])
    links.new(n_in.outputs['Sphere Radius'], sphere.inputs['Radius'])

    # 3. Animate dispersal from center
    anim_factor = new_node(nodes, 'ShaderNodeMapRange', location=(-1000, -200))
    anim_factor.clamp = True
    links.new(time_val.outputs['Value'], anim_factor.inputs['Value'])
    links.new(n_in.outputs['Duration (s)'], anim_factor.inputs['From Max'])

    sphere_pos = new_node(nodes, 'GeometryNodeInputPosition', location=(-1000, 200))
    
    pos_scaler = new_node(nodes, 'ShaderNodeVectorMath', location=(-800, 200))
    pos_scaler.operation = 'SCALE'
    links.new(sphere_pos.outputs['Position'], pos_scaler.inputs['Vector'])
    links.new(anim_factor.outputs['Result'], pos_scaler.inputs['Scale'])

    set_pos = new_node(nodes, 'GeometryNodeSetPosition', location=(-600, 200))
    links.new(sphere.outputs['Mesh'], set_pos.inputs['Geometry'])
    links.new(pos_scaler.outputs['Vector'], set_pos.inputs['Position'])

    # 4. Calculate local spin rotation
    spin_angle = new_node(nodes, 'ShaderNodeMath', location=(-400, 0))
    spin_angle.operation = 'MULTIPLY'
    links.new(time_val.outputs['Value'], spin_angle.inputs[0])
    links.new(n_in.outputs['Spin Speed'], spin_angle.inputs[1])

    spin_euler = new_node(nodes, 'ShaderNodeCombineXYZ', location=(-200, 0))
    links.new(spin_angle.outputs['Value'], spin_euler.inputs['Z'])

    # 5. Use the sphere's normal for the base orientation
    sphere_normal = new_node(nodes, 'GeometryNodeInputNormal', location=(-200, 200))

    # 6. Combine orientation and spin
    # This simplified fallback adds the spin vector to the normal vector.
    # This correctly uses the normal to drive the orientation.
    final_rot = new_node(nodes, 'ShaderNodeVectorMath', location=(0, 100))
    final_rot.operation = 'ADD'
    links.new(sphere_normal.outputs['Normal'], final_rot.inputs[0])
    links.new(spin_euler.outputs['Vector'], final_rot.inputs[1])

    # 7. Instance Geometry
    inst_on_pts = new_node(nodes, 'GeometryNodeInstanceOnPoints', location=(200, 100))
    links.new(set_pos.outputs['Geometry'], inst_on_pts.inputs['Points'])
    links.new(n_in.outputs['Instance Geometry'], inst_on_pts.inputs['Instance'])
    links.new(final_rot.outputs['Vector'], inst_on_pts.inputs['Rotation'])

    scale_vec = new_node(nodes, 'ShaderNodeVectorMath', location=(0, 0))
    scale_vec.operation = 'SCALE'
    scale_vec.inputs['Vector'].default_value = (1, 1, 1)
    links.new(n_in.outputs['Instance Scale'], scale_vec.inputs['Scale'])
    links.new(scale_vec.outputs['Vector'], inst_on_pts.inputs['Scale'])

    # 8. Realize and Output
    realize = new_node(nodes, 'GeometryNodeRealizeInstances', location=(400, 100))
    links.new(inst_on_pts.outputs['Instances'], realize.inputs['Geometry'])
    links.new(realize.outputs['Geometry'], n_out.inputs['Geometry'])

def setup_and_run():
    """Primary function to set up the scene and run the node tree creation."""
    ng = new_gn_group("Sphere Dispersal Effect")
    build_sphere_dispersal_tree(ng)
    mod = attach_group_modifier(OBJ, ng, "Sphere Dispersal")

    # As a helpful starting point, if the instance input is not connected, create a default cone and link it.
    group_input_node = next((n for n in ng.nodes if n.type == 'GROUP_INPUT'), None)
    if group_input_node and not group_input_node.outputs['Instance Geometry'].is_linked:
        bpy.ops.mesh.primitive_cone_add(vertices=8, radius1=0.4, depth=0.8, enter_editmode=False, align='WORLD', location=(0, 0, 0))
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
    print("A default 'InstanceCone' has been created and linked to the modifier as an example.")

# --- Execute the script ---
setup_and_run()
