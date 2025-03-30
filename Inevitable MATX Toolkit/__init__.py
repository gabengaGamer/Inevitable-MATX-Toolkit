#=============================================================================
#
#  Addon:          InevitableMATXToolkit
#
#  Author:         GameSpy
#
#  Date:           Started 1.03.2025
#
#  Module:         Initializer and UI.
#
#=============================================================================

import os
import sys
import bpy
import traceback
from bpy_extras.io_utils import ImportHelper, ExportHelper
from bpy.props import (
    StringProperty, 
    BoolProperty, 
    EnumProperty, 
    IntProperty, 
    FloatProperty,
    FloatVectorProperty,
    PointerProperty,
)
from bpy.types import Operator, PropertyGroup, Panel

bl_info = {
    "name": "Inevitable MATX Toolkit.",
    "author": "GameSpy",
    "version": (1, 0),
    "blender": (4, 0, 0),
    "location": "File > Import/Export > MATX (.matx)",
    "description": "Toolkit for working with .МАТХ files",
    "category": "Import-Export",
}

addon_dir = os.path.dirname(os.path.realpath(__file__))
if addon_dir not in sys.path:
    sys.path.append(addon_dir)

from . import matx_importer
from . import matx_exporter
from . import rigidbody_visualizer

#=========================================================================  
#==-------------------------------------
# MATERIAL PROPERTIES
#==-------------------------------------    
#========================================================================= 

class MATXMaterialProperties(PropertyGroup):
    blend_type: EnumProperty(
        name="Blend Type",
        items=[
            ('BLEND_TYPE_OVERWRITE', "Overwrite", "Replace underlying pixels"),
            ('BLEND_TYPE_ADD', "Add", "Add to underlying pixels"),
            ('BLEND_TYPE_SUB', "Subtract", "Subtract from underlying pixels"),
            ('BLEND_TYPE_MUL', "Multiply", "Multiply with underlying pixels"),
        ],
        default='BLEND_TYPE_OVERWRITE',
        description="Blend method used for this material"
    )
    
    lighting_type: EnumProperty(
        name="Lighting Type",
        items=[
            ('LIGHTING_TYPE_STATIC', "Static", "Only static lighting"),
            ('LIGHTING_TYPE_DYNAMIC', "Dynamic", "Only dynamic lighting"),
            ('LIGHTING_TYPE_STATIC_AND_DYNAMIC', "Static & Dynamic", "Both static and dynamic lighting"),
            ('LIGHTING_TYPE_SELF_ILLUM', "Self Illuminated", "Self illuminated material"),
        ],
        default='LIGHTING_TYPE_STATIC_AND_DYNAMIC',
        description="Lighting method used for this material"
    )
    
    tint_type: EnumProperty(
        name="Tint Type",
        items=[
            ('TINT_TYPE_NONE', "None", "No tinting"),
            ('TINT_TYPE_FIRST_DIFFUSE', "First Diffuse", "Tint first diffuse map"),
            ('TINT_TYPE_FINAL_DIFFUSE_OUTPUT', "Final Diffuse", "Tint final diffuse output"),
            ('TINT_TYPE_FINAL_OUTPUT', "Final Output", "Tint final output"),
            ('TINT_TYPE_CUSTOM1', "Custom 1", "Custom tint 1"),
            ('TINT_TYPE_CUSTOM2', "Custom 2", "Custom tint 2"),
        ],
        default='TINT_TYPE_NONE',
        description="How tinting is applied to the material"
    )
    
    sort_bias: IntProperty(
        name="Sort Bias",
        description="Bias applied to sorting order for transparent objects",
        default=50,
        min=0,
        max=100
    )
    
    two_sided: BoolProperty(
        name="Two Sided",
        description="Render both sides of faces",
        default=False
    )
    
    punchthrough: BoolProperty(
        name="Punchthrough",
        description="Enable punchthrough alpha (no blending)",
        default=False
    )   

#========================================================================= 
#==-------------------------------------
# RIGIDBODY PROPERTIES
#==-------------------------------------    
#=========================================================================

class RigidBodyDOFProperties(PropertyGroup):
    active: BoolProperty(
        name="Active",
        description="Activate constraint for this axis",
        default=False
    )
    limited: BoolProperty(
        name="Limited",
        description="Limit values for this axis",
        default=False
    )
    min: FloatProperty(
        name="Min",
        description="Minimum value",
        default=0.0
    )
    max: FloatProperty(
        name="Max",
        description="Maximum value",
        default=0.0
    )

#=========================================================================

class RigidBodyProperties(PropertyGroup):
    enabled: BoolProperty(
        name="Enabled",
        description="Enable rigid body for this object",
        default=False
    )
    
    rb_type: EnumProperty(
        name="Body Type",
        description="Type of rigid body",
        items=[
            ('BOX', "Box", "Rectangular parallelepiped"),
            ('SPHERE', "Sphere", "Sphere"),
            ('CAPSULE', "Capsule", "Capsule")
        ],
        default='BOX'
    )
    
    mass: FloatProperty(
        name="Mass",
        description="Body mass in kg",
        default=1.0,
        min=0.001
    )
    
    # Dimensions
    radius: FloatProperty(
        name="Radius",
        description="Radius for sphere or capsule",
        default=1.0,
        min=0.001
    )
    
    width: FloatProperty(
        name="Width",
        description="Width for box",
        default=1.0,
        min=0.001
    )
    
    height: FloatProperty(
        name="Height",
        description="Height for box or capsule",
        default=1.0,
        min=0.001
    )
    
    length: FloatProperty(
        name="Length",
        description="Length for box",
        default=1.0,
        min=0.001
    )
    
    # Body position and rotation
    body_position: FloatVectorProperty(
        name="Body Position",
        description="Body position relative to object",
        default=(0.0, 0.0, 0.0),
        subtype='TRANSLATION'
    )
    
    body_rotation: FloatVectorProperty(
        name="Body Rotation",
        description="Body rotation (quaternion)",
        default=(1.0, 0.0, 0.0, 0.0),
        size=4
    )
    
    body_scale: FloatVectorProperty(
        name="Body Scale",
        description="Body scale",
        default=(1.0, 1.0, 1.0),
        subtype='XYZ'
    )
    
    # Pivot position and rotation
    pivot_position: FloatVectorProperty(
        name="Pivot Position",
        description="Pivot point position",
        default=(0.0, 0.0, 0.0),
        subtype='TRANSLATION'
    )
    
    pivot_rotation: FloatVectorProperty(
        name="Pivot Rotation",
        description="Pivot point rotation (quaternion)",
        default=(1.0, 0.0, 0.0, 0.0),
        size=4
    )
    
    pivot_scale: FloatVectorProperty(
        name="Pivot Scale",
        description="Pivot point scale",
        default=(1.0, 1.0, 1.0),
        subtype='XYZ'
    )

#=========================================================================
#==-------------------------------------
# UI
#==-------------------------------------    
#========================================================================= 

class MATX_PT_material_settings(Panel):
    bl_label = "MATX Material Settings"
    bl_idname = "MATX_PT_material_settings"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "material"
    
    def draw(self, context):
        layout = self.layout
        material = context.material
        
        if not material:
            layout.label(text="No active material")
            return
            
        matx_settings = material.matx_settings
        
        col = layout.column()
        col.prop(matx_settings, "blend_type")
        col.prop(matx_settings, "lighting_type")
        col.prop(matx_settings, "tint_type")
        col.prop(matx_settings, "sort_bias")
        col.prop(matx_settings, "two_sided")
        col.prop(matx_settings, "punchthrough")

#=========================================================================

class MATX_PT_RigidBodyPanel(Panel):
    bl_label = "MATX Rigid Body"
    bl_idname = "MATX_PT_RigidBodyPanel"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "physics"
    
    @classmethod
    def poll(cls, context):
        return context.object and context.object.type == 'MESH'
    
    def draw(self, context):
        layout = self.layout
        obj = context.object
        rb = obj.matx_rigid_body
        
        layout.prop(rb, "enabled", text="Enable MATX Rigid Body")
        
        if not rb.enabled:
            return
        
        box = layout.box()
        box.label(text="Basic Properties")
        box.prop(rb, "rb_type")
        box.prop(rb, "mass")

        has_vis = False
        for vis_obj in bpy.data.objects:
            if "matx_rb_visualization" in vis_obj and vis_obj.get("matx_rb_parent") == obj.name:
                has_vis = True
                break       
        
        if has_vis:
            box.operator("matx.remove_rigidbody_visualization", icon='X')
            box.operator("matx.create_rigidbody_visualization", text="Update Visualization", icon='FILE_REFRESH')
        else:
            box.operator("matx.create_rigidbody_visualization", icon='MESH_CUBE')        
        
        box = layout.box()
        box.label(text="Dimensions")
        if rb.rb_type == 'SPHERE':
            box.prop(rb, "radius")
        elif rb.rb_type == 'CAPSULE':
            box.prop(rb, "radius")
            box.prop(rb, "height")
        elif rb.rb_type == 'BOX':
            box.prop(rb, "width")
            box.prop(rb, "height")
            box.prop(rb, "length")
            
        if obj.type == 'MESH':
            box.operator("matx.fit_rigidbody_to_mesh", icon='FULLSCREEN_ENTER')    
        
        box = layout.box()
        box.label(text="Body Transform")
        
        # Body Position
        pos_row = box.column(align=True)
        pos_row.prop(rb, "body_position", text="X", index=0)
        pos_row.prop(rb, "body_position", text="Y", index=1)
        pos_row.prop(rb, "body_position", text="Z", index=2)
        
        # Body Rotation
        box.label(text="Rotation:")
        col = box.column(align=True)
        col.prop(rb, "body_rotation", text="W", index=0)
        col.prop(rb, "body_rotation", text="X", index=1)
        col.prop(rb, "body_rotation", text="Y", index=2)
        col.prop(rb, "body_rotation", text="Z", index=3)
        
        # Body Scale
        box.prop(rb, "body_scale")
        
        box = layout.box()
        box.label(text="Pivot Transform")
        
        # Pivot Position
        pos_row = box.column(align=True)
        pos_row.prop(rb, "pivot_position", text="X", index=0)
        pos_row.prop(rb, "pivot_position", text="Y", index=1)
        pos_row.prop(rb, "pivot_position", text="Z", index=2)
        
        # Pivot Rotation
        box.label(text="Rotation:")
        col = box.column(align=True)
        col.prop(rb, "pivot_rotation", text="W", index=0)
        col.prop(rb, "pivot_rotation", text="X", index=1)
        col.prop(rb, "pivot_rotation", text="Y", index=2)
        col.prop(rb, "pivot_rotation", text="Z", index=3)
        
        # Pivot Scale
        box.prop(rb, "pivot_scale")        
        
        # Degrees of Freedom UI
        box = layout.box()
        box.label(text="Degrees of Freedom")
        
        col = box.column(align=True)
        
        header_row = col.row()
        header_row.label(text="Axis")
        header_row.label(text="Active")
        header_row.label(text="Limited")
        header_row.label(text="Min")
        header_row.label(text="Max")
        
        col.separator()
        
        dofs = [
            {"name": "Translate X", "prop": obj.tx_dof},
            {"name": "Translate Y", "prop": obj.ty_dof},
            {"name": "Translate Z", "prop": obj.tz_dof},
            {"name": "Rotate X", "prop": obj.rx_dof},
            {"name": "Rotate Y", "prop": obj.ry_dof},
            {"name": "Rotate Z", "prop": obj.rz_dof}
        ]
        
        col.label(text="Translation")
        for dof in dofs[:3]:
            row = col.row(align=True)
            row.label(text=dof["name"])
            row.prop(dof["prop"], "active", text="")
            
            limited_row = row.row()
            limited_row.prop(dof["prop"], "limited", text="")
            limited_row.enabled = dof["prop"].active
            
            min_row = row.row()
            min_row.prop(dof["prop"], "min", text="")
            min_row.enabled = dof["prop"].active and dof["prop"].limited
            
            max_row = row.row()
            max_row.prop(dof["prop"], "max", text="")
            max_row.enabled = dof["prop"].active and dof["prop"].limited
        
        col.separator()
        
        col.label(text="Rotation")
        for dof in dofs[3:]:
            row = col.row(align=True)
            row.label(text=dof["name"])
            row.prop(dof["prop"], "active", text="")
            
            limited_row = row.row()
            limited_row.prop(dof["prop"], "limited", text="")
            limited_row.enabled = dof["prop"].active
            
            min_row = row.row()
            min_row.prop(dof["prop"], "min", text="")
            min_row.enabled = dof["prop"].active and dof["prop"].limited
            
            max_row = row.row()
            max_row.prop(dof["prop"], "max", text="")
            max_row.enabled = dof["prop"].active and dof["prop"].limited
            
#=========================================================================
#==-------------------------------------
# IMPORT/EXPORT
#==-------------------------------------    
#=========================================================================

class ImportMatx(Operator, ImportHelper):
    bl_idname = "import_mesh.matx_simple"
    bl_label = "Import MATX"
    
    filename_ext = ".matx"
    filter_glob: StringProperty(default="*.matx", options={'HIDDEN'})
    
    def execute(self, context):
        try:
            return matx_importer.parse_matx_file(self.filepath)
        except Exception as e:
            error_msg = f"Error: {str(e)}\n{traceback.format_exc()}"
            self.report({'ERROR'}, f"Import failed: {str(e)}")
            print(error_msg)
            return {'CANCELLED'}

#=========================================================================

class ExportMatx(Operator, ExportHelper):
    bl_idname = "export_mesh.matx_simple"
    bl_label = "Export MATX"
    
    filename_ext = ".matx"
    filter_glob: StringProperty(default="*.matx", options={'HIDDEN'})   
    
    def execute(self, context):
        try:           
            return matx_exporter.export_matx_file(
                self.filepath, 
                context
            )
        except Exception as e:
            error_msg = f"Error: {str(e)}\n{traceback.format_exc()}"
            self.report({'ERROR'}, f"Export failed: {str(e)}")
            print(error_msg)
            return {'CANCELLED'}

#=========================================================================

def menu_func_import(self, context):
    self.layout.operator(ImportMatx.bl_idname, text="MATX (.matx)")

#=========================================================================

def menu_func_export(self, context):
    self.layout.operator(ExportMatx.bl_idname, text="MATX (.matx)")

#=========================================================================  
#==-------------------------------------
# REG/UNREG
#==-------------------------------------    
#========================================================================= 

def register():
    rigidbody_visualizer.register()
    
    bpy.utils.register_class(MATXMaterialProperties)
    bpy.types.Material.matx_settings = PointerProperty(type=MATXMaterialProperties)
    
    bpy.utils.register_class(RigidBodyDOFProperties)
    bpy.utils.register_class(RigidBodyProperties)    
    bpy.types.Object.matx_rigid_body = PointerProperty(type=RigidBodyProperties)
    bpy.types.Object.tx_dof = PointerProperty(type=RigidBodyDOFProperties)
    bpy.types.Object.ty_dof = PointerProperty(type=RigidBodyDOFProperties)
    bpy.types.Object.tz_dof = PointerProperty(type=RigidBodyDOFProperties)
    bpy.types.Object.rx_dof = PointerProperty(type=RigidBodyDOFProperties)
    bpy.types.Object.ry_dof = PointerProperty(type=RigidBodyDOFProperties)
    bpy.types.Object.rz_dof = PointerProperty(type=RigidBodyDOFProperties)
    
    bpy.utils.register_class(MATX_PT_material_settings)
    bpy.utils.register_class(MATX_PT_RigidBodyPanel)
    
    bpy.utils.register_class(ImportMatx)
    bpy.utils.register_class(ExportMatx)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)

#=========================================================================

def unregister():
    rigidbody_visualizer.unregister()
    
    bpy.utils.unregister_class(MATX_PT_RigidBodyPanel)
    bpy.utils.unregister_class(MATX_PT_material_settings)
    
    del bpy.types.Object.matx_rigid_body
    del bpy.types.Object.tx_dof
    del bpy.types.Object.ty_dof
    del bpy.types.Object.tz_dof
    del bpy.types.Object.rx_dof
    del bpy.types.Object.ry_dof
    del bpy.types.Object.rz_dof
    del bpy.types.Material.matx_settings
    
    bpy.utils.unregister_class(RigidBodyProperties)
    bpy.utils.unregister_class(RigidBodyDOFProperties)
    bpy.utils.unregister_class(MATXMaterialProperties)
    
    bpy.utils.unregister_class(ImportMatx)
    bpy.utils.unregister_class(ExportMatx)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)

#=========================================================================

if __name__ == "__main__":
    register()
    
#=========================================================================    