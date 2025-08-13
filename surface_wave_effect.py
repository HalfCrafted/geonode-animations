# Blender 4.4 - "Surface Wave Effect" Geometry Nodes Script
# Creates a wave that propagates across the surface of a sphere, displacing instances along the normals.

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

def build_surface_wave_tree(ng):
    """Constructs the node tree for the surface wave effect."""
    nodes, links, iface = ng.nodes, ng.links, ng.interface

    # ---- Interface Definition ----
    socket(iface, name="Instance Geometry", in_out='INPUT', socket_type='NodeSocketGeometry', desc="The mesh to instance on the sphere")
    socket(iface, name="Sphere Radius", in_out='INPUT', socket_type='NodeSocketFloat', desc="Radius of the planet sphere", default=3.0, min_val=0.1, max_val=50.0)
    socket(iface, name="Resolution", in_out='INPUT', socket_type='NodeSocketInt', desc="Resolution of the base sphere", default=32, min_val=3, max_val=256)
    socket(iface, name="Wave Origin", in_out='INPUT', socket_type='NodeSocketVector', desc="World-space coordinate where the wave originates", default=(0, 0, 3.0))
    socket(iface, name="Wave Speed", in_out='INPUT', socket_type='NodeSocketFloat', desc="How fast the wave travels across the surface", default=2.0, min_val=0.0, max_val=50.0)
    socket(iface, name="Wave Width", in_out='INPUT', socket_type='NodeSocketFloat', desc="The width of the wave crest", default=2.5, min_val=0.1, max_val=50.0)
    socket(iface, name="Wave Height", in_out='INPUT', socket_type='NodeSocketFloat', desc="How high instances are lifted by the wave", default=0.5, min_val=0.0, max_val=10.0)
    socket(iface, name="Instance Scale", in_out='INPUT', socket_type='NodeSocketFloat', desc="Uniform scale of each instance", default=0.3, min_val=0.0, max_val=10.0)
    socket(iface, name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry', desc="The final output geometry")

    # ---- Node Graph Construction ----
    n_in = new_node(nodes, 'NodeGroupInput', location=(-1400, 0))
    n_out = new_node(nodes, 'NodeGroupOutput', location=(800, 0))

    # 1. Time Driver
    time_val = new_node(nodes, 'ShaderNodeValue', location=(-1400, -400))
    time_val.label = "Time (Seconds)"
    safe_time_driver(time_val)

    # 2. Base Sphere
    sphere = new_node(nodes, 'GeometryNodeMeshUVSphere', location=(-1200, 200))
    links.new(n_in.outputs['Resolution'], sphere.inputs['Segments'])
    links.new(n_in.outputs['Resolution'], sphere.inputs['Rings'])
    links.new(n_in.outputs['Sphere Radius'], sphere.inputs['Radius'])

    # 3. Calculate distance from wave origin for each point
    sphere_pos = new_node(nodes, 'GeometryNodeInputPosition', location=(-1000, 400))
    dist_from_origin = new_node(nodes, 'ShaderNodeVectorMath', location=(-800, 400))
    dist_from_origin.operation = 'DISTANCE'
    links.new(sphere_pos.outputs['Position'], dist_from_origin.inputs[0])
    links.new(n_in.outputs['Wave Origin'], dist_from_origin.inputs[1])

    # 4. Calculate the wave's current position
    wave_center = new_node(nodes, 'ShaderNodeMath', location=(-800, 200))
    wave_center.operation = 'MULTIPLY'
    links.new(time_val.outputs['Value'], wave_center.inputs[0])
    links.new(n_in.outputs['Wave Speed'], wave_center.inputs[1])

    # 5. Calculate the wave profile (a smooth bump)
    # Get distance of each point relative to the wave's center
    relative_dist = new_node(nodes, 'ShaderNodeMath', location=(-600, 300))
    relative_dist.operation = 'SUBTRACT'
    links.new(dist_from_origin.outputs['Value'], relative_dist.inputs[0])
    links.new(wave_center.outputs['Value'], relative_dist.inputs[1])

    # Map the wave width to a Cosine shape for a smooth 0->1->0 bump
    map_to_cos = new_node(nodes, 'ShaderNodeMapRange', location=(-400, 300))
    map_to_cos.clamp = True
    map_to_cos.inputs['To Min'].default_value = -math.pi / 2
    map_to_cos.inputs['To Max'].default_value = math.pi / 2
    links.new(relative_dist.outputs['Value'], map_to_cos.inputs['Value'])
    # From Min is -Width/2, From Max is Width/2
    half_width_neg = new_node(nodes, 'ShaderNodeMath', location=(-600, 100))
    half_width_neg.operation = 'MULTIPLY'
    half_width_neg.inputs[1].default_value = -0.5
    links.new(n_in.outputs['Wave Width'], half_width_neg.inputs[0])
    links.new(half_width_neg.outputs['Value'], map_to_cos.inputs['From Min'])

    half_width_pos = new_node(nodes, 'ShaderNodeMath', location=(-600, -50))
    half_width_pos.operation = 'MULTIPLY'
    half_width_pos.inputs[1].default_value = 0.5
    links.new(n_in.outputs['Wave Width'], half_width_pos.inputs[0])
    links.new(half_width_pos.outputs['Value'], map_to_cos.inputs['From Max'])

    cos_wave = new_node(nodes, 'ShaderNodeMath', location=(-200, 300))
    cos_wave.operation = 'COSINE'
    links.new(map_to_cos.outputs['Result'], cos_wave.inputs[0])

    # 6. Apply Wave Height to the bump and create displacement vector
    displacement_amount = new_node(nodes, 'ShaderNodeMath', location=(0, 300))
    displacement_amount.operation = 'MULTIPLY'
    links.new(cos_wave.outputs['Value'], displacement_amount.inputs[0])
    links.new(n_in.outputs['Wave Height'], displacement_amount.inputs[1])

    sphere_normal = new_node(nodes, 'GeometryNodeInputNormal', location=(0, 150))
    displacement_vector = new_node(nodes, 'ShaderNodeVectorMath', location=(200, 200))
    displacement_vector.operation = 'SCALE'
    links.new(sphere_normal.outputs['Normal'], displacement_vector.inputs['Vector'])
    links.new(displacement_amount.outputs['Value'], displacement_vector.inputs['Scale'])

    # 7. Set Position to create the displaced points for instancing
    set_pos = new_node(nodes, 'GeometryNodeSetPosition', location=(400, 200))
    links.new(sphere.outputs['Mesh'], set_pos.inputs['Geometry'])
    links.new(displacement_vector.outputs['Vector'], set_pos.inputs['Offset'])

    # 8. Instance Geometry
    inst_on_pts = new_node(nodes, 'GeometryNodeInstanceOnPoints', location=(600, 100))
    links.new(set_pos.outputs['Geometry'], inst_on_pts.inputs['Points'])
    links.new(n_in.outputs['Instance Geometry'], inst_on_pts.inputs['Instance'])
    # Use the original sphere normal for a stable rotation
    links.new(sphere_normal.outputs['Normal'], inst_on_pts.inputs['Rotation'])

    scale_vec = new_node(nodes, 'ShaderNodeVectorMath', location=(400, 0))
    scale_vec.operation = 'SCALE'
    scale_vec.inputs['Vector'].default_value = (1, 1, 1)
    links.new(n_in.outputs['Instance Scale'], scale_vec.inputs['Scale'])
    links.new(scale_vec.outputs['Vector'], inst_on_pts.inputs['Scale'])

    # 9. Realize and Output
    links.new(inst_on_pts.outputs['Instances'], n_out.inputs['Geometry'])

def setup_and_run():
    """Primary function to set up the scene and run the node tree creation."""
    ng = new_gn_group("Surface Wave Effect")
    build_surface_wave_tree(ng)
    mod = attach_group_modifier(OBJ, ng, "Surface Wave")

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
