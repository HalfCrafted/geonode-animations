GEMINI.md - Custom Instructions for Gemini: Blender 4.4 Geometry Nodes Scripting



These are custom instructions to help Gemini generate accurate Python scripts for Blender 4.4's Geometry Nodes. Following this guide will prevent common errors related to API changes and version-specific node names.



Core Prompting Principles



To get the best results, structure your prompt with the following five key sections:



1\. State the Exact Blender Version



This is the most critical piece of information, as the Python API changes between versions.



Example:



&nbsp;   "I am using Blender 4.4."



2\. Clearly State the Goal and Process



Describe the final visual effect, including any animation. If you have a specific process in mind, describe it step-by-step, as this translates directly into code.



Example:



&nbsp;   "I want to create a procedural chain link fence. The process should be:



&nbsp;       Create a grid of points.



&nbsp;       Instance a custom chain-link object at each point.



&nbsp;       Use a noise texture to randomly remove some instances."



3\. Provide a Ground-Truth Syntax Snippet



This is the most effective way to prevent API syntax errors. Provide a short, working example of how your Blender version creates a modifier input. This acts as a definitive reference.



Example:



&nbsp;   "For reference, here is the correct syntax for adding a modifier input in my version:

&nbsp;   Python



&nbsp;   node\_tree.interface.new\_socket(name='MyInput', in\_out='INPUT', socket\_type='NodeSocketFloat')

&nbsp;   ```"



4\. Specify Key Nodes, Techniques, and Settings



List specific nodes you want to use by their name from the Add menu. This prevents ambiguity and errors from incorrect internal names. Also, specify robust techniques.



Example:



&nbsp;   "Please use the 'Grid' node for the points. For animation timing, use a 



&nbsp;   driver on a Value node instead of the 'Scene Time' node."



5\. Describe Exposed Parameters with Ranges



Clearly list all the parameters you want to control from the modifier panel. For numerical values, include the desired default value, and a minimum/maximum range.



Example:



&nbsp;   "Please expose the following parameters on the modifier:



&nbsp;       Fence Width: Float, Default=10.0, Min=1.0, Max=100.0.



&nbsp;       Fence Height: Float, Default=2.0, Min=0.5, Max=5.0.



&nbsp;       Post Spacing: Float, Default=2.5, Min=1.0, Max=5.0."



Reference Data for Blender 4.4 (Derived from Manual)



This section contains a list of common node names and types derived from the provided Blender 4.5 LTS manual, which should be accurate for version 4.4.



Common Node bl\_idnames



Curve Primitives 



&nbsp;   Curve Circle: 



&nbsp;   GeometryNodeCurvePrimitiveCircle 



Curve Line: 



GeometryNodeCurvePrimitiveLine 



Spiral: 



GeometryNodeCurvePrimitiveSpiral 



Star: 



GeometryNodeCurvePrimitiveStar 



Mesh Primitives 



&nbsp;   Cube: 



&nbsp;   GeometryNodeMeshCube 



Grid: 



GeometryNodeMeshGrid 



Icosphere: 



GeometryNodeMeshIcoSphere 



UV Sphere: 



GeometryNodeMeshUVSphere 



Input / Read Nodes



&nbsp;   Position: 



&nbsp;   GeometryNodeInputPosition 



Normal: 



GeometryNodeInputNormal 



Curve Tangent: GeometryNodeInputTangent



Spline Parameter: 



GeometryNodeSplineParameter 



Scene Time: 



GeometryNodeSceneTime  (



&nbsp;   Note: Using a driver on a Value node is often more reliable.)



Operation Nodes



&nbsp;   Set Position: 



&nbsp;   GeometryNodeSetPosition 



Transform Geometry: 



GeometryNodeTransform 



Instance on Points: 



GeometryNodeInstanceOnPoints 



Curve to Mesh: 



GeometryNodeCurveToMesh 



Vector Rotate: 



GeometryNodeVectorRotate 



Utility Nodes



&nbsp;   Math: 



&nbsp;   ShaderNodeMath 



Vector Math: 



ShaderNodeVectorMath 



Map Range: 



ShaderNodeMapRange 



Combine XYZ: 



ShaderNodeCombineXYZ 



Value: 



ShaderNodeValue 



Common Socket Types (socket\_type)



&nbsp;   NodeSocketFloat (for single numbers)



&nbsp;   NodeSocketInt (for integers)



&nbsp;   NodeSocketVector (for vectors)



&nbsp;   NodeSocketGeometry (for geometry data)



&nbsp;   NodeSocketBool (for boolean true/false)



&nbsp;   NodeSocketRotation (for rotation data)

