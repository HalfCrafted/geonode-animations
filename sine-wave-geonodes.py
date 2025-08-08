import bpy
import math

# --- Create a new Geometry Node Group ---
def create_geometry_node_group(name="Waving Circle Animation"):
    """Creates a new geometry node group and clears the default nodes."""
    node_group = bpy.data.node_groups.new(name, 'GeometryNodeTree')
    
    # Remove default input/output nodes
    for node in node_group.nodes:
        node_group.nodes.remove(node)
        
    return node_group

# --- Main function to build the node tree ---
def build_waving_circle_nodetree(node_group):
    """Builds the node tree for the animated waving circle."""

    # Get node tree links and nodes shortcuts
    links = node_group.links
    nodes = node_group.nodes

    # 1. --- DEFINE GROUP INTERFACE (INPUTS & OUTPUTS) ---
    scale_input = node_group.interface.new_socket(name='Scale', in_out='INPUT', socket_type='NodeSocketFloat')
    scale_input.default_value = 1.0
    scale_input.min_value = 0.0
    scale_input.max_value = 10.0

    bloom_input = node_group.interface.new_socket(name='Bloom', in_out='INPUT', socket_type='NodeSocketFloat')
    bloom_input.default_value = 0.0
    bloom_input.min_value = 0.0
    bloom_input.max_value = 1.0
    
    node_group.interface.new_socket(name='Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')

    # Create the Group Input and Output nodes
    group_input = nodes.new(type='NodeGroupInput')
    group_input.location = (-1600, 0)
    
    group_output = nodes.new(type='NodeGroupOutput')
    group_output.location = (1800, 0)

    # 2. --- CREATE BASE CIRCLE CURVE ---
    curve_circle = nodes.new(type='GeometryNodeCurvePrimitiveCircle')
    curve_circle.location = (-1400, 200)
    curve_circle.inputs['Resolution'].default_value = 128
    curve_circle.inputs['Radius'].default_value = 1.0

    # 3. --- CREATE THE SINE WAVE DEFORMATION ---
    time_node = nodes.new(type='ShaderNodeValue')
    time_node.location = (-1400, -200)
    time_node.label = "Time (Seconds)"
    driver = time_node.outputs[0].driver_add('default_value')
    driver.driver.expression = 'frame / 24'

    spline_parameter = nodes.new(type='GeometryNodeSplineParameter')
    spline_parameter.location = (-1400, -400)
    
    multiply_for_wave = nodes.new(type='ShaderNodeMath')
    multiply_for_wave.location = (-1200, -300)
    multiply_for_wave.operation = 'MULTIPLY'
    multiply_for_wave.inputs[1].default_value = 2 * math.pi
    links.new(spline_parameter.outputs['Factor'], multiply_for_wave.inputs[0])

    add_time_to_wave = nodes.new(type='ShaderNodeMath')
    add_time_to_wave.location = (-1000, -250)
    add_time_to_wave.operation = 'ADD'
    links.new(time_node.outputs['Value'], add_time_to_wave.inputs[0])
    links.new(multiply_for_wave.outputs['Value'], add_time_to_wave.inputs[1])

    wave_sine = nodes.new(type='ShaderNodeMath')
    wave_sine.location = (-800, -200)
    wave_sine.operation = 'SINE'
    links.new(add_time_to_wave.outputs['Value'], wave_sine.inputs[0])

    combine_xyz_wave = nodes.new(type='ShaderNodeCombineXYZ')
    combine_xyz_wave.location = (-600, -150)
    links.new(wave_sine.outputs['Value'], combine_xyz_wave.inputs['Z'])

    set_position_wave = nodes.new(type='GeometryNodeSetPosition')
    set_position_wave.location = (-400, 100)
    links.new(curve_circle.outputs['Curve'], set_position_wave.inputs['Geometry'])
    links.new(combine_xyz_wave.outputs['Vector'], set_position_wave.inputs['Offset'])

    # 4. --- CREATE BLOOMING / FLIPPING EFFECT (MANUAL ROTATION) ---
    
    # --- Get Inputs for Rotation Formula ---
    # v (vector to be rotated) is the position
    input_position = nodes.new(type='GeometryNodeInputPosition')
    input_position.location = (-200, -600)
    
    # k (axis of rotation) is the curve tangent
    curve_tangent = nodes.new(type='GeometryNodeInputTangent')
    curve_tangent.location = (-200, -500)

    # theta (angle of rotation) is the bloom parameter mapped to radians
    map_range_bloom_angle = nodes.new(type='ShaderNodeMapRange')
    map_range_bloom_angle.location = (0, -550)
    map_range_bloom_angle.inputs['To Min'].default_value = 0.0
    map_range_bloom_angle.inputs['To Max'].default_value = 2 * math.pi # Full 360-degree flip
    links.new(group_input.outputs['Bloom'], map_range_bloom_angle.inputs['Value'])

    # --- Implement Rodrigues' Rotation Formula ---
    # v_rot = v*cos(theta) + (k x v)*sin(theta) + k*(k . v)*(1-cos(theta))

    # Calculate sin and cos of the angle
    angle_cos = nodes.new(type='ShaderNodeMath')
    angle_cos.location = (200, -600)
    angle_cos.operation = 'COSINE'
    links.new(map_range_bloom_angle.outputs['Result'], angle_cos.inputs[0])

    angle_sin = nodes.new(type='ShaderNodeMath')
    angle_sin.location = (200, -500)
    angle_sin.operation = 'SINE'
    links.new(map_range_bloom_angle.outputs['Result'], angle_sin.inputs[0])

    # Term 1: v * cos(theta)
    term1 = nodes.new(type='ShaderNodeVectorMath')
    term1.location = (400, -600)
    term1.operation = 'SCALE'
    links.new(input_position.outputs['Position'], term1.inputs[0])
    links.new(angle_cos.outputs['Value'], term1.inputs[1])

    # Term 2: (k x v) * sin(theta)
    cross_product = nodes.new(type='ShaderNodeVectorMath')
    cross_product.location = (400, -450)
    cross_product.operation = 'CROSS_PRODUCT'
    links.new(curve_tangent.outputs['Tangent'], cross_product.inputs[0])
    links.new(input_position.outputs['Position'], cross_product.inputs[1])

    term2 = nodes.new(type='ShaderNodeVectorMath')
    term2.location = (600, -500)
    term2.operation = 'SCALE'
    links.new(cross_product.outputs['Vector'], term2.inputs[0])
    links.new(angle_sin.outputs['Value'], term2.inputs[1])

    # Term 3: k * (k . v) * (1 - cos(theta))
    dot_product = nodes.new(type='ShaderNodeVectorMath')
    dot_product.location = (400, -300)
    dot_product.operation = 'DOT_PRODUCT'
    links.new(curve_tangent.outputs['Tangent'], dot_product.inputs[0])
    links.new(input_position.outputs['Position'], dot_product.inputs[1])

    one_minus_cos = nodes.new(type='ShaderNodeMath')
    one_minus_cos.location = (400, -200)
    one_minus_cos.operation = 'SUBTRACT'
    one_minus_cos.inputs[0].default_value = 1.0
    links.new(angle_cos.outputs['Value'], one_minus_cos.inputs[1])

    term3_factor = nodes.new(type='ShaderNodeMath')
    term3_factor.location = (600, -300)
    term3_factor.operation = 'MULTIPLY'
    links.new(dot_product.outputs['Value'], term3_factor.inputs[0])
    links.new(one_minus_cos.outputs['Value'], term3_factor.inputs[1])

    term3 = nodes.new(type='ShaderNodeVectorMath')
    term3.location = (800, -350)
    term3.operation = 'SCALE'
    links.new(curve_tangent.outputs['Tangent'], term3.inputs[0])
    links.new(term3_factor.outputs['Value'], term3.inputs[1])

    # Add the terms together
    add_term1_term2 = nodes.new(type='ShaderNodeVectorMath')
    add_term1_term2.location = (1000, -500)
    add_term1_term2.operation = 'ADD'
    links.new(term1.outputs['Vector'], add_term1_term2.inputs[0])
    links.new(term2.outputs['Vector'], add_term1_term2.inputs[1])

    final_rotated_vector = nodes.new(type='ShaderNodeVectorMath')
    final_rotated_vector.location = (1200, -450)
    final_rotated_vector.operation = 'ADD'
    links.new(add_term1_term2.outputs['Vector'], final_rotated_vector.inputs[0])
    links.new(term3.outputs['Vector'], final_rotated_vector.inputs[1])

    # --- Set the final position ---
    set_position_bloom = nodes.new(type='GeometryNodeSetPosition')
    set_position_bloom.location = (1400, 100)
    links.new(set_position_wave.outputs['Geometry'], set_position_bloom.inputs['Geometry'])
    links.new(final_rotated_vector.outputs['Vector'], set_position_bloom.inputs['Position'])

    # 5. --- CONVERT THE CURVE TO A TUBING MESH ---
    profile_circle = nodes.new(type='GeometryNodeCurvePrimitiveCircle')
    profile_circle.location = (1400, -200)
    profile_circle.inputs['Radius'].default_value = 0.05
    
    curve_to_mesh = nodes.new(type='GeometryNodeCurveToMesh')
    curve_to_mesh.location = (1600, 100)
    links.new(set_position_bloom.outputs['Geometry'], curve_to_mesh.inputs['Curve'])
    links.new(profile_circle.outputs['Curve'], curve_to_mesh.inputs['Profile Curve'])

    # 6. --- ANIMATE THE OVERALL SCALE ---
    scale_sine = nodes.new(type='ShaderNodeMath')
    scale_sine.location = (1000, -300)
    scale_sine.operation = 'SINE'
    links.new(time_node.outputs['Value'], scale_sine.inputs[0])

    map_range_scale = nodes.new(type='ShaderNodeMapRange')
    map_range_scale.location = (1200, -250)
    map_range_scale.inputs['From Min'].default_value = -1.0
    map_range_scale.inputs['From Max'].default_value = 1.0
    map_range_scale.inputs['To Min'].default_value = 0.5
    map_range_scale.inputs['To Max'].default_value = 1.5
    links.new(scale_sine.outputs['Value'], map_range_scale.inputs['Value'])
    
    multiply_by_scale_param = nodes.new(type='ShaderNodeMath')
    multiply_by_scale_param.location = (1400, -150)
    multiply_by_scale_param.operation = 'MULTIPLY'
    links.new(map_range_scale.outputs['Result'], multiply_by_scale_param.inputs[0])
    links.new(group_input.outputs['Scale'], multiply_by_scale_param.inputs[1])

    combine_xyz_scale = nodes.new(type='ShaderNodeCombineXYZ')
    combine_xyz_scale.location = (1550, -100)
    links.new(multiply_by_scale_param.outputs['Value'], combine_xyz_scale.inputs['X'])
    links.new(multiply_by_scale_param.outputs['Value'], combine_xyz_scale.inputs['Y'])
    links.new(multiply_by_scale_param.outputs['Value'], combine_xyz_scale.inputs['Z'])

    transform_geometry = nodes.new(type='GeometryNodeTransform')
    transform_geometry.location = (1600, 50)
    links.new(curve_to_mesh.outputs['Mesh'], transform_geometry.inputs['Geometry'])
    links.new(combine_xyz_scale.outputs['Vector'], transform_geometry.inputs['Scale'])

    # 7. --- CONNECT TO FINAL OUTPUT ---
    links.new(transform_geometry.outputs['Geometry'], group_output.inputs['Geometry'])


# --- Setup and run the script ---
def setup_and_run():
    """Sets up an object with the new geometry node group."""
    # Ensure there is an active object
    if bpy.context.active_object is None:
        bpy.ops.mesh.primitive_plane_add()

    obj = bpy.context.active_object

    # Check for existing geometry node modifiers
    modifier = None
    for mod in obj.modifiers:
        if mod.type == 'NODES':
            modifier = mod
            break
            
    # If no geometry node modifier exists, create one
    if modifier is None:
        modifier = obj.modifiers.new(name="Waving Circle", type='NODES')

    # Create and build the node group
    node_group = create_geometry_node_group()
    build_waving_circle_nodetree(node_group)

    # Assign the new node group to the modifier
    modifier.node_group = node_group
    
    print(f"Successfully created and assigned '{node_group.name}' node group to '{obj.name}'.")

# Execute the main function
setup_and_run()