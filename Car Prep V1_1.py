"""
==============================================================
  CAR PREP TOOL  v1.1
  by Alfredo Mendez

  A Blender addon to streamline vehicle asset preparation
  for game engines. Handles pivot correction, orientation,
  collection organization and FBX export.

  Public Release v1.1
  Compatible with Blender 4.3 and above
==============================================================
  INSTALLATION:
  - Edit > Preferences > Add-ons > Install... -> enable addon
  -- OR --
  - Scripting workspace -> paste -> Run Script
  Panel available in N-bar -> "Car Prep" tab
==============================================================
"""

from __future__ import annotations
import bpy
import bmesh
import math
import os
from mathutils import Vector, Matrix


bl_info = {
    "name": "Car Prep Tool",
    "author": "Alfredo Mendez",
    "version": (1, 1),
    "blender": (4, 3, 0),
    "location": "View3D > Sidebar > Car Prep",
    "description": "Vehicle asset preparation tool: pivot, orientation, collections and FBX export for game engines.",
    "doc_url": "",
    "category": "Object",
}

CAR_COLLECTIONS = [
    ("Body",               "Body",               "Car body / chassis"),
    ("Glass",              "Glass",              "Windows and windshields (optional)"),
    ("Interior",           "Interior",           "Interior parts"),
    ("Front_Left_Wheel",   "Front Left Wheel",   "Front left wheel"),
    ("Front_Right_Wheel",  "Front Right Wheel",  "Front right wheel"),
    ("Rear_Left_Wheel",    "Rear Left Wheel",    "Rear left wheel"),
    ("Rear_Right_Wheel",   "Rear Right Wheel",   "Rear right wheel"),
    ("Front_Left_Caliper",  "Front Left Caliper",  "Front left brake caliper"),
    ("Front_Right_Caliper", "Front Right Caliper", "Front right brake caliper"),
    ("Rear_Left_Caliper",   "Rear Left Caliper",   "Rear left brake caliper"),
    ("Rear_Right_Caliper",  "Rear Right Caliper",  "Rear right brake caliper"),
    ("NO_Export",          "NO_Export",          "Hidden from export"),
]

FRONT_ITEMS = [
    ("Y",  "+Y -> +X  (default)", "Front faces +Y, will be rotated to +X"),
    ("-Y", "-Y -> +X",            "Front faces -Y, will be rotated to +X"),
    ("-X", "-X -> +X",            "Front faces -X, will be rotated to +X"),
    ("X",  "+X  (already set)",   "Front already faces +X, no rotation needed"),
]


# ──────────────────────────────────────────────────────────────
#  UTILITIES
# ──────────────────────────────────────────────────────────────

def get_hierarchy(obj, collected=None):
    if collected is None:
        collected = []
    collected.append(obj)
    for child in obj.children:
        get_hierarchy(child, collected)
    return collected


def get_root_and_meshes(context):
    selected = context.selected_objects
    if not selected:
        return [], []
    sel_set = set(selected)
    roots = set()
    for obj in selected:
        root = obj
        while root.parent and root.parent in sel_set:
            root = root.parent
        roots.add(root)
    all_objects = []
    for root in roots:
        get_hierarchy(root, all_objects)
    seen, unique = set(), []
    for o in all_objects:
        if o.name not in seen:
            seen.add(o.name)
            unique.append(o)
    meshes = [o for o in unique if o.type == 'MESH']
    return unique, meshes


def global_bounding_box(mesh_objects):
    coords = []
    for obj in mesh_objects:
        mat = obj.matrix_world
        for corner in obj.bound_box:
            coords.append(mat @ Vector(corner))
    if not coords:
        return Vector((0, 0, 0)), Vector((0, 0, 0))
    return (
        Vector((min(c.x for c in coords), min(c.y for c in coords), min(c.z for c in coords))),
        Vector((max(c.x for c in coords), max(c.y for c in coords), max(c.z for c in coords))),
    )


def angle_for_x_forward(original_front):
    return {"Y": -math.pi/2, "-Y": math.pi/2, "-X": math.pi, "X": 0.0}[original_front]


def find_layer_collection(layer_col, name):
    if layer_col.name == name:
        return layer_col
    for child in layer_col.children:
        result = find_layer_collection(child, name)
        if result:
            return result
    return None


def get_export_path(blend_path, cname):
    blend_name = os.path.splitext(os.path.basename(blend_path))[0]
    export_dir = os.path.join(os.path.dirname(blend_path), "export")
    os.makedirs(export_dir, exist_ok=True)
    return os.path.join(export_dir, f"{blend_name}_{cname}.fbx")


def fbx_export_params(filepath):
    return dict(
        filepath             = filepath,
        use_selection        = True,
        object_types         = {'MESH'},
        use_mesh_modifiers   = True,
        global_scale         = 1.0,
        apply_scale_options  = 'FBX_SCALE_NONE',
        axis_forward         = 'Y',
        axis_up              = 'Z',
        apply_unit_scale     = False,
        bake_space_transform = False,
        use_space_transform  = False,
        add_leaf_bones       = False,
        path_mode            = 'AUTO',
    )


def do_export(context, cname):
    blend_path = bpy.data.filepath
    if not blend_path:
        return False, "Save the .blend file first."
    col = bpy.data.collections.get(cname)
    if col is None or not col.objects:
        return False, f"'{cname}' is empty or does not exist."
    meshes = [o for o in col.objects if o.type == 'MESH']
    if not meshes:
        return False, f"'{cname}' has no mesh objects."
    bpy.ops.object.select_all(action='DESELECT')
    for obj in meshes:
        obj.hide_set(False)
        obj.select_set(True)
    context.view_layer.objects.active = meshes[0]
    fbx_path = get_export_path(blend_path, cname)
    bpy.ops.export_scene.fbx(**fbx_export_params(fbx_path))
    bpy.ops.object.select_all(action='DESELECT')
    return True, os.path.basename(fbx_path)


# ──────────────────────────────────────────────────────────────
#  PROPERTIES
# ──────────────────────────────────────────────────────────────

class CarPrepProperties(bpy.types.PropertyGroup):
    original_front: bpy.props.EnumProperty(
        name="Original Front",
        description="Which axis the vehicle front faces in the imported file",
        items=FRONT_ITEMS,
        default="Y",
    )


# ──────────────────────────────────────────────────────────────
#  ADDON PREFERENCES
# ──────────────────────────────────────────────────────────────

class CarPrepAddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__ if __name__ != "__main__" else "car_prep_tool"

    def draw(self, context):
        layout = self.layout
        layout.label(text="Car Prep Tool by Alfredo Mendez", icon='AUTO')


# ──────────────────────────────────────────────────────────────
#  OPERATOR – Check & Fix Scale
# ──────────────────────────────────────────────────────────────

class OBJECT_OT_fix_car_scale(bpy.types.Operator):
    bl_idname  = "object.fix_car_scale"
    bl_label   = "Set Proper Scale"
    bl_description = (
        "Detects scale order of magnitude and normalizes geometry "
        "so the longest dimension sits in the 1-9 range (single digit before decimal). "
        "Proportions are fully preserved."
    )
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        _, meshes = get_root_and_meshes(context)

        if not meshes:
            self.report({'WARNING'}, "No mesh objects selected.")
            return {'CANCELLED'}

        min_v, max_v = global_bounding_box(meshes)
        dims    = [max_v.x - min_v.x, max_v.y - min_v.y, max_v.z - min_v.z]
        longest = max(dims)

        if longest <= 0:
            self.report({'WARNING'}, "Could not determine bounding box size.")
            return {'CANCELLED'}

        # Calculate the power-of-10 factor needed to bring longest into [1, 10)
        magnitude = math.floor(math.log10(longest))

        if magnitude == 0:
            # Already in [1, 10) — single digit before decimal, nothing to do
            self.report({'INFO'}, f"Scale is correct — longest dimension: {longest:.4f}m")
            return {'FINISHED'}

        # Factor to shift decimal: e.g. 450m → /100 → 4.5, 0.045 → *100 → 4.5
        factor = 10 ** (-magnitude)

        scale_mat = Matrix.Scale(factor, 4)
        for obj in meshes:
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            bmesh.ops.transform(bm, matrix=scale_mat, verts=bm.verts)
            bm.to_mesh(obj.data)
            bm.free()
            obj.data.update()

        bpy.ops.object.select_all(action='DESELECT')
        for obj in meshes:
            obj.select_set(True)
        context.view_layer.objects.active = meshes[0]
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

        new_longest = longest * factor
        self.report({'INFO'},
            f"Scale fixed — was {longest:.4f}m → now {new_longest:.4f}m  "
            f"(factor: {'x' if factor > 1 else '÷'}{abs(int(round(1/factor if factor < 1 else factor)))})"
        )
        return {'FINISHED'}




class OBJECT_OT_fix_car_pivot(bpy.types.Operator):
    bl_idname  = "object.fix_car_pivot"
    bl_label   = "Fix Car Pivot"
    bl_description = (
        "Clear hierarchy, apply transforms, "
        "center XY, floor to Z=0, orient front to +X"
    )
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.car_prep_props
        all_objs, meshes = get_root_and_meshes(context)

        if not meshes:
            self.report({'WARNING'}, "No mesh objects selected.")
            return {'CANCELLED'}

        # 1. Clear parent hierarchy
        bpy.ops.object.select_all(action='DESELECT')
        for obj in all_objs:
            obj.select_set(True)
        context.view_layer.objects.active = all_objs[0]
        bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')

        meshes = [o for o in context.scene.objects if o.type == 'MESH' and o.select_get()]

        # 2. Apply all transforms
        bpy.ops.object.select_all(action='DESELECT')
        for obj in meshes:
            obj.select_set(True)
        context.view_layer.objects.active = meshes[0]
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

        # 3. Center XY, floor to Z=0
        min_v, max_v = global_bounding_box(meshes)
        offset = Vector((-(min_v.x+max_v.x)/2, -(min_v.y+max_v.y)/2, -min_v.z))
        for obj in meshes:
            obj.location += offset
        bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)

        # 4. Rotate geometry directly via bmesh (idempotent)
        angle = angle_for_x_forward(props.original_front)
        if abs(angle) > 1e-6:
            rot_mat = Matrix.Rotation(angle, 4, 'Z')
            for obj in meshes:
                obj.rotation_euler.zero()
                bm = bmesh.new()
                bm.from_mesh(obj.data)
                bmesh.ops.transform(bm, matrix=rot_mat, verts=bm.verts)
                bm.to_mesh(obj.data)
                bm.free()
                obj.data.update()

        # 5. Re-check floor after rotation
        min_v2, _ = global_bounding_box(meshes)
        if abs(min_v2.z) > 1e-5:
            for obj in meshes:
                obj.location.z -= min_v2.z
            bpy.ops.object.select_all(action='DESELECT')
            for obj in meshes:
                obj.select_set(True)
            context.view_layer.objects.active = meshes[0]
            bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)

        # 6. Remove leftover empties / armatures
        non_mesh = [o for o in all_objs if o.type not in ('MESH', 'CAMERA', 'LIGHT')]
        if non_mesh:
            bpy.ops.object.select_all(action='DESELECT')
            for obj in non_mesh:
                obj.select_set(True)
            bpy.ops.object.delete()

        # Restore selection
        bpy.ops.object.select_all(action='DESELECT')
        for obj in meshes:
            try: obj.select_set(True)
            except ReferenceError: pass
        if meshes:
            context.view_layer.objects.active = meshes[0]

        self.report({'INFO'}, f"Done | {len(meshes)} meshes | Front: +X | Floor: Z=0")
        return {'FINISHED'}


# ──────────────────────────────────────────────────────────────
#  OPERATOR – Toggle Collection Visibility
# ──────────────────────────────────────────────────────────────

class OBJECT_OT_toggle_car_collection(bpy.types.Operator):
    bl_idname  = "object.toggle_car_collection"
    bl_label   = "Toggle Visibility"
    bl_options = {'REGISTER', 'UNDO'}

    collection_name: bpy.props.StringProperty()

    def execute(self, context):
        col = bpy.data.collections.get(self.collection_name)
        if col is None:
            self.report({'WARNING'}, f"Collection '{self.collection_name}' does not exist yet.")
            return {'CANCELLED'}
        lc = find_layer_collection(context.view_layer.layer_collection, col.name)
        if lc:
            lc.hide_viewport = not lc.hide_viewport
        return {'FINISHED'}


# ──────────────────────────────────────────────────────────────
#  OPERATOR – Assign to Collection
# ──────────────────────────────────────────────────────────────

class OBJECT_OT_assign_car_collection(bpy.types.Operator):
    bl_idname  = "object.assign_car_collection"
    bl_label   = "Assign to Collection"
    bl_options = {'REGISTER', 'UNDO'}

    collection_name: bpy.props.StringProperty()

    def execute(self, context):
        meshes = [o for o in context.selected_objects if o.type == 'MESH']
        if not meshes:
            self.report({'WARNING'}, "Select at least one mesh object.")
            return {'CANCELLED'}

        col = bpy.data.collections.get(self.collection_name)
        if col is None:
            col = bpy.data.collections.new(self.collection_name)
            context.scene.collection.children.link(col)
            lc = find_layer_collection(context.view_layer.layer_collection, col.name)
            if lc:
                lc.hide_viewport = True

        if self.collection_name == "NO_Export":
            col.hide_render = True

        for obj in meshes:
            for c in list(obj.users_collection):
                c.objects.unlink(obj)
            col.objects.link(obj)

        self.report({'INFO'}, f"{len(meshes)} object(s) -> '{self.collection_name}'")
        return {'FINISHED'}


# ──────────────────────────────────────────────────────────────
#  OPERATOR – Export Single Collection
# ──────────────────────────────────────────────────────────────

class OBJECT_OT_export_single_collection(bpy.types.Operator):
    bl_idname  = "object.export_single_collection"
    bl_label   = "Export Collection"
    bl_description = "Export only this collection as a .fbx file"
    bl_options = {'REGISTER'}

    collection_name: bpy.props.StringProperty()

    def execute(self, context):
        ok, msg = do_export(context, self.collection_name)
        self.report({'INFO'} if ok else {'ERROR'}, msg)
        return {'FINISHED'} if ok else {'CANCELLED'}


# ──────────────────────────────────────────────────────────────
#  OPERATOR – Export Selected as Single FBX
# ──────────────────────────────────────────────────────────────

class OBJECT_OT_export_selected_single(bpy.types.Operator):
    bl_idname  = "object.export_selected_single"
    bl_label   = "Export Selected as FBX"
    bl_description = (
        "Exports all selected meshes into a single .fbx file "
        "regardless of their collection. Named: blendfile_Selected.fbx"
    )
    bl_options = {'REGISTER'}

    def execute(self, context):
        if not bpy.data.filepath:
            self.report({'ERROR'}, "Save the .blend file first.")
            return {'CANCELLED'}

        meshes = [o for o in context.selected_objects if o.type == 'MESH']
        if not meshes:
            self.report({'WARNING'}, "No mesh objects selected.")
            return {'CANCELLED'}

        # Make sure all selected meshes are visible so export picks them up
        for obj in meshes:
            obj.hide_set(False)

        fbx_path = get_export_path(bpy.data.filepath, "Selected")
        bpy.ops.export_scene.fbx(**fbx_export_params(fbx_path))

        self.report({'INFO'}, f"✓ Exported {len(meshes)} mesh(es) → {os.path.basename(fbx_path)}")
        return {'FINISHED'}




class OBJECT_OT_export_car_collections(bpy.types.Operator):
    bl_idname  = "object.export_car_collections"
    bl_label   = "Export All Collections as FBX"
    bl_description = "Export each collection (except NO_Export) as a separate .fbx file"
    bl_options = {'REGISTER'}

    def execute(self, context):
        if not bpy.data.filepath:
            self.report({'ERROR'}, "Save the .blend file first.")
            return {'CANCELLED'}

        exported, skipped = [], []
        for cname, _, _ in CAR_COLLECTIONS:
            if cname == "NO_Export":
                continue
            ok, msg = do_export(context, cname)
            (exported if ok else skipped).append(cname)

        self.report({'INFO'},
            f"Exported: {', '.join(exported) or 'none'}"
            + (f" | Empty / skipped: {', '.join(skipped)}" if skipped else "")
        )
        return {'FINISHED'}


# ──────────────────────────────────────────────────────────────
#  PANEL
# ──────────────────────────────────────────────────────────────

class VIEW3D_PT_car_prep_panel(bpy.types.Panel):
    bl_label       = "Car Prep Tool"
    bl_idname      = "VIEW3D_PT_car_prep_panel"
    bl_space_type  = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category    = "Car Prep"

    def draw(self, context):
        layout = self.layout
        props  = context.scene.car_prep_props
        meshes = [o for o in context.selected_objects if o.type == 'MESH']

        icons = {
            "Front_Left_Wheel":    'MESH_CIRCLE',
            "Front_Right_Wheel":   'MESH_CIRCLE',
            "Rear_Left_Wheel":     'MESH_CIRCLE',
            "Rear_Right_Wheel":    'MESH_CIRCLE',
            "Body":                'MESH_CUBE',
            "Glass":               'SHADING_RENDERED',
            "Front_Left_Caliper":  'MESH_TORUS',
            "Front_Right_Caliper": 'MESH_TORUS',
            "Rear_Left_Caliper":   'MESH_TORUS',
            "Rear_Right_Caliper":  'MESH_TORUS',
            "Interior":            'SNAP_FACE_CENTER',
            "NO_Export":           'RESTRICT_RENDER_ON',
        }

        # ── Current Selection ──────────────────────────────────
        box = layout.box()
        box.label(text="Current selection:", icon='INFO')
        if meshes:
            box.label(text=f"  {len(meshes)} mesh(es) selected", icon='CHECKMARK')
        else:
            box.label(text="  Select meshes first", icon='ERROR')

        layout.separator()

        # ── 1. Fix Pivot ───────────────────────────────────────
        layout.label(text="1. Pivot & Orientation:", icon='ORIENTATION_GLOBAL')
        layout.prop(props, "original_front", text="Original Front")
        row = layout.row()
        row.scale_y = 1.8
        row.enabled = len(meshes) > 0
        row.operator("object.fix_car_pivot", text="▶  Fix Car Pivot", icon='CHECKMARK')

        layout.separator()

        # ── 2. Scale Check ─────────────────────────────────────
        layout.label(text="2. Scale Check:", icon='FULLSCREEN_ENTER')

        if meshes:
            _, all_m = get_root_and_meshes(context)
            if all_m:
                mn, mx = global_bounding_box(all_m)
                dims    = [mx.x-mn.x, mx.y-mn.y, mx.z-mn.z]
                longest = max(dims)
                magnitude = math.floor(math.log10(longest)) if longest > 0 else 0
                box_s = layout.box()
                if magnitude == 0:
                    box_s.label(text=f"  Longest dim: {longest:.4f}m  ✓", icon='CHECKMARK')
                else:
                    factor_display = 10 ** abs(magnitude)
                    direction = f"÷{factor_display}" if magnitude > 0 else f"×{factor_display}"
                    box_s.label(text=f"  Longest dim: {longest:.4f}m — fix: {direction}", icon='ERROR')

        row = layout.row()
        row.scale_y = 1.5
        row.enabled = len(meshes) > 0
        row.operator("object.fix_car_scale", text="▶  Set Proper Scale", icon='FULLSCREEN_ENTER')

        layout.separator()

        # ── 3. Collections ─────────────────────────────────────
        layout.label(text="3. Assign to Collection:", icon='OUTLINER_COLLECTION')
        col_ui = layout.column(align=True)
        for cname, label, _ in CAR_COLLECTIONS:
            row = col_ui.row(align=True)
            row.alert = (cname == "NO_Export")

            sub = row.row(align=True)
            sub.enabled = len(meshes) > 0
            op = sub.operator(
                "object.assign_car_collection",
                text=label,
                icon=icons.get(cname, 'OUTLINER_COLLECTION'),
            )
            op.collection_name = cname

            # Toggle visibility
            col_exists = bpy.data.collections.get(cname)
            if col_exists:
                lc = find_layer_collection(context.view_layer.layer_collection, cname)
                eye_icon = 'HIDE_ON' if (lc and lc.hide_viewport) else 'HIDE_OFF'
            else:
                eye_icon = 'HIDE_ON'
            tog = row.operator("object.toggle_car_collection", text="", icon=eye_icon)
            tog.collection_name = cname

            # Export individual (not for NO_Export)
            if cname != "NO_Export":
                exp = row.operator("object.export_single_collection", text="", icon='EXPORT')
                exp.collection_name = cname

        layout.separator()

        # ── 4. Export ──────────────────────────────────────────
        layout.label(text="4. Export:", icon='EXPORT')

        blend_saved = bool(bpy.data.filepath)
        box3 = layout.box()
        if blend_saved:
            box3.label(text="Output folder:", icon='FILE_FOLDER')
            box3.label(text=f"  .../{os.path.basename(os.path.dirname(bpy.data.filepath))}/export/")
        else:
            box3.alert = True
            box3.label(text="Save the .blend file first", icon='ERROR')

        row = layout.row()
        row.scale_y = 1.8
        row.operator("object.export_car_collections", text="▶  Export All Collections to FBX", icon='EXPORT')

        layout.separator()

        row2 = layout.row()
        row2.scale_y = 1.5
        row2.enabled = len(meshes) > 0
        row2.operator("object.export_selected_single", text="▶  Export Selected as FBX", icon='MESH_DATA')

        layout.separator()

        # ── Collections Status ─────────────────────────────────
        box4 = layout.box()
        box4.label(text="Collections in scene:", icon='OUTLINER_COLLECTION')
        for cname, label, _ in CAR_COLLECTIONS:
            exists = bpy.data.collections.get(cname)
            count  = len(exists.objects) if exists else 0
            icon   = 'CHECKMARK' if exists else 'RADIOBUT_OFF'
            box4.label(text=f"  {label}  ({count})" if exists else f"  {label}", icon=icon)

        # ── Signature ──────────────────────────────────────────
        layout.separator()
        col = layout.column()
        col.enabled = False
        col.label(text="Car Prep Tool by Alfredo Mendez", icon='AUTO')


# ──────────────────────────────────────────────────────────────
#  REGISTRATION
# ──────────────────────────────────────────────────────────────

classes = (
    CarPrepProperties,
    CarPrepAddonPreferences,
    OBJECT_OT_fix_car_scale,
    OBJECT_OT_fix_car_pivot,
    OBJECT_OT_toggle_car_collection,
    OBJECT_OT_assign_car_collection,
    OBJECT_OT_export_single_collection,
    OBJECT_OT_export_selected_single,
    OBJECT_OT_export_car_collections,
    VIEW3D_PT_car_prep_panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.car_prep_props = bpy.props.PointerProperty(type=CarPrepProperties)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.car_prep_props

if __name__ == "__main__":
    register()
