### ✲ PRE-PROMPT GUARANTEE (PASTE FIRST IN EVERY SCRIPT)

> **Before generating or writing any GN script, include this header block.** It enforces the `description=` keyword on sockets, prevents duplicate/buggy drivers, gates unsupported nodes, and standardizes group/modifier setup. All later code must use these helpers.



**AI Instruction Guide for Procedural Geometry Nodes Animations in Blender 4.4**

This guide consolidates best practices for creating modular, animated geometry node setups in Blender using Python and ensures scripts avoid common AI-generated errors.



\# === Blender GN Safety Header (required) =====================================

import bpy



def socket(iface, \*, name, in\_out, socket\_type, desc, default=None, min=None, max=None):

&#x20;   s = iface.new\_socket(name=name, in\_out=in\_out, socket\_type=socket\_type, description=desc)

&#x20;   if default is not None and hasattr(s, 'default\_value'):

&#x20;       try: s.default\_value = default

&#x20;       except TypeError: pass

&#x20;   if min is not None and hasattr(s, 'min\_value'):

&#x20;       try: s.min\_value = min

&#x20;       except TypeError: pass

&#x20;   if max is not None and hasattr(s, 'max\_value'):

&#x20;       try: s.max\_value = max

&#x20;       except TypeError: pass

&#x20;   return s



\# Backwards-compat alias so any existing \`new\_socket(...)\` calls are safe

new\_socket = socket



\# Value node time driver (removes old drivers to avoid duplicates)

def safe\_time\_driver(value\_node, expr="frame/24"):

&#x20;   try:

&#x20;       value\_node.outputs[0].driver\_remove('default\_value')

&#x20;   except Exception:

&#x20;       pass

&#x20;   d = value\_node.outputs[0].driver\_add('default\_value')

&#x20;   d.driver.expression = expr

&#x20;   return d



\# Node creation with support check

def node\_supported(bl\_idname: str) -> bool:

&#x20;   return hasattr(bpy.types, bl\_idname)



def new\_node(nodes, bl\_idname, \*, location=(0,0)):

&#x20;   if not node\_supported(bl\_idname):

&#x20;       raise RuntimeError(f"Unsupported node type: {bl\_idname}. Provide a math-based fallback.")

&#x20;   n = nodes.new(bl\_idname); n.location = location; return n



\# Group + modifier utilities

def new\_gn\_group(name="GN Group"):

&#x20;   ng = bpy.data.node\_groups.new(name, 'GeometryNodeTree')

&#x20;   for n in list(ng.nodes): ng.nodes.remove(n)

&#x20;   return ng



def attach\_group\_modifier(obj, ng, name="GN Modifier"):

&#x20;   mod = next((m for m in obj.modifiers if m.type == 'NODES'), None)

&#x20;   if mod is None: mod = obj.modifiers.new(name=name, type='NODES')

&#x20;   mod.node\_group = ng; return mod



\# Scene object guarantee

if bpy.context.active\_object is None:

&#x20;   bpy.ops.mesh.primitive\_plane\_add()

OBJ = bpy.context.active\_object







**Generation rule:** any prompt/template should state: *“Start by pasting the Safety Header verbatim, then build the interface using **``** (or **``**), never direct **``** calls.”*

If you want, I can try another targeted insert at a specific line (“place it after section X”), or just replace the first “OVERALL STRUCTURE” divider with this block + the divider.



---

### ✲ KEY ERROR PREVENTION

**Socket Creation:** Always use a helper that forces `description=` as a keyword argument:

```python
def socket(iface, *, name, in_out, socket_type, desc, default=None, min=None, max=None):
    s = iface.new_socket(name=name, in_out=in_out, socket_type=socket_type, description=desc)
    if default is not None and hasattr(s, 'default_value'):
        try: s.default_value = default
        except TypeError: pass
    if min is not None and hasattr(s, 'min_value'):
        try: s.min_value = min
        except TypeError: pass
    if max is not None and hasattr(s, 'max_value'):
        try: s.max_value = max
        except TypeError: pass
    return s
```

Use this in every script, replacing direct `iface.new_socket()` calls.

**Unsupported Nodes:**

```python
def node_supported(bl_idname):
    import bpy
    return hasattr(bpy.types, bl_idname)
```

Before creating a node, check `if not node_supported(type):` and provide a math-based fallback.

**Time Driver:**

```python
def safe_time_driver(val_node, expr="frame/24"):
    val_node.outputs[0].driver_remove('default_value')
    d = val_node.outputs[0].driver_add('default_value')
    d.driver.expression = expr
```

Always drive animation time from a `ShaderNodeValue`.

---

### ✲ SCRIPT STRUCTURE

1. **Ensure Active Object:** Create a default plane if none exists.
2. **Create Node Group:** `bpy.data.node_groups.new(name, 'GeometryNodeTree')` and clear nodes.
3. **Interface:** Declare sockets via `socket()` helper.
4. **Node Graph:** Create nodes with `nodes.new()` or `new_node()` wrapper.
5. **Outputs:** Limit to a `Geometry` output.
6. **Attach Modifier:** Apply to the object.

---

### ✲ CHECKLIST

- All sockets created with `socket()` helper.
- Node creation gated with `node_supported()`.
- Time driven via `safe_time_driver()`.
- Default/min/max values set.
- No unlinked required inputs.
- Deprecated nodes replaced with procedural math setups.
- Build and test in phases.

---

Following these patterns ensures scripts run without `TypeError` for missing keyword arguments, avoid undefined node types, and support robust customization.

