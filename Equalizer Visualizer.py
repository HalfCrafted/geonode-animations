import bpy
import math

# --- Create a new Geometry Node Group ---
def create_geometry_node_group(name="Animated Equalizer Visualizer"):
    """Creates a new geometry node group and clears the default nodes."""
    node_group = bpy.data.node_groups.new(name, 'GeometryNodeTree')
    
    # Remove default input/output nodes
    for node in node_group.nodes:
        node_group.nodes.remove(node)
        
    return node_group

# --- Main function to build the node tree ---
def build_animated_equalizer_nodetree(node_group):
    """Builds the node tree for the animated equalizer visualizer."""

    # Get node tree links and nodes shortcuts
    links = node_group.links
    nodes = node_group.nodes

    # 1. --- DEFINE GROUP INTERFACE (INPUTS & OUTPUTS) ---
    count_x_input = node_group.interface.new_socket(name='Count X', in_out='INPUT', socket_type='NodeSocketInt')
    count_x_input.default_value = 32
    count_x_input.min_value = 2
    count_x_input.max_value = 100

    count_y_input = node_group.interface.new_socket(name='Count Y', in_out='INPUT', socket_type='NodeSocketInt')
    count_y_input.default_value = 16
    count_y_input.min_value = 2
    count_y_input.max_value = 50

    size_x_input = node_group.interface.new_socket(name='Size X', in_out='INPUT', socket_type='NodeSocketFloat')
    size_x_input.default_value = 30.0
    size_x_input.min_value = 1.0
    size_x_input.max_value = 100.0

    size_y_input = node_group.interface.new_socket(name='Size Y', in_out='INPUT', socket_type='NodeSocketFloat')
    size_y_input.default_value = 10.0
    size_y_input.min_value = 1.0
    size_y_input.max_value = 50.0

    bar_width_input = node_group.interface.new_socket(name='Bar Width', in_out='INPUT', socket_type='NodeSocketFloat')
    bar_width_input.default_value = 0.8
    bar_width_input.min_value = 0.1
    bar_width_input.max_value = 2.0

    base_height_input = node_group.interface.new_socket(name='Base Height', in_out='INPUT', socket_type='NodeSocketFloat')
    base_height_input.default_value = 0.1
    base_height_input.min_value = 0.01
    base_height_input.max_value = 1.0

    amplitude_input = node_group.interface.new_socket(name='Amplitude', in_out='INPUT', socket_type='NodeSocketFloat')
    amplitude_input.default_value = 5.0
    amplitude_input.min_value = 0.0
    amplitude_input.max_value = 20.0

    freq1_input = node_group.interface.new_socket(name='Frequency 1', in_out='INPUT', socket_type='NodeSocketFloat')
    freq1_input.default_value = 0.2
    freq1_input.min_value = 0.01
    freq1_input.max_value = 1.0

    speed1_input = node_group.interface.new_socket(name='Speed 1', in_out='INPUT', socket_type='NodeSocketFloat')
    speed1_input.default_value = 2.0
    speed1_input.min_value = 0.0
    speed1_input.max_value = 10.0

    freq2_input = node_group.interface.new_socket(name='Frequency 2', in_out='INPUT', socket_type='NodeSocketFloat')
    freq2_input.default_value = 0.5
    freq2_input.min_value = 0.01
    freq2_input.max_value = 1.0

    speed2_input = node_group.interface.new_socket(name='Speed 2', in_out='INPUT', socket_type='NodeSocketFloat')
    speed2_input.default_value = 3.0
    speed2_input.min_value = 0.0
    speed2_input.max_value = 10.0
    
    node_group.interface.new_socket(name='Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')

    # Create the Group Input and Output nodes
    group_input = nodes.new(type='NodeGroupInput')
    group_input.location = (-2000, 0)
    
    group_output = nodes.new(type='NodeGroupOutput')
    group_output.location = (3000, 0)

    # 2. --- CREATE TIME NODE FOR ANIMATION ---
    time_node = nodes.new(type='ShaderNodeValue')
    time_node.location = (-2000, -400)
    time_node.label = "Time (Seconds)"
    driver = time_node.outputs[0].driver_add('default_value')
    driver.driver.expression = 'frame / 24'

    # 3. --- CREATE THE GRID OF POINTS ---
    grid = nodes.new(type='GeometryNodeMeshGrid')
    grid.location = (-1800, 200)
    links.new(group_input.outputs['Size X'], grid.inputs['Size X'])
    links.new(group_input.outputs['Size Y'], grid.inputs['Size Y'])
    links.new(group_input.outputs['Count X'], grid.inputs['Vertices X'])
    links.new(group_input.outputs['Count Y'], grid.inputs['Vertices Y'])

    # 4. --- CREATE THE BAR (CUBE) INSTANCE ---
    cube_size_combine = nodes.new(type='ShaderNodeCombineXYZ')
    cube_size_combine.location = (-1800, -200)
    links.new(group_input.outputs['Bar Width'], cube_size_combine.inputs['X'])
    links.new(group_input.outputs['Bar Width'], cube_size_combine.inputs['Y'])
    cube_size_combine.inputs['Z'].default_value = 1.0

    cube = nodes.new(type='GeometryNodeMeshCube')
    cube.location = (-1600, -200)
    links.new(cube_size_combine.outputs['Vector'], cube.inputs['Size'])

    # 5. --- COMPUTE HEIGHT FIELD ON POINTS FOR SCALE ---
    position1 = nodes.new(type='GeometryNodeInputPosition')
    position1.location = (-1600, 600)

    sep_xyz1 = nodes.new(type='ShaderNodeSeparateXYZ')
    sep_xyz1.location = (-1400, 600)
    links.new(position1.outputs['Position'], sep_xyz1.inputs['Vector'])

    # Wave 1
    mult_x_freq1 = nodes.new(type='ShaderNodeMath')
    mult_x_freq1.operation = 'MULTIPLY'
    mult_x_freq1.location = (-1200, 700)
    links.new(sep_xyz1.outputs['X'], mult_x_freq1.inputs[0])
    links.new(group_input.outputs['Frequency 1'], mult_x_freq1.inputs[1])

    mult_time_speed1 = nodes.new(type='ShaderNodeMath')
    mult_time_speed1.operation = 'MULTIPLY'
    mult_time_speed1.location = (-1200, 600)
    links.new(time_node.outputs['Value'], mult_time_speed1.inputs[0])
    links.new(group_input.outputs['Speed 1'], mult_time_speed1.inputs[1])

    add_phase1 = nodes.new(type='ShaderNodeMath')
    add_phase1.operation = 'ADD'
    add_phase1.location = (-1000, 650)
    links.new(mult_x_freq1.outputs['Value'], add_phase1.inputs[0])
    links.new(mult_time_speed1.outputs['Value'], add_phase1.inputs[1])

    sin1 = nodes.new(type='ShaderNodeMath')
    sin1.operation = 'SINE'
    sin1.location = (-800, 650)
    links.new(add_phase1.outputs['Value'], sin1.inputs[0])

    # Wave 2
    mult_x_freq2 = nodes.new(type='ShaderNodeMath')
    mult_x_freq2.operation = 'MULTIPLY'
    mult_x_freq2.location = (-1200, 500)
    links.new(sep_xyz1.outputs['X'], mult_x_freq2.inputs[0])
    links.new(group_input.outputs['Frequency 2'], mult_x_freq2.inputs[1])

    mult_time_speed2 = nodes.new(type='ShaderNodeMath')
    mult_time_speed2.operation = 'MULTIPLY'
    mult_time_speed2.location = (-1200, 400)
    links.new(time_node.outputs['Value'], mult_time_speed2.inputs[0])
    links.new(group_input.outputs['Speed 2'], mult_time_speed2.inputs[1])

    add_phase2 = nodes.new(type='ShaderNodeMath')
    add_phase2.operation = 'ADD'
    add_phase2.location = (-1000, 450)
    links.new(mult_x_freq2.outputs['Value'], add_phase2.inputs[0])
    links.new(mult_time_speed2.outputs['Value'], add_phase2.inputs[1])

    sin2 = nodes.new(type='ShaderNodeMath')
    sin2.operation = 'SINE'
    sin2.location = (-800, 450)
    links.new(add_phase2.outputs['Value'], sin2.inputs[0])

    # Combine waves to height
    add_sins = nodes.new(type='ShaderNodeMath')
    add_sins.operation = 'ADD'
    add_sins.location = (-600, 550)
    links.new(sin1.outputs['Value'], add_sins.inputs[0])
    links.new(sin2.outputs['Value'], add_sins.inputs[1])

    add_2 = nodes.new(type='ShaderNodeMath')
    add_2.operation = 'ADD'
    add_2.location = (-400, 550)
    links.new(add_sins.outputs['Value'], add_2.inputs[0])
    add_2.inputs[1].default_value = 2.0

    divide_4 = nodes.new(type='ShaderNodeMath')
    divide_4.operation = 'DIVIDE'
    divide_4.location = (-200, 550)
    links.new(add_2.outputs['Value'], divide_4.inputs[0])
    divide_4.inputs[1].default_value = 4.0

    mult_amp = nodes.new(type='ShaderNodeMath')
    mult_amp.operation = 'MULTIPLY'
    mult_amp.location = (0, 550)
    links.new(divide_4.outputs['Value'], mult_amp.inputs[0])
    links.new(group_input.outputs['Amplitude'], mult_amp.inputs[1])

    add_base = nodes.new(type='ShaderNodeMath')
    add_base.operation = 'ADD'
    add_base.location = (200, 550)
    links.new(mult_amp.outputs['Value'], add_base.inputs[0])
    links.new(group_input.outputs['Base Height'], add_base.inputs[1])

    # 6. --- INSTANCE ON POINTS WITH SCALE ---
    scale_combine = nodes.new(type='ShaderNodeCombineXYZ')
    scale_combine.location = (200, 300)
    scale_combine.inputs['X'].default_value = 1.0
    scale_combine.inputs['Y'].default_value = 1.0
    links.new(add_base.outputs['Value'], scale_combine.inputs['Z'])

    instance_on_points = nodes.new(type='GeometryNodeInstanceOnPoints')
    instance_on_points.location = (400, 200)
    links.new(grid.outputs['Mesh'], instance_on_points.inputs['Points'])
    links.new(cube.outputs['Mesh'], instance_on_points.inputs['Instance'])
    links.new(scale_combine.outputs['Vector'], instance_on_points.inputs['Scale'])

    # 7. --- COMPUTE HEIGHT FIELD ON INSTANCES FOR TRANSLATION ---
    position2 = nodes.new(type='GeometryNodeInputPosition')
    position2.location = (400, -400)

    sep_xyz2 = nodes.new(type='ShaderNodeSeparateXYZ')
    sep_xyz2.location = (600, -400)
    links.new(position2.outputs['Position'], sep_xyz2.inputs['Vector'])

    # Wave 1 (duplicate computation)
    mult_x_freq1_2 = nodes.new(type='ShaderNodeMath')
    mult_x_freq1_2.operation = 'MULTIPLY'
    mult_x_freq1_2.location = (800, -300)
    links.new(sep_xyz2.outputs['X'], mult_x_freq1_2.inputs[0])
    links.new(group_input.outputs['Frequency 1'], mult_x_freq1_2.inputs[1])

    mult_time_speed1_2 = nodes.new(type='ShaderNodeMath')
    mult_time_speed1_2.operation = 'MULTIPLY'
    mult_time_speed1_2.location = (800, -400)
    links.new(time_node.outputs['Value'], mult_time_speed1_2.inputs[0])
    links.new(group_input.outputs['Speed 1'], mult_time_speed1_2.inputs[1])

    add_phase1_2 = nodes.new(type='ShaderNodeMath')
    add_phase1_2.operation = 'ADD'
    add_phase1_2.location = (1000, -350)
    links.new(mult_x_freq1_2.outputs['Value'], add_phase1_2.inputs[0])
    links.new(mult_time_speed1_2.outputs['Value'], add_phase1_2.inputs[1])

    sin1_2 = nodes.new(type='ShaderNodeMath')
    sin1_2.operation = 'SINE'
    sin1_2.location = (1200, -350)
    links.new(add_phase1_2.outputs['Value'], sin1_2.inputs[0])

    # Wave 2 (duplicate computation)
    mult_x_freq2_2 = nodes.new(type='ShaderNodeMath')
    mult_x_freq2_2.operation = 'MULTIPLY'
    mult_x_freq2_2.location = (800, -500)
    links.new(sep_xyz2.outputs['X'], mult_x_freq2_2.inputs[0])
    links.new(group_input.outputs['Frequency 2'], mult_x_freq2_2.inputs[1])

    mult_time_speed2_2 = nodes.new(type='ShaderNodeMath')
    mult_time_speed2_2.operation = 'MULTIPLY'
    mult_time_speed2_2.location = (800, -600)
    links.new(time_node.outputs['Value'], mult_time_speed2_2.inputs[0])
    links.new(group_input.outputs['Speed 2'], mult_time_speed2_2.inputs[1])

    add_phase2_2 = nodes.new(type='ShaderNodeMath')
    add_phase2_2.operation = 'ADD'
    add_phase2_2.location = (1000, -550)
    links.new(mult_x_freq2_2.outputs['Value'], add_phase2_2.inputs[0])
    links.new(mult_time_speed2_2.outputs['Value'], add_phase2_2.inputs[1])

    sin2_2 = nodes.new(type='ShaderNodeMath')
    sin2_2.operation = 'SINE'
    sin2_2.location = (1200, -550)
    links.new(add_phase2_2.outputs['Value'], sin2_2.inputs[0])

    # Combine waves to height
    add_sins_2 = nodes.new(type='ShaderNodeMath')
    add_sins_2.operation = 'ADD'
    add_sins_2.location = (1400, -450)
    links.new(sin1_2.outputs['Value'], add_sins_2.inputs[0])
    links.new(sin2_2.outputs['Value'], add_sins_2.inputs[1])

    add_2_2 = nodes.new(type='ShaderNodeMath')
    add_2_2.operation = 'ADD'
    add_2_2.location = (1600, -450)
    links.new(add_sins_2.outputs['Value'], add_2_2.inputs[0])
    add_2_2.inputs[1].default_value = 2.0

    divide_4_2 = nodes.new(type='ShaderNodeMath')
    divide_4_2.operation = 'DIVIDE'
    divide_4_2.location = (1800, -450)
    links.new(add_2_2.outputs['Value'], divide_4_2.inputs[0])
    divide_4_2.inputs[1].default_value = 4.0

    mult_amp_2 = nodes.new(type='ShaderNodeMath')
    mult_amp_2.operation = 'MULTIPLY'
    mult_amp_2.location = (2000, -450)
    links.new(divide_4_2.outputs['Value'], mult_amp_2.inputs[0])
    links.new(group_input.outputs['Amplitude'], mult_amp_2.inputs[1])

    add_base_2 = nodes.new(type='ShaderNodeMath')
    add_base_2.operation = 'ADD'
    add_base_2.location = (2200, -450)
    links.new(mult_amp_2.outputs['Value'], add_base_2.inputs[0])
    links.new(group_input.outputs['Base Height'], add_base_2.inputs[1])

    # Translation vector (0, 0, height / 2)
    divide_2 = nodes.new(type='ShaderNodeMath')
    divide_2.operation = 'DIVIDE'
    divide_2.location = (2400, -450)
    links.new(add_base_2.outputs['Value'], divide_2.inputs[0])
    divide_2.inputs[1].default_value = 2.0

    trans_combine = nodes.new(type='ShaderNodeCombineXYZ')
    trans_combine.location = (2600, -450)
    trans_combine.inputs['X'].default_value = 0.0
    trans_combine.inputs['Y'].default_value = 0.0
    links.new(divide_2.outputs['Value'], trans_combine.inputs['Z'])

    # 8. --- TRANSLATE INSTANCES ---
    translate_inst = nodes.new(type='GeometryNodeTranslateInstances')
    translate_inst.location = (2800, 200)
    links.new(instance_on_points.outputs['Instances'], translate_inst.inputs['Instances'])
    links.new(trans_combine.outputs['Vector'], translate_inst.inputs['Translation'])

    # 9. --- REALIZE INSTANCES FOR FINAL MESH ---
    realize = nodes.new(type='GeometryNodeRealizeInstances')
    realize.location = (3000, 200)
    links.new(translate_inst.outputs['Instances'], realize.inputs['Geometry'])

    # 10. --- CONNECT TO FINAL OUTPUT ---
    links.new(realize.outputs['Geometry'], group_output.inputs['Geometry'])


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
        modifier = obj.modifiers.new(name="Equalizer Visualizer", type='NODES')

    # Create and build the node group
    node_group = create_geometry_node_group()
    build_animated_equalizer_nodetree(node_group)

    # Assign the new node group to the modifier
    modifier.node_group = node_group
    
    print(f"Successfully created and assigned '{node_group.name}' node group to '{obj.name}'.")

# Execute the main function
setup_and_run()