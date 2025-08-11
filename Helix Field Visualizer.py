# Blender 4.4 — "Helix Field Visualizer" (Geometry Nodes)
# Creates a grid of animated helical tubes with per-instance phase/offset noise,
# twist over length, oscillating scale, and plentiful exposed parameters.

import bpy
import math

# --- Helpers ---------------------------------------------------------------

def ensure_active_object():
    if bpy.context.active_object is None:
        bpy.ops.mesh.primitive_plane_add()
    return bpy.context.active_object

def new_gn_group(name="Helix Field Visualizer"):
    ng = bpy.data.node_groups.new(name, 'GeometryNodeTree')
    # Clear any default nodes if present
    for n in list(ng.nodes):
        ng.nodes.remove(n)
    return ng

# --- Build Node Tree -------------------------------------------------------

def build_helix_field(ng):
    nodes, links, iface = ng.nodes, ng.links, ng.interface

    # 1) Interface (lots of exports)
    # Layout/Placement
    p_cols   = iface.new_socket(name="Columns",   in_out='INPUT', socket_type='NodeSocketInt');   p_cols.default_value, p_cols.min_value, p_cols.max_value = 12, 1, 1024
    p_rows   = iface.new_socket(name="Rows",      in_out='INPUT', socket_type='NodeSocketInt');   p_rows.default_value, p_rows.min_value, p_rows.max_value = 12, 1, 1024
    p_spaceX = iface.new_socket(name="Spacing X", in_out='INPUT', socket_type='NodeSocketFloat'); p_spaceX.default_value, p_spaceX.min_value, p_spaceX.max_value = 0.7, 0.0, 100.0
    p_spaceY = iface.new_socket(name="Spacing Y", in_out='INPUT', socket_type='NodeSocketFloat'); p_spaceY.default_value, p_spaceY.min_value, p_spaceY.max_value = 0.7, 0.0, 100.0

    # Helix shape
    p_height = iface.new_socket(name="Helix Height", in_out='INPUT', socket_type='NodeSocketFloat'); p_height.default_value, p_height.min_value, p_height.max_value = 2.0, 0.01, 50.0
    p_turns  = iface.new_socket(name="Turns",        in_out='INPUT', socket_type='NodeSocketFloat'); p_turns.default_value,  p_turns.min_value,  p_turns.max_value  = 3.0, 0.0, 64.0
    p_amp    = iface.new_socket(name="Radius (Amp)", in_out='INPUT', socket_type='NodeSocketFloat'); p_amp.default_value,    p_amp.min_value,    p_amp.max_value    = 0.25, 0.0, 10.0
    p_twist  = iface.new_socket(name="Twist Over Length", in_out='INPUT', socket_type='NodeSocketFloat'); p_twist.default_value, p_twist.min_value, p_twist.max_value = 0.0, -32.0, 32.0

    # Animation
    p_speed  = iface.new_socket(name="Time Speed",   in_out='INPUT', socket_type='NodeSocketFloat'); p_speed.default_value,  p_speed.min_value,  p_speed.max_value  = 1.0, -10.0, 10.0
    p_freq   = iface.new_socket(name="Angular Freq", in_out='INPUT', socket_type='NodeSocketFloat'); p_freq.default_value,   p_freq.min_value,   p_freq.max_value   = 1.0, 0.0, 10.0
    p_phaseJ = iface.new_socket(name="Per-Instance Phase", in_out='INPUT', socket_type='NodeSocketFloat'); p_phaseJ.default_value, p_phaseJ.min_value, p_phaseJ.max_value = 1.0, 0.0, 10.0

    # Noise modulation
    p_noise_mag   = iface.new_socket(name="Noise Magnitude", in_out='INPUT', socket_type='NodeSocketFloat'); p_noise_mag.default_value, p_noise_mag.min_value, p_noise_mag.max_value = 0.08, 0.0, 2.0
    p_noise_scale = iface.new_socket(name="Noise Scale",     in_out='INPUT', socket_type='NodeSocketFloat'); p_noise_scale.default_value, p_noise_scale.min_value, p_noise_scale.max_value = 3.0, 0.0, 64.0
    p_seed        = iface.new_socket(name="Seed",            in_out='INPUT', socket_type='NodeSocketInt');   p_seed.default_value, p_seed.min_value, p_seed.max_value = 0, 0, 2**31-1

    # Thickness + resolution
    p_profile = iface.new_socket(name="Tube Radius", in_out='INPUT', socket_type='NodeSocketFloat'); p_profile.default_value, p_profile.min_value, p_profile.max_value = 0.035, 0.0005, 5.0
    p_curve_res = iface.new_socket(name="Curve Resolution", in_out='INPUT', socket_type='NodeSocketInt'); p_curve_res.default_value, p_curve_res.min_value, p_curve_res.max_value = 128, 3, 2048
    p_segments  = iface.new_socket(name="Segments", in_out='INPUT', socket_type='NodeSocketInt'); p_segments.default_value, p_segments.min_value, p_segments.max_value = 128, 4, 4096

    # Global scale osc
    p_scale_min = iface.new_socket(name="Scale Min", in_out='INPUT', socket_type='NodeSocketFloat'); p_scale_min.default_value, p_scale_min.min_value, p_scale_min.max_value = 0.75, 0.0, 10.0
    p_scale_max = iface.new_socket(name="Scale Max", in_out='INPUT', socket_type='NodeSocketFloat'); p_scale_max.default_value, p_scale_max.min_value, p_scale_max.max_value = 1.25, 0.0, 10.0

    # Output
    iface.new_socket(name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')

    # Group IO
    n_in  = nodes.new("NodeGroupInput");  n_in.location  = (-1800, 0)
    n_out = nodes.new("NodeGroupOutput"); n_out.location = (1800,  0)

    # 2) Time driver (Value node) — per GEMINI guidance
    time_val = nodes.new("ShaderNodeValue"); time_val.location = (-1800, -300); time_val.label = "Time (Seconds)"
    d = time_val.outputs[0].driver_add('default_value'); d.driver.expression = "frame/24"  # Base seconds; speed applied later
    t_mul = nodes.new("ShaderNodeMath"); t_mul.location = (-1600, -300); t_mul.operation = 'MULTIPLY'
    links.new(time_val.outputs['Value'], t_mul.inputs[0])
    links.new(n_in.outputs['Time Speed'], t_mul.inputs[1])  # apply p_speed

    # 3) Point field (grid -> points)
    grid = nodes.new("GeometryNodeMeshGrid"); grid.location = (-1600, 200)
    links.new(n_in.outputs['Columns'],   grid.inputs['Vertices X'])
    links.new(n_in.outputs['Rows'],      grid.inputs['Vertices Y'])
    links.new(n_in.outputs['Spacing X'], grid.inputs['Size X'])
    links.new(n_in.outputs['Spacing Y'], grid.inputs['Size Y'])

    mesh_to_points = nodes.new("GeometryNodeMeshToPoints"); mesh_to_points.location = (-1400, 200)
    mesh_to_points.inputs['Radius'].default_value = 0.0
    links.new(grid.outputs['Mesh'], mesh_to_points.inputs['Mesh'])

    # Per-instance randomness
    rand_phase = nodes.new("FunctionNodeRandomValue"); rand_phase.location = (-1200, 120)
    rand_phase.data_type = 'FLOAT'
    links.new(n_in.outputs['Seed'], rand_phase.inputs['ID'])
    # Jitter phase scale
    phase_scale = nodes.new("ShaderNodeMath"); phase_scale.location = (-1000, 120); phase_scale.operation = 'MULTIPLY'
    links.new(rand_phase.outputs['Value'], phase_scale.inputs[0])
    links.new(n_in.outputs['Per-Instance Phase'], phase_scale.inputs[1])

    # Instance source: a straight line curve along Z
    curve_line = nodes.new("GeometryNodeCurvePrimitiveLine"); curve_line.location = (-1200, -100)
    # Start (0,0,0), End (0,0,height)
    end_z = nodes.new("ShaderNodeCombineXYZ"); end_z.location = (-1000, -90)
    links.new(n_in.outputs['Helix Height'], end_z.inputs['Z'])
    links.new(end_z.outputs['Vector'], curve_line.inputs['End'])

    # High resolution via Resample
    resample = nodes.new("GeometryNodeResampleCurve"); resample.location = (-800, -80)
    resample.mode = 'COUNT'
    links.new(curve_line.outputs['Curve'], resample.inputs['Curve'])
    links.new(n_in.outputs['Segments'], resample.inputs['Count'])

    # Spline factor (0..1 along length)
    spline_param = nodes.new("GeometryNodeSplineParameter"); spline_param.location = (-600, -80)

    # Angle = 2π*(turns*factor + freq*time) + twist*factor + phase_jitter
    # a) turns*factor
    m_turns = nodes.new("ShaderNodeMath"); m_turns.location = (-400, -180); m_turns.operation = 'MULTIPLY'
    links.new(n_in.outputs['Turns'], m_turns.inputs[0])
    links.new(spline_param.outputs['Factor'], m_turns.inputs[1])

    # b) 2π * ( ... )
    two_pi = nodes.new("ShaderNodeMath"); two_pi.location = (-400, -260); two_pi.operation = 'MULTIPLY'
    two_pi.inputs[1].default_value = 2 * math.pi
    links.new(m_turns.outputs['Value'], two_pi.inputs[0])

    # c) freq*time
    m_freq_time = nodes.new("ShaderNodeMath"); m_freq_time.location = (-600, -260); m_freq_time.operation = 'MULTIPLY'
    links.new(n_in.outputs['Angular Freq'], m_freq_time.inputs[0])
    links.new(t_mul.outputs['Value'],        m_freq_time.inputs[1])

    # d) add freq*time to (2π*turns*factor)
    add_ft = nodes.new("ShaderNodeMath"); add_ft.location = (-200, -220); add_ft.operation = 'ADD'
    links.new(two_pi.outputs['Value'], add_ft.inputs[0])
    links.new(m_freq_time.outputs['Value'], add_ft.inputs[1])

    # e) twist*factor
    m_twist = nodes.new("ShaderNodeMath"); m_twist.location = (-400, -20); m_twist.operation = 'MULTIPLY'
    links.new(n_in.outputs['Twist Over Length'], m_twist.inputs[0])
    links.new(spline_param.outputs['Factor'],     m_twist.inputs[1])

    # f) add twist
    add_twist = nodes.new("ShaderNodeMath"); add_twist.location = (-200, -60); add_twist.operation = 'ADD'
    links.new(add_ft.outputs['Value'], add_twist.inputs[0])
    links.new(m_twist.outputs['Value'], add_twist.inputs[1])

    # g) add per-instance phase jitter
    add_phase = nodes.new("ShaderNodeMath"); add_phase.location = (0, -60); add_phase.operation = 'ADD'
    links.new(add_twist.outputs['Value'], add_phase.inputs[0])
    links.new(phase_scale.outputs['Value'], add_phase.inputs[1])

    # Helix XY = amp * (cos(angle), sin(angle))
    cos_a = nodes.new("ShaderNodeMath"); cos_a.location = (200, -120); cos_a.operation = 'COSINE'
    sin_a = nodes.new("ShaderNodeMath"); sin_a.location = (200,  -20); sin_a.operation = 'SINE'
    links.new(add_phase.outputs['Value'], cos_a.inputs[0])
    links.new(add_phase.outputs['Value'], sin_a.inputs[0])

    mul_x = nodes.new("ShaderNodeMath"); mul_x.location = (400, -120); mul_x.operation = 'MULTIPLY'
    mul_y = nodes.new("ShaderNodeMath"); mul_y.location = (400,  -20); mul_y.operation = 'MULTIPLY'
    links.new(cos_a.outputs['Value'], mul_x.inputs[0]); links.new(n_in.outputs['Radius (Amp)'], mul_x.inputs[1])
    links.new(sin_a.outputs['Value'], mul_y.inputs[0]); links.new(n_in.outputs['Radius (Amp)'], mul_y.inputs[1])

    helix_xy = nodes.new("ShaderNodeCombineXYZ"); helix_xy.location = (600, -60)
    links.new(mul_x.outputs['Value'], helix_xy.inputs['X'])
    links.new(mul_y.outputs['Value'], helix_xy.inputs['Y'])
    # Z stays as original position from the line
    pos = nodes.new("GeometryNodeInputPosition"); pos.location = (400, -260)
    links.new(pos.outputs['Position'], helix_xy.inputs['Z'])

    # Noise offset for organic wobble (per-point & over length)
    # Simple noise via RandomValue mixes into XY
    rand_off = nodes.new("FunctionNodeRandomValue"); rand_off.location = (200, 160); rand_off.data_type = 'FLOAT_VECTOR'
    links.new(n_in.outputs['Seed'], rand_off.inputs['ID'])

    noise_scale = nodes.new("ShaderNodeMath"); noise_scale.location = (400, 160); noise_scale.operation = 'MULTIPLY'
    links.new(n_in.outputs['Noise Magnitude'], noise_scale.inputs[0])
    # Use the X component of vector random as scalar for simplicity
    sep_rand = nodes.new("ShaderNodeSeparateXYZ"); sep_rand.location = (200, 240)
    links.new(rand_off.outputs['Value'], sep_rand.inputs['Vector'])
    links.new(sep_rand.outputs['X'], noise_scale.inputs[1])

    noise_vec = nodes.new("ShaderNodeCombineXYZ"); noise_vec.location = (600, 120)
    # Vary across length using sin(factor * noise_scale_ui)
    noise_phase = nodes.new("ShaderNodeMath"); noise_phase.location = (200, 320); noise_phase.operation = 'MULTIPLY'
    links.new(spline_param.outputs['Factor'], noise_phase.inputs[0])
    links.new(n_in.outputs['Noise Scale'],     noise_phase.inputs[1])

    noise_s = nodes.new("ShaderNodeMath"); noise_s.location = (400, 320); noise_s.operation = 'SINE'
    links.new(noise_phase.outputs['Value'], noise_s.inputs[0])

    mul_noise = nodes.new("ShaderNodeMath"); mul_noise.location = (600, 280); mul_noise.operation = 'MULTIPLY'
    links.new(noise_s.outputs['Value'], mul_noise.inputs[0])
    links.new(noise_scale.outputs['Value'], mul_noise.inputs[1])

    links.new(mul_noise.outputs['Value'], noise_vec.inputs['X'])
    links.new(mul_noise.outputs['Value'], noise_vec.inputs['Y'])

    add_xy_noise = nodes.new("ShaderNodeVectorMath"); add_xy_noise.location = (800, 40); add_xy_noise.operation = 'ADD'
    links.new(helix_xy.outputs['Vector'], add_xy_noise.inputs[0])
    links.new(noise_vec.outputs['Vector'], add_xy_noise.inputs[1])

    # Set helix positions
    set_pos = nodes.new("GeometryNodeSetPosition"); set_pos.location = (1000, -60)
    links.new(resample.outputs['Curve'], set_pos.inputs['Geometry'])
    links.new(add_xy_noise.outputs['Vector'], set_pos.inputs['Position'])

    # Convert to tube
    prof_circle = nodes.new("GeometryNodeCurvePrimitiveCircle"); prof_circle.location = (1200, -220)
    links.new(n_in.outputs['Curve Resolution'], prof_circle.inputs['Resolution'])
    links.new(n_in.outputs['Tube Radius'],      prof_circle.inputs['Radius'])

    curve_to_mesh = nodes.new("GeometryNodeCurveToMesh"); curve_to_mesh.location = (1400, -60)
    links.new(set_pos.outputs['Geometry'], curve_to_mesh.inputs['Curve'])
    links.new(prof_circle.outputs['Curve'], curve_to_mesh.inputs['Profile Curve'])

    # Instance the tube on grid points
    inst_on_pts = nodes.new("GeometryNodeInstanceOnPoints"); inst_on_pts.location = (-1000, 420)
    links.new(mesh_to_points.outputs['Points'], inst_on_pts.inputs['Points'])
    links.new(curve_to_mesh.outputs['Mesh'],    inst_on_pts.inputs['Instance'])

    realize = nodes.new("GeometryNodeRealizeInstances"); realize.location = (-800, 420)
    links.new(inst_on_pts.outputs['Instances'], realize.inputs['Geometry'])

    # Global oscillating scale (SINE → Map Range → Transform), similar pattern as example
    s_sine = nodes.new("ShaderNodeMath"); s_sine.location = (-600, 420); s_sine.operation = 'SINE'
    links.new(t_mul.outputs['Value'], s_sine.inputs[0])

    s_map = nodes.new("ShaderNodeMapRange"); s_map.location = (-400, 420)
    s_map.inputs['From Min'].default_value = -1.0
    s_map.inputs['From Max'].default_value =  1.0
    links.new(s_sine.outputs['Value'], s_map.inputs['Value'])
    links.new(n_in.outputs['Scale Min'], s_map.inputs['To Min'])
    links.new(n_in.outputs['Scale Max'], s_map.inputs['To Max'])

    s_vec = nodes.new("ShaderNodeCombineXYZ"); s_vec.location = (-240, 420)
    links.new(s_map.outputs['Result'], s_vec.inputs['X'])
    links.new(s_map.outputs['Result'], s_vec.inputs['Y'])
    links.new(s_map.outputs['Result'], s_vec.inputs['Z'])

    transform = nodes.new("GeometryNodeTransform"); transform.location = (-60, 420)
    links.new(realize.outputs['Geometry'], transform.inputs['Geometry'])
    links.new(s_vec.outputs['Vector'],     transform.inputs['Scale'])

    # Final out
    links.new(transform.outputs['Geometry'], n_out.inputs['Geometry'])

# --- Attach to an object as a modifier ------------------------------------

def setup_and_run():
    obj = ensure_active_object()

    # Reuse an existing GN modifier if present
    mod = None
    for m in obj.modifiers:
        if m.type == 'NODES':
            mod = m
            break
    if mod is None:
        mod = obj.modifiers.new(name="Helix Field", type='NODES')

    ng = new_gn_group()
    build_helix_field(ng)
    mod.node_group = ng
    print(f"Assigned node group '{ng.name}' to '{obj.name}'")

# Execute
setup_and_run()
