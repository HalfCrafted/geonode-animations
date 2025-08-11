# Blender 4.4 — Geometry Nodes "Radial Kaleido Field" Visualizer (keyword-arg sockets, star-from-circle)
# Driver-based time, lots of exposed parameters, and procedural star instances.

import bpy
import math

def create_geometry_node_group(name="Radial Kaleido Field"):
    node_group = bpy.data.node_groups.new(name, 'GeometryNodeTree')
    for n in list(node_group.nodes):
        node_group.nodes.remove(n)
    return node_group

def build_kaleido_tree(node_group):
    links = node_group.links
    nodes = node_group.nodes

    # --- Interface (use keyword args, include description=) ---
    def add_float(name, default, lo, hi, desc):
        s = node_group.interface.new_socket(
            name=name, in_out='INPUT', socket_type='NodeSocketFloat', description=desc
        )
        s.default_value = default
        s.min_value = lo
        s.max_value = hi
        return s

    def add_int(name, default, lo, hi, desc):
        s = node_group.interface.new_socket(
            name=name, in_out='INPUT', socket_type='NodeSocketInt', description=desc
        )
        s.default_value = default
        s.min_value = lo
        s.max_value = hi
        return s

    # Field / grid
    add_float('Grid Size X', 20.0, 0.1, 500.0, 'World size of grid in X')
    add_float('Grid Size Y', 20.0, 0.1, 500.0, 'World size of grid in Y')
    add_int  ('Grid Res X', 100, 2, 2048, 'Vertex resolution in X')
    add_int  ('Grid Res Y', 100, 2, 2048, 'Vertex resolution in Y')

    # Animation
    add_float('Time Speed', 1.0, 0.0, 10.0, 'Multiplier for time driver (frame/24)')
    add_float('Spin Speed', 1.0, -20.0, 20.0, 'Per-instance Z spin speed')

    # Radial sine
    add_float('Radial Freq', 2.0, 0.0, 50.0, 'Ring frequency (cycles per unit radius * 2π)')
    add_float('Radial Amp',  0.5, 0.0, 10.0, 'Amplitude of radial sine displacement')
    rp = node_group.interface.new_socket(
        name='Radial Phase', in_out='INPUT', socket_type='NodeSocketFloat', description='Phase offset (radians)'
    )
    rp.default_value = 0.0
    rp.min_value = -math.pi*8
    rp.max_value =  math.pi*8

    # Noise
    add_float('Noise Scale', 2.5, 0.01, 100.0, 'Noise scale')
    add_float('Noise Detail', 3.0, 0.0, 16.0, 'Noise detail (FBM)')
    add_float('Noise Distortion', 0.0, 0.0, 1.0, 'Noise domain warp')
    add_float('Noise Amp', 0.35, 0.0, 10.0, 'Noise contribution amplitude')

    # Instance shape and tube
    add_int  ('Star Points', 8, 3, 64, 'Number of star points (pre-resample x2)')
    add_float('Star Inner Radius', 0.15, 0.001, 10.0, 'Inner radius of the star')
    add_float('Star Outer Radius', 0.35, 0.001, 10.0, 'Outer radius of the star')
    add_float('Tube Radius', 0.02, 0.001, 1.0, 'Tube profile radius')

    # Placement / scale
    add_float('Instance Scale', 0.85, 0.01, 10.0, 'Uniform scale of instances')
    add_float('Radial Scale', 1.0, 0.01, 10.0, 'Scale factor applied to radial distance')

    node_group.interface.new_socket(
        name='Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry', description='Output geometry'
    )

    group_in  = nodes.new('NodeGroupInput');  group_in.location  = (-1800, 0)
    group_out = nodes.new('NodeGroupOutput'); group_out.location = (1800, 0)

    # --- Time driver: frame/24 * Time Speed ---
    time_val = nodes.new('ShaderNodeValue'); time_val.location = (-1800, -350); time_val.label = "Time (Seconds)"
    drv = time_val.outputs[0].driver_add('default_value'); drv.driver.expression = 'frame / 24'
    time_speed_mult = nodes.new('ShaderNodeMath'); time_speed_mult.operation = 'MULTIPLY'; time_speed_mult.location = (-1600, -350)
    links.new(time_val.outputs['Value'], time_speed_mult.inputs[0])
    links.new(group_in.outputs['Time Speed'], time_speed_mult.inputs[1])

    # --- Grid -> Points ---
    grid = nodes.new('GeometryNodeMeshGrid'); grid.location = (-1600, 250)
    links.new(group_in.outputs['Grid Size X'], grid.inputs['Size X'])
    links.new(group_in.outputs['Grid Size Y'], grid.inputs['Size Y'])
    links.new(group_in.outputs['Grid Res X'], grid.inputs['Vertices X'])
    links.new(group_in.outputs['Grid Res Y'], grid.inputs['Vertices Y'])

    mesh_to_points = nodes.new('GeometryNodeMeshToPoints'); mesh_to_points.location = (-1400, 250)
    mesh_to_points.inputs['Radius'].default_value = 0.0
    links.new(grid.outputs['Mesh'], mesh_to_points.inputs['Mesh'])

    # --- Radial distance in XY ---
    pos = nodes.new('GeometryNodeInputPosition'); pos.location = (-1400, 0)
    xy_mask = nodes.new('ShaderNodeCombineXYZ'); xy_mask.location = (-1400, -120)
    xy_mask.inputs['X'].default_value = 1.0; xy_mask.inputs['Y'].default_value = 1.0; xy_mask.inputs['Z'].default_value = 0.0
    sep_xy = nodes.new('ShaderNodeVectorMath'); sep_xy.location = (-1200, -40); sep_xy.operation = 'SCALE'
    links.new(pos.outputs['Position'], sep_xy.inputs[0]); links.new(xy_mask.outputs['Vector'], sep_xy.inputs[1])
    length_xy = nodes.new('ShaderNodeVectorMath'); length_xy.location = (-1000, 0); length_xy.operation = 'LENGTH'
    links.new(sep_xy.outputs['Vector'], length_xy.inputs[0])

    radial_scale_mult = nodes.new('ShaderNodeMath'); radial_scale_mult.operation = 'MULTIPLY'; radial_scale_mult.location = (-800, 0)
    links.new(length_xy.outputs['Value'], radial_scale_mult.inputs[0])
    links.new(group_in.outputs['Radial Scale'], radial_scale_mult.inputs[1])

    # --- Sine height ---
    two_pi = nodes.new('ShaderNodeMath'); two_pi.operation='MULTIPLY'; two_pi.location = (-820,-160)
    two_pi.inputs[0].default_value = 2.0*math.pi
    links.new(group_in.outputs['Radial Freq'], two_pi.inputs[1])

    sine_arg_mul = nodes.new('ShaderNodeMath'); sine_arg_mul.operation='MULTIPLY'; sine_arg_mul.location=(-640,-80)
    links.new(radial_scale_mult.outputs['Value'], sine_arg_mul.inputs[0])
    links.new(two_pi.outputs['Value'], sine_arg_mul.inputs[1])

    sine_arg_add_phase = nodes.new('ShaderNodeMath'); sine_arg_add_phase.operation='ADD'; sine_arg_add_phase.location=(-460,-80)
    links.new(sine_arg_mul.outputs['Value'], sine_arg_add_phase.inputs[0])
    links.new(group_in.outputs['Radial Phase'], sine_arg_add_phase.inputs[1])

    sine_arg_add_time = nodes.new('ShaderNodeMath'); sine_arg_add_time.operation='ADD'; sine_arg_add_time.location=(-280,-80)
    links.new(sine_arg_add_phase.outputs['Value'], sine_arg_add_time.inputs[0])
    links.new(time_speed_mult.outputs['Value'], sine_arg_add_time.inputs[1])

    sine_val = nodes.new('ShaderNodeMath'); sine_val.operation='SINE'; sine_val.location=(-100,-80)
    links.new(sine_arg_add_time.outputs['Value'], sine_val.inputs[0])

    sine_amp = nodes.new('ShaderNodeMath'); sine_amp.operation='MULTIPLY'; sine_amp.location=(80,-80)
    links.new(sine_val.outputs['Value'], sine_amp.inputs[0])
    links.new(group_in.outputs['Radial Amp'], sine_amp.inputs[1])

    # --- Noise layer ---
    noise = nodes.new('ShaderNodeTexNoise'); noise.location = (-640,-300)
    links.new(pos.outputs['Position'], noise.inputs['Vector'])
    links.new(group_in.outputs['Noise Scale'], noise.inputs['Scale'])
    links.new(group_in.outputs['Noise Detail'], noise.inputs['Detail'])
    links.new(group_in.outputs['Noise Distortion'], noise.inputs['Distortion'])

    noise_centered = nodes.new('ShaderNodeMath'); noise_centered.location=(-460,-300); noise_centered.operation='SUBTRACT'
    noise_centered.inputs[0].default_value = 0.0
    links.new(noise.outputs['Fac'], noise_centered.inputs[1])

    noise_map = nodes.new('ShaderNodeMapRange'); noise_map.location=(-280,-300)
    noise_map.inputs['From Min'].default_value=-1.0
    noise_map.inputs['From Max'].default_value=0.0
    noise_map.inputs['To Min'].default_value=-1.0
    noise_map.inputs['To Max'].default_value=1.0
    links.new(noise_centered.outputs['Value'], noise_map.inputs['Value'])

    noise_amp_mul = nodes.new('ShaderNodeMath'); noise_amp_mul.location=(-100,-300); noise_amp_mul.operation='MULTIPLY'
    links.new(noise_map.outputs['Result'], noise_amp_mul.inputs[0])
    links.new(group_in.outputs['Noise Amp'], noise_amp_mul.inputs[1])

    # --- Height sum -> Set Position Z offset ---
    height_sum = nodes.new('ShaderNodeMath'); height_sum.location=(260,-180); height_sum.operation='ADD'
    links.new(sine_amp.outputs['Value'], height_sum.inputs[0])
    links.new(noise_amp_mul.outputs['Value'], height_sum.inputs[1])

    combine_z = nodes.new('ShaderNodeCombineXYZ'); combine_z.location=(440,-120)
    links.new(height_sum.outputs['Value'], combine_z.inputs['Z'])

    set_pos = nodes.new('GeometryNodeSetPosition'); set_pos.location=(650,240)
    links.new(mesh_to_points.outputs['Points'], set_pos.inputs['Geometry'])
    links.new(combine_z.outputs['Vector'], set_pos.inputs['Offset'])

    # --- Procedural star from circle + resample + alternating curve radius ---
    circle = nodes.new('GeometryNodeCurvePrimitiveCircle'); circle.location = (-300, 420)

    resample = nodes.new('GeometryNodeResampleCurve'); resample.location = (-120, 420)
    resample.mode = 'COUNT'
    mul2 = nodes.new('ShaderNodeMath'); mul2.operation='MULTIPLY'; mul2.location = (-300, 540)
    links.new(group_in.outputs['Star Points'], mul2.inputs[0])
    mul2.inputs[1].default_value = 2.0
    links.new(mul2.outputs['Value'], resample.inputs['Count'])
    links.new(circle.outputs['Curve'], resample.inputs['Curve'])

    idx = nodes.new('GeometryNodeInputIndex'); idx.location = (60, 520)
    mod2 = nodes.new('ShaderNodeMath'); mod2.operation='MODULO'; mod2.location = (220, 520)
    links.new(idx.outputs['Index'], mod2.inputs[0]); mod2.inputs[1].default_value = 2.0

    one_minus = nodes.new('ShaderNodeMath'); one_minus.operation='SUBTRACT'; one_minus.location = (380, 520)
    one_minus.inputs[0].default_value = 1.0
    links.new(mod2.outputs['Value'], one_minus.inputs[1])  # 1 - (i % 2)

    inner_mul = nodes.new('ShaderNodeMath'); inner_mul.operation='MULTIPLY'; inner_mul.location = (540, 560)
    links.new(group_in.outputs['Star Inner Radius'], inner_mul.inputs[0]); links.new(one_minus.outputs['Value'], inner_mul.inputs[1])

    outer_mul = nodes.new('ShaderNodeMath'); outer_mul.operation='MULTIPLY'; outer_mul.location = (540, 480)
    links.new(group_in.outputs['Star Outer Radius'], outer_mul.inputs[0]); links.new(mod2.outputs['Value'], outer_mul.inputs[1])

    radius_sum = nodes.new('ShaderNodeMath'); radius_sum.operation='ADD'; radius_sum.location = (720, 520)
    links.new(inner_mul.outputs['Value'], radius_sum.inputs[0]); links.new(outer_mul.outputs['Value'], radius_sum.inputs[1])

    set_curve_radius = nodes.new('GeometryNodeSetCurveRadius'); set_curve_radius.location = (900, 420)
    links.new(resample.outputs['Curve'], set_curve_radius.inputs['Curve'])
    links.new(radius_sum.outputs['Value'], set_curve_radius.inputs['Radius'])

    profile = nodes.new('GeometryNodeCurvePrimitiveCircle'); profile.location = (1080, 420)
    links.new(group_in.outputs['Tube Radius'], profile.inputs['Radius'])

    curve_to_mesh = nodes.new('GeometryNodeCurveToMesh'); curve_to_mesh.location = (1260, 420)
    links.new(set_curve_radius.outputs['Curve'], curve_to_mesh.inputs['Curve'])
    links.new(profile.outputs['Curve'], curve_to_mesh.inputs['Profile Curve'])

    # --- Instance on Points + per-instance rotation ---
    inst_on_points = nodes.new('GeometryNodeInstanceOnPoints'); inst_on_points.location = (900, 240)
    links.new(set_pos.outputs['Geometry'], inst_on_points.inputs['Points'])
    links.new(curve_to_mesh.outputs['Mesh'], inst_on_points.inputs['Instance'])

    scale_mul = nodes.new('ShaderNodeMath'); scale_mul.operation='MULTIPLY'; scale_mul.location = (740, 40)
    scale_mul.inputs[0].default_value = 1.0
    links.new(group_in.outputs['Instance Scale'], scale_mul.inputs[1])
    links.new(scale_mul.outputs['Value'], inst_on_points.inputs['Scale'])

    # angle = (frame/24 * Time Speed * Spin Speed) + 0.1*(radial*2π*freq)
    swirl_comp = nodes.new('ShaderNodeMath'); swirl_comp.operation='MULTIPLY'; swirl_comp.location = (460, 40)
    swirl_comp.inputs[1].default_value = 0.1
    links.new(sine_arg_mul.outputs['Value'], swirl_comp.inputs[0])

    spin_base = nodes.new('ShaderNodeMath'); spin_base.operation='MULTIPLY'; spin_base.location = (460, -40)
    links.new(time_speed_mult.outputs['Value'], spin_base.inputs[0]); links.new(group_in.outputs['Spin Speed'], spin_base.inputs[1])

    spin_angle = nodes.new('ShaderNodeMath'); spin_angle.operation='ADD'; spin_angle.location = (620, 0)
    links.new(spin_base.outputs['Value'], spin_angle.inputs[0]); links.new(swirl_comp.outputs['Value'], spin_angle.inputs[1])

    rot_euler = nodes.new('ShaderNodeCombineXYZ'); rot_euler.location = (620, 120)
    links.new(spin_angle.outputs['Value'], rot_euler.inputs['Z'])
    links.new(rot_euler.outputs['Vector'], inst_on_points.inputs['Rotation'])

    # --- Realize + Transform + Output ---
    realize = nodes.new('GeometryNodeRealizeInstances'); realize.location = (1120, 240)
    links.new(inst_on_points.outputs['Instances'], realize.inputs['Geometry'])

    xform = nodes.new('GeometryNodeTransform'); xform.location = (1320, 240)
    xform.inputs['Scale'].default_value = (1.0, 1.0, 1.0)
    links.new(realize.outputs['Geometry'], xform.inputs['Geometry'])
    links.new(xform.outputs['Geometry'], group_out.inputs['Geometry'])

def setup_and_run():
    if bpy.context.active_object is None:
        bpy.ops.mesh.primitive_plane_add()
    obj = bpy.context.active_object

    modifier = next((m for m in obj.modifiers if m.type == 'NODES'), None)
    if modifier is None:
        modifier = obj.modifiers.new(name="Radial Kaleido Field", type='NODES')

    node_group = create_geometry_node_group()
    build_kaleido_tree(node_group)
    modifier.node_group = node_group
    print(f"Successfully created and assigned '{node_group.name}' to '{obj.name}'.")

setup_and_run()
