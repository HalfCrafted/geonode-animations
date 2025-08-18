# discover_curve_attributes.py
import bpy
node_tree = bpy.data.node_groups.get("BouncyBounce")
if node_tree:
    float_curve_node = node_tree.nodes.get("Float Curve")
    if float_curve_node:
        point = float_curve_node.mapping.curves[0].points[0]
        print("--- Attributes for CurveMapPoint ---")
        print(dir(point))
        print("------------------------------------")
