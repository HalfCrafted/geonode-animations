# Blender 4.4 — "Cyclone Sunburst Visualizer" (Geometry Nodes, spiral via math)
# Animated spiral ribbons orbiting a ring with wobble, twist, tilt, noise, and global pulsing.

import bpy
import math

# ---------------------------- Helpers --------------------------------------
def ensure_active_object():
    if bpy.context.active_object is None:
        bpy.ops.mesh.primitive_plane_add()
    return bpy.context.active_object

def new_gn_group(name="Cyclone Sunburst Visualizer"):
    ng = bpy.data.node_groups.new(name, 'GeometryNodeTree')
    for n in list(ng.nodes):
        ng.nodes.remove(n)
    return ng

# -------------------------- Build Node Tree --------------------------------
def build_cyclone_sunburst(ng):
    nodes, links, iface = ng.nodes, ng.links, ng.interface

    # ---- Interface (EXPOSED PARAMS) ----
    p_arms = iface.new_socket(
        name="Arms", in_out='INPUT', socket_type='NodeSocketInt',
        description="Number of spiral arms around the ring"
    ); p_arms.default_value, p_arms.min_value, p_arms.max_value = 16, 1, 1024

    p_ringR = iface.new_socket(
        name="Ring Radius", in_out='INPUT', socket_type='NodeSocketFloat',
        description="Radius of the placement ring"
    ); p_ringR.default_value, p_ringR.min_value, p_ringR.max_value = 2.5, 0.0, 100.0

    p_armTilt = iface.new_socket(
        name="Arm Tilt (deg)", in_out='INPUT', socket_type='NodeSocketFloat',
        description="Tilt each arm around local X (degrees)"
    ); p_armTilt.default_value, p_armTilt.min_value, p_armTilt.max_value = 8.0, -90.0, 90.0

    p_turns = iface.new_socket(
        name="Spiral Turns", in_out='INPUT', socket_type='NodeSocketFloat',
        description="Number of turns per arm"
    ); p_turns.default_value, p_turns.min_value, p_turns.max_value = 5.0, 0.0, 128.0

    p_height = iface.new_socket(
        name="Spiral Height", in_out='INPUT', socket_type='NodeSocketFloat',
        description="Height of each spiral arm"
    ); p_height.default_value, p_height.min_value, p_height.max_value = 1.5, 0.0, 100.0

    p_rStart = iface.new_socket(
        name="Radius Start", in_out='INPUT', socket_type='NodeSocketFloat',
        description="Inner radius of the spiral arm"
    ); p_rStart.default_value, p_rStart.min_value, p_rStart.max_value = 0.25, 0.0, 100.0

    p_rEnd = iface.new_socket(
        name="Radius End", in_out='INPUT', socket_type='NodeSocketFloat',
        description="Outer radius of the spiral arm"
    ); p_rEnd.default_value, p_rEnd.min_value, p_rEnd.max_value = 0.75, 0.0, 100.0

    p_segments = iface.new_socket(
        name="Segments", in_out='INPUT', socket_type='NodeSocketInt',
        description="Curve sample count for each arm"
    ); p_segments.default_value, p_segments.min_value, p_segments.max_value = 256, 8, 8192

    p_speed = iface.new_socket(
        name="Time Speed", in_out='INPUT', socket_type='NodeSocketFloat',
        description="Global time multiplier"
    ); p_speed.default_value, p_speed.min_value, p_speed.max_value = 1.0, -10.0, 10.0

    p_spinSpd = iface.new_socket(
        name="Orbit Spin Speed", in_out='INPUT', socket_type='NodeSocketFloat',
        description="Spin speed of the arm ring (radians/sec)"
    ); p_spinSpd.default_value, p_spinSpd.min_value, p_spinSpd.max_value = 0.4, -10.0, 10.0

    p_phaseJ = iface.new_socket(
        name="Per-Arm Phase", in_out='INPUT', socket_type='NodeSocketFloat',
        description="Random phase offset per arm"
    ); p_phaseJ.default_value, p_phaseJ.min_value, p_phaseJ.max_value = 1.0, 0.0, 10.0

    p_wobAmp = iface.new_socket(
        name="Wobble Amp", in_out='INPUT', socket_type='NodeSocketFloat',
        description="Amplitude of arm wobble"
    ); p_wobAmp.default_value, p_wobAmp.min_value, p_wobAmp.max_value = 0.25, 0.0, 10.0

    p_wobFreq = iface.new_socket(
        name="Wobble Freq", in_out='INPUT', socket_type='NodeSocketFloat',
        description="Frequency of arm wobble"
    ); p_wobFreq.default_value, p_wobFreq.min_value, p_wobFreq.max_value = 3.0, 0.0, 64.0

    p_twist = iface.new_socket(
        name="Twist Over Length", in_out='INPUT', socket_type='NodeSocketFloat',
        description="Angular twist over arm length"
    ); p_twist.default_value, p_twist.min_value, p_twist.max_value = 4.0, -64.0, 64.0

    p_noiseMag = iface.new_socket(
        name="Noise Magnitude", in_out='INPUT', socket_type='NodeSocketFloat',
        description="Strength of per-arm/per-point noise"
    ); p_noiseMag.default_value, p_noiseMag.min_value, p_noiseMag.max_value = 0.1, 0.0, 5.0

    p_noiseScale = iface.new_socket(
        name="Noise Scale", in_out='INPUT', socket_type='NodeSocketFloat',
        description="Lengthwise noise scale"
    ); p_noiseScale.default_value, p_noiseScale.min_value, p_noiseScale.max_value = 2.0, 0.0, 64.0

    p_seed = iface.new_socket(
        name="Seed", in_out='INPUT', socket_type='NodeSocketInt',
        description="Random seed"
    ); p_seed.default_value, p_seed.min_value, p_seed.max_value = 0, 0, 2**31-1

    p_profileR = iface.new_socket(
        name="Tube Radius", in_out='INPUT', socket_type='NodeSocketFloat',
        description="Profile radius for tube"
    ); p_profileR.default_value, p_profileR.min_value, p_profileR.max_value = 0.03, 0.0005, 5.0

    p_curveRes = iface.new_socket(
        name="Curve Resolution", in_out='INPUT', socket_type='NodeSocketInt',
        description="Profile curve resolution"
    ); p_curveRes.default_value, p_curveRes.min_value, p_curveRes.max_value = 64, 3, 2048

    p_scaleMin = iface.new_socket(
        name="Scale Min", in_out='INPUT', socket_type='NodeSocketFloat',
        description="Lower bound of global pulse scale"
    ); p_scaleMin.default_value, p_scaleMin.min_value, p_scaleMin.max_value = 0.85, 0.0, 10.0

    p_scaleMax = iface.new_socket(
        name="Scale Max", in_out='INPUT', socket_type='NodeSocketFloat',
        description="Upper bound of global pulse scale"
    ); p_scaleMax.default_value, p_scaleMax.min_value, p_scaleMax.max_value = 1.15, 0.0, 10.0

    iface.new_socket(
        name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry',
        description="Output geometry"
    )

    # Group IO
    n_in  = nodes.new("NodeGroupInput");  n_in.location  = (-2200, 0)
    n_out = nodes.new("NodeGroupOutput"); n_out.location = (360,  520)

    # ---- Time driver ----
    time_val = nodes.new("ShaderNodeValue"); time_val.location = (-2200, -300); time_val.label = "Time (s)"
    drv = time_val.outputs[0].driver_add('default_value'); drv.driver.expression = "frame/24"
    t_mul  = nodes.new("ShaderNodeMath"); t_mul.location = (-2000, -300); t_mul.operation = 'MULTIPLY'
    links.new(time_val.outputs['Value'], t_mul.inputs[0])
    links.new(n_in.outputs['Time Speed'], t_mul.inputs[1])

    # ---- Arm placement ring ----
    circle = nodes.new("GeometryNodeCurvePrimitiveCircle"); circle.location = (-2100, 240)
    links.new(n_in.outputs['Curve Resolution'], circle.inputs['Resolution'])
    links.new(n_in.outputs['Ring Radius'],      circle.inputs['Radius'])

    resample_ring = nodes.new("GeometryNodeResampleCurve"); resample_ring.location = (-1900, 240); resample_ring.mode = 'COUNT'
    links.new(circle.outputs['Curve'], resample_ring.inputs['Curve'])
    links.new(n_in.outputs['Arms'],    resample_ring.inputs['Count'])

    ring_pts = nodes.new("GeometryNodeCurveToPoints"); ring_pts.location = (-1700, 240)
    links.new(resample_ring.outputs['Curve'], ring_pts.inputs['Curve'])

    # ---- Single spiral arm (build from a straight line + math) ----
    line = nodes.new("GeometryNodeCurvePrimitiveLine"); line.location = (-2100, -140)
    end_z = nodes.new("ShaderNodeCombineXYZ"); end_z.location = (-1920, -140)
    links.new(n_in.outputs['Spiral Height'], end_z.inputs['Z'])
    links.new(end_z.outputs['Vector'], line.inputs['End'])

    resample_arm = nodes.new("GeometryNodeResampleCurve"); resample_arm.location = (-1740, -140); resample_arm.mode = 'COUNT'
    links.new(line.outputs['Curve'], resample_arm.inputs['Curve'])
    links.new(n_in.outputs['Segments'], resample_arm.inputs['Count'])

    spline_param = nodes.new("GeometryNodeSplineParameter"); spline_param.location = (-1560, -160)

    # angle_base = 2π * turns * factor
    mul_turns = nodes.new("ShaderNodeMath"); mul_turns.location = (-1380, -220); mul_turns.operation = 'MULTIPLY'
    links.new(n_in.outputs['Spiral Turns'], mul_turns.inputs[0])
    links.new(spline_param.outputs['Factor'], mul_turns.inputs[1])

    angle = nodes.new("ShaderNodeMath"); angle.location = (-1200, -220); angle.operation = 'MULTIPLY'
    angle.inputs[1].default_value = 2 * math.pi
    links.new(mul_turns.outputs['Value'], angle.inputs[0])

    # radius_lerp = lerp(rStart, rEnd, factor) = rStart*(1 - f) + rEnd*f
    one_minus_f = nodes.new("ShaderNodeMath"); one_minus_f.location = (-1560, -20); one_minus_f.operation = 'SUBTRACT'
    one_minus_f.inputs[0].default_value = 1.0
    links.new(spline_param.outputs['Factor'], one_minus_f.inputs[1])

    rstart_term = nodes.new("ShaderNodeMath"); rstart_term.location = (-1380, -20); rstart_term.operation = 'MULTIPLY'
    links.new(n_in.outputs['Radius Start'], rstart_term.inputs[0])
    links.new(one_minus_f.outputs['Value'], rstart_term.inputs[1])

    rend_term = nodes.new("ShaderNodeMath"); rend_term.location = (-1380, 60); rend_term.operation = 'MULTIPLY'
    links.new(n_in.outputs['Radius End'], rend_term.inputs[0])
    links.new(spline_param.outputs['Factor'], rend_term.inputs[1])

    radius = nodes.new("ShaderNodeMath"); radius.location = (-1200, 20); radius.operation = 'ADD'
    links.new(rstart_term.outputs['Value'], radius.inputs[0])
    links.new(rend_term.outputs['Value'],  radius.inputs[1])

    # base XY from angle & radius; Z from line position
    sin_a = nodes.new("ShaderNodeMath"); sin_a.location = (-1020, -180); sin_a.operation = 'SINE'
    cos_a = nodes.new("ShaderNodeMath"); cos_a.location = (-1020, -80);  cos_a.operation = 'COSINE'
    links.new(angle.outputs['Value'], sin_a.inputs[0])
    links.new(angle.outputs['Value'], cos_a.inputs[0])

    x_mul = nodes.new("ShaderNodeMath"); x_mul.location = (-840, -80); x_mul.operation = 'MULTIPLY'
    y_mul = nodes.new("ShaderNodeMath"); y_mul.location = (-840, -180); y_mul.operation = 'MULTIPLY'
    links.new(cos_a.outputs['Value'], x_mul.inputs[0]); links.new(radius.outputs['Value'], x_mul.inputs[1])
    links.new(sin_a.outputs['Value'], y_mul.inputs[0]); links.new(radius.outputs['Value'], y_mul.inputs[1])

    pos_line = nodes.new("GeometryNodeInputPosition"); pos_line.location = (-1020, -320)

    base_pos = nodes.new("ShaderNodeCombineXYZ"); base_pos.location = (-660, -160)
    links.new(x_mul.outputs['Value'], base_pos.inputs['X'])
    links.new(y_mul.outputs['Value'], base_pos.inputs['Y'])
    links.new(pos_line.outputs['Position'], base_pos.inputs['Z'])  # use Z from the line

    # ---- Animated wobble + twist + time + per-arm phase ----
    m_twist  = nodes.new("ShaderNodeMath"); m_twist.location = (-1200, 220); m_twist.operation = 'MULTIPLY'
    links.new(n_in.outputs['Twist Over Length'], m_twist.inputs[0])
    links.new(spline_param.outputs['Factor'],     m_twist.inputs[1])

    m_wf    = nodes.new("ShaderNodeMath"); m_wf.location = (-1200, 300); m_wf.operation = 'MULTIPLY'
    links.new(n_in.outputs['Wobble Freq'], m_wf.inputs[0])
    links.new(spline_param.outputs['Factor'], m_wf.inputs[1])

    add_base = nodes.new("ShaderNodeMath"); add_base.location = (-1020, 260); add_base.operation = 'ADD'
    links.new(m_twist.outputs['Value'], add_base.inputs[0])
    links.new(m_wf.outputs['Value'],    add_base.inputs[1])

    add_time = nodes.new("ShaderNodeMath"); add_time.location = (-840, 260); add_time.operation = 'ADD'
    links.new(add_base.outputs['Value'], add_time.inputs[0])
    links.new(t_mul.outputs['Value'],    add_time.inputs[1])

    rand_phase = nodes.new("FunctionNodeRandomValue"); rand_phase.location = (-1200, 420); rand_phase.data_type = 'FLOAT'
    links.new(n_in.outputs['Seed'], rand_phase.inputs['ID'])

    phase_scale = nodes.new("ShaderNodeMath"); phase_scale.location = (-1020, 420); phase_scale.operation = 'MULTIPLY'
    links.new(rand_phase.outputs['Value'], phase_scale.inputs[0])
    links.new(n_in.outputs['Per-Arm Phase'], phase_scale.inputs[1])

    add_phase = nodes.new("ShaderNodeMath"); add_phase.location = (-660, 260); add_phase.operation = 'ADD'
    links.new(add_time.outputs['Value'], add_phase.inputs[0])
    links.new(phase_scale.outputs['Value'], add_phase.inputs[1])

    ang_sin = nodes.new("ShaderNodeMath"); ang_sin.location = (-480, 200); ang_sin.operation = 'SINE'
    ang_cos = nodes.new("ShaderNodeMath"); ang_cos.location = (-480, 320); ang_cos.operation = 'COSINE'
    links.new(add_phase.outputs['Value'], ang_sin.inputs[0])
    links.new(add_phase.outputs['Value'], ang_cos.inputs[0])

    wob_x = nodes.new("ShaderNodeMath"); wob_x.location = (-300, 320); wob_x.operation = 'MULTIPLY'
    wob_y = nodes.new("ShaderNodeMath"); wob_y.location = (-300, 200); wob_y.operation = 'MULTIPLY'
    links.new(ang_cos.outputs['Value'], wob_x.inputs[0]); links.new(n_in.outputs['Wobble Amp'], wob_x.inputs[1])
    links.new(ang_sin.outputs['Value'], wob_y.inputs[0]); links.new(n_in.outputs['Wobble Amp'], wob_y.inputs[1])

    wob_vec = nodes.new("ShaderNodeCombineXYZ"); wob_vec.location = (-120, 260)
    links.new(wob_x.outputs['Value'], wob_vec.inputs['X'])
    links.new(wob_y.outputs['Value'], wob_vec.inputs['Y'])

    half = nodes.new("ShaderNodeMath"); half.location = (-300, 120); half.operation = 'MULTIPLY'; half.inputs[1].default_value = 0.5
    links.new(add_phase.outputs['Value'], half.inputs[0])
    wob_z = nodes.new("ShaderNodeMath"); wob_z.location = (-120, 120); wob_z.operation = 'SINE'
    links.new(half.outputs['Value'], wob_z.inputs[0])
    wob_z_scale = nodes.new("ShaderNodeMath"); wob_z_scale.location = (60, 120); wob_z_scale.operation = 'MULTIPLY'; wob_z_scale.inputs[1].default_value = 0.25
    links.new(wob_z.outputs['Value'], wob_z_scale.inputs[0])
    links.new(wob_z_scale.outputs['Value'], wob_vec.inputs['Z'])

    # Per-point gentle noise along the arm
    rnd_vec = nodes.new("FunctionNodeRandomValue"); rnd_vec.location = (-480, 520); rnd_vec.data_type = 'FLOAT_VECTOR'
    links.new(n_in.outputs['Seed'], rnd_vec.inputs['ID'])
    sep_rnd = nodes.new("ShaderNodeSeparateXYZ"); sep_rnd.location = (-300, 520)
    links.new(rnd_vec.outputs['Value'], sep_rnd.inputs['Vector'])

    len_scale = nodes.new("ShaderNodeMath"); len_scale.location = (-120, 520); len_scale.operation = 'MULTIPLY'
    links.new(n_in.outputs['Noise Scale'], len_scale.inputs[0])
    links.new(spline_param.outputs['Factor'], len_scale.inputs[1])

    sin_len = nodes.new("ShaderNodeMath"); sin_len.location = (60, 520); sin_len.operation = 'SINE'
    links.new(len_scale.outputs['Value'], sin_len.inputs[0])

    noise_amp = nodes.new("ShaderNodeMath"); noise_amp.location = (240, 520); noise_amp.operation = 'MULTIPLY'
    links.new(n_in.outputs['Noise Magnitude'], noise_amp.inputs[0])
    links.new(sep_rnd.outputs['X'],            noise_amp.inputs[1])

    noise_vec = nodes.new("ShaderNodeCombineXYZ"); noise_vec.location = (420, 520)
    mul_noise = nodes.new("ShaderNodeMath"); mul_noise.location = (420, 600); mul_noise.operation = 'MULTIPLY'
    links.new(sin_len.outputs['Value'], mul_noise.inputs[0])
    links.new(noise_amp.outputs['Value'], mul_noise.inputs[1])
    links.new(mul_noise.outputs['Value'], noise_vec.inputs['X'])
    links.new(mul_noise.outputs['Value'], noise_vec.inputs['Y'])

    # Apply base spiral position + wobble + noise
    add_offsets = nodes.new("ShaderNodeVectorMath"); add_offsets.location = (60, -160); add_offsets.operation = 'ADD'
    links.new(base_pos.outputs['Vector'], add_offsets.inputs[0])

    add_wob_noise = nodes.new("ShaderNodeVectorMath"); add_wob_noise.location = (240, -160); add_wob_noise.operation = 'ADD'
    links.new(wob_vec.outputs['Vector'], add_wob_noise.inputs[0])
    links.new(noise_vec.outputs['Vector'], add_wob_noise.inputs[1])

    sum_all = nodes.new("ShaderNodeVectorMath"); sum_all.location = (420, -160); sum_all.operation = 'ADD'
    links.new(add_offsets.outputs['Vector'], sum_all.inputs[0])
    links.new(add_wob_noise.outputs['Vector'], sum_all.inputs[1])

    set_pos = nodes.new("GeometryNodeSetPosition"); set_pos.location = (600, -140)
    links.new(resample_arm.outputs['Curve'], set_pos.inputs['Geometry'])
    links.new(sum_all.outputs['Vector'], set_pos.inputs['Position'])

    # ---- Arm tilt using Transform (X rotation from degrees) ----
    tilt_rad = nodes.new("ShaderNodeMath"); tilt_rad.location = (780, -300); tilt_rad.operation = 'MULTIPLY'
    tilt_rad.inputs[1].default_value = math.pi / 180.0
    links.new(n_in.outputs['Arm Tilt (deg)'], tilt_rad.inputs[0])

    rot_vec = nodes.new("ShaderNodeCombineXYZ"); rot_vec.location = (960, -300)
    links.new(tilt_rad.outputs['Value'], rot_vec.inputs['X'])

    transform_arm = nodes.new("GeometryNodeTransform"); transform_arm.location = (960, -140)
    links.new(set_pos.outputs['Geometry'], transform_arm.inputs['Geometry'])
    links.new(rot_vec.outputs['Vector'],   transform_arm.inputs['Rotation'])

    # ---- Tube ----
    prof = nodes.new("GeometryNodeCurvePrimitiveCircle"); prof.location = (780, 100)
    links.new(n_in.outputs['Curve Resolution'], prof.inputs['Resolution'])
    links.new(n_in.outputs['Tube Radius'],      prof.inputs['Radius'])

    curve_to_mesh = nodes.new("GeometryNodeCurveToMesh"); curve_to_mesh.location = (960, 100)
    links.new(transform_arm.outputs['Geometry'], curve_to_mesh.inputs['Curve'])
    links.new(prof.outputs['Curve'],            curve_to_mesh.inputs['Profile Curve'])

    # ---- Instance on ring + spin ----
    inst_on_pts = nodes.new("GeometryNodeInstanceOnPoints"); inst_on_pts.location = (-1500, 540)
    links.new(ring_pts.outputs['Points'], inst_on_pts.inputs['Points'])
    links.new(curve_to_mesh.outputs['Mesh'], inst_on_pts.inputs['Instance'])

    spin = nodes.new("ShaderNodeMath"); spin.location = (-1320, 540); spin.operation = 'MULTIPLY'
    links.new(t_mul.outputs['Value'], spin.inputs[0])
    links.new(n_in.outputs['Orbit Spin Speed'], spin.inputs[1])

    spin_vec = nodes.new("ShaderNodeCombineXYZ"); spin_vec.location = (-1140, 540)
    links.new(spin.outputs['Value'], spin_vec.inputs['Z'])

    xform = nodes.new("GeometryNodeTransform"); xform.location = (-960, 540)
    links.new(inst_on_pts.outputs['Instances'], xform.inputs['Geometry'])
    links.new(spin_vec.outputs['Vector'],       xform.inputs['Rotation'])

    realize = nodes.new("GeometryNodeRealizeInstances"); realize.location = (-780, 540)
    links.new(xform.outputs['Geometry'], realize.inputs['Geometry'])

    # ---- Global pulse ----
    s_sine = nodes.new("ShaderNodeMath"); s_sine.location = (-600, 540); s_sine.operation = 'SINE'
    links.new(t_mul.outputs['Value'], s_sine.inputs[0])

    s_map = nodes.new("ShaderNodeMapRange"); s_map.location = (-420, 540)
    s_map.inputs['From Min'].default_value = -1.0
    s_map.inputs['From Max'].default_value =  1.0
    links.new(s_sine.outputs['Value'], s_map.inputs['Value'])
    links.new(n_in.outputs['Scale Min'], s_map.inputs['To Min'])
    links.new(n_in.outputs['Scale Max'], s_map.inputs['To Max'])

    s_vec = nodes.new("ShaderNodeCombineXYZ"); s_vec.location = (-240, 540)
    links.new(s_map.outputs['Result'], s_vec.inputs['X'])
    links.new(s_map.outputs['Result'], s_vec.inputs['Y'])
    links.new(s_map.outputs['Result'], s_vec.inputs['Z'])

    transform_final = nodes.new("GeometryNodeTransform"); transform_final.location = (-60, 540)
    links.new(realize.outputs['Geometry'], transform_final.inputs['Geometry'])
    links.new(s_vec.outputs['Vector'],     transform_final.inputs['Scale'])

    links.new(transform_final.outputs['Geometry'], n_out.inputs['Geometry'])

# ---------------------- Attach to an object --------------------------------
def setup_and_run():
    obj = ensure_active_object()
    mod = next((m for m in obj.modifiers if m.type == 'NODES'), None)
    if mod is None:
        mod = obj.modifiers.new(name="Cyclone Sunburst", type='NODES')
    ng = new_gn_group()
    build_cyclone_sunburst(ng)
    mod.node_group = ng
    print(f"Assigned node group '{ng.name}' to '{obj.name}'")

# Execute
setup_and_run()
