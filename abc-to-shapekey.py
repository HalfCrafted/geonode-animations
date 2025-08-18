#
#    Copyright (c) 2025 Google LLC.
#    All rights reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.
#
"""
Converts MeshSequenceCache modifiers to individual shape keys AND
creates keyframes to animate their influence over time.
"""

import bpy

def convert_and_animate_mesh_cache():
    """
    Converts MeshSequenceCache modifiers on selected objects into shape keys
    and creates the necessary keyframes to replicate the original animation.
    """
    # Get only the selected objects that are meshes
    selected_objects = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']

    if not selected_objects:
        print("⚠️ No mesh objects selected. Please select your target objects.")
        return {'CANCELLED'}

    # Get the scene's frame range and store the original frame
    scene = bpy.context.scene
    frame_start = scene.frame_start
    frame_end = scene.frame_end
    original_frame = scene.frame_current

    print(f"🎬 Processing frames {frame_start} to {frame_end}...")

    # Process each selected object
    for obj in selected_objects:
        bpy.context.view_layer.objects.active = obj
        print(f"\nProcessing object: '{obj.name}'")

        # Find the first MeshSequenceCache modifier
        cache_modifier = next((mod for mod in obj.modifiers if mod.type == 'MESH_SEQUENCE_CACHE'), None)

        if not cache_modifier:
            print(f"  - No MeshSequenceCache modifier found on '{obj.name}'. Skipping.")
            continue

        print(f"  - Found modifier: '{cache_modifier.name}'")

        # --- Part 1: Create Shape Keys ---
        if not obj.data.shape_keys:
            obj.shape_key_add(name='Basis')
            print("  - Created 'Basis' shape key.")

        depsgraph = bpy.context.evaluated_depsgraph_get()
        new_keys = []

        for frame in range(frame_start, frame_end + 1):
            print(f"  - Generating shape key for frame {frame}...")
            scene.frame_set(frame)
            obj_eval = obj.evaluated_get(depsgraph)
            
            key_name = f"Frame_{frame}"
            new_key = obj.shape_key_add(name=key_name, from_mix=False)
            new_keys.append(new_key) # Store the new key for later

            if len(new_key.data) == len(obj_eval.data.vertices):
                for i, v_eval in enumerate(obj_eval.data.vertices):
                    new_key.data[i].co = v_eval.co
            else:
                print(f"  - ❌ ERROR: Vertex count mismatch on frame {frame}. Aborting for this object.")
                obj.shape_key_remove(new_key)
                break
        
        # --- Part 2: Animate the Shape Keys ---
        print("\n  - Animating newly created shape keys...")
        skeys = obj.data.shape_keys

        # Ensure there is animation data to add keyframes to
        if not skeys.animation_data:
            skeys.animation_data_create()

        # Keyframe each shape key to be 1.0 on its frame and 0.0 otherwise
        for key in new_keys:
            frame_num = int(key.name.split('_')[-1])
            
            # Set value to 0.0 on the frame before
            key.value = 0.0
            key.keyframe_insert(data_path='value', frame=frame_num - 1)
            
            # Set value to 1.0 on the correct frame
            key.value = 1.0
            key.keyframe_insert(data_path='value', frame=frame_num)

            # Set value to 0.0 on the frame after
            key.value = 0.0
            key.keyframe_insert(data_path='value', frame=frame_num + 1)
        
        # Set interpolation to CONSTANT to prevent blending between frames
        if skeys.animation_data.action:
            for fcurve in skeys.animation_data.action.fcurves:
                for kf_point in fcurve.keyframe_points:
                    kf_point.interpolation = 'CONSTANT'
        
        print("  - Animation keyframes created successfully.")

        # --- Part 3: Cleanup ---
        print(f"  - Removing modifier '{cache_modifier.name}'...")
        obj.modifiers.remove(cache_modifier)

        print(f"  - ✅ Finished with '{obj.name}'.")

    # Restore the original frame in the timeline
    scene.frame_set(original_frame)
    print("\n✨ Conversion and animation complete!")
    
    return {'FINISHED'}

# This allows the script to be run directly from Blender's Text Editor
if __name__ == "__main__":
    convert_and_animate_mesh_cache()