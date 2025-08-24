#=============================================================================
#
# Module:  Simple RigidBody renderer.
#
#=============================================================================

import bpy
import bmesh
import math
from mathutils import Vector, Matrix, Quaternion

VISUALIZATION_TAG = "matx_rb_visualization"
PARENT_TAG = "matx_rb_parent"
_panel_function = None

from . import matx_exporter

#=========================================================================
#==-------------------------------------
# VISUALIZER
#==-------------------------------------    
#=========================================================================  

def create_rigidbody_visualization(context):
    obj = context.object
    if not obj or not hasattr(obj, 'matx_rigid_body') or not obj.matx_rigid_body.enabled:
        return {'CANCELLED'}
    
    rb = obj.matx_rigid_body
    rb_type = rb.rb_type
    
    remove_old_visualization(obj)
    
    vis_mesh = None
    if rb_type == 'BOX':
        vis_mesh = create_box_mesh(rb.width, rb.height, rb.length)
    elif rb_type == 'SPHERE':
        vis_mesh = create_sphere_mesh(rb.radius)
    elif rb_type == 'CAPSULE':
        vis_mesh = create_capsule_mesh(rb.radius, rb.height)
    
    if not vis_mesh:
        return {'CANCELLED'}
    
    vis_obj = bpy.data.objects.new(f"{obj.name}_RB_Vis", vis_mesh)
    context.collection.objects.link(vis_obj)
    
    vis_obj.display_type = 'WIRE'
    vis_obj.show_in_front = True
    
    vis_obj.parent = obj
    
    vis_obj.location = rb.body_position
    
    rot = rb.body_rotation
    vis_obj.rotation_mode = 'QUATERNION'
    vis_obj.rotation_quaternion = (rot[0], rot[1], rot[2], rot[3])
    
    vis_obj.scale = rb.body_scale
    
    vis_obj[VISUALIZATION_TAG] = True
    vis_obj[PARENT_TAG] = obj.name
    
    vis_obj.hide_select = True
    vis_obj.hide_render = True
    
    return {'FINISHED'}

#=========================================================================

def remove_old_visualization(obj):
    for vis_obj in bpy.data.objects:
        if VISUALIZATION_TAG in vis_obj and vis_obj.get(PARENT_TAG) == obj.name:
            for collection in vis_obj.users_collection:
                collection.objects.unlink(vis_obj)
            
            mesh = vis_obj.data
            bpy.data.objects.remove(vis_obj)
            if mesh and mesh.users == 0:
                bpy.data.meshes.remove(mesh)
                
#========================================================================= 
#==-------------------------------------
# BODIES
#==-------------------------------------    
#=========================================================================                

def create_box_mesh(width, height, length):
    mesh = bpy.data.meshes.new("RB_Box")
    bm = bmesh.new()
    
    hw, hh, hl = width/2, height/2, length/2
    
    v1 = bm.verts.new((-hw, -hh, -hl))
    v2 = bm.verts.new((hw, -hh, -hl))
    v3 = bm.verts.new((hw, hh, -hl))
    v4 = bm.verts.new((-hw, hh, -hl))
    v5 = bm.verts.new((-hw, -hh, hl))
    v6 = bm.verts.new((hw, -hh, hl))
    v7 = bm.verts.new((hw, hh, hl))
    v8 = bm.verts.new((-hw, hh, hl))
    
    bm.edges.new((v1, v2))
    bm.edges.new((v2, v3))
    bm.edges.new((v3, v4))
    bm.edges.new((v4, v1))
    
    bm.edges.new((v5, v6))
    bm.edges.new((v6, v7))
    bm.edges.new((v7, v8))
    bm.edges.new((v8, v5))
    
    bm.edges.new((v1, v5))
    bm.edges.new((v2, v6))
    bm.edges.new((v3, v7))
    bm.edges.new((v4, v8))
    
    bm.to_mesh(mesh)
    bm.free()
    
    return mesh

#=========================================================================

def create_sphere_mesh(radius, segments=16):
    mesh = bpy.data.meshes.new("RB_Sphere")
    bm = bmesh.new()
    
    for axis in range(3):
        prev_vert = None
        first_vert = None
        
        for i in range(segments):
            angle = 2.0 * math.pi * i / segments
            x, y, z = 0, 0, 0
            
            if axis == 0:
                y = radius * math.cos(angle)
                z = radius * math.sin(angle)
            elif axis == 1:
                x = radius * math.cos(angle)
                z = radius * math.sin(angle)
            elif axis == 2:
                x = radius * math.cos(angle)
                y = radius * math.sin(angle)
            
            vert = bm.verts.new((x, y, z))
            
            if prev_vert:
                bm.edges.new((prev_vert, vert))
            else:
                first_vert = vert
            
            prev_vert = vert
            
            if i == segments - 1:
                bm.edges.new((vert, first_vert))
    
    bm.to_mesh(mesh)
    bm.free()
    
    return mesh

#=========================================================================

def create_capsule_mesh(radius, height, segments=16):
    mesh = bpy.data.meshes.new("RB_Capsule")
    bm = bmesh.new()
    
    cyl_height = height - 2 * radius if height > 2 * radius else 0
    half_height = cyl_height / 2
    
    v1_bottom = bm.verts.new((0, 0, -half_height-radius))
    v1_top = bm.verts.new((0, 0, half_height+radius))
    bm.edges.new((v1_bottom, v1_top))
    
    v2_bottom = bm.verts.new((0, radius, -half_height))
    v2_top = bm.verts.new((0, radius, half_height))
    bm.edges.new((v2_bottom, v2_top))
    
    v3_bottom = bm.verts.new((radius, 0, -half_height))
    v3_top = bm.verts.new((radius, 0, half_height))
    bm.edges.new((v3_bottom, v3_top))
    
    for z in [-half_height, half_height]:
        prev_vert = None
        first_vert = None
        
        for i in range(segments):
            angle = 2.0 * math.pi * i / segments
            x = radius * math.cos(angle)
            y = radius * math.sin(angle)
            
            vert = bm.verts.new((x, y, z))
            
            if prev_vert:
                bm.edges.new((prev_vert, vert))
            else:
                first_vert = vert
            
            prev_vert = vert
            
            if i == segments - 1:
                bm.edges.new((vert, first_vert))
    
    for cap_z, cap_sign in [(-half_height, -1), (half_height, 1)]:
        for axis in range(2):
            prev_vert = None
            
            for i in range(segments // 2 + 1):
                angle = math.pi * i / (segments // 2)
                x, y, z = 0, 0, 0
                
                if axis == 0:
                    x = radius * math.sin(angle)
                    z = cap_z + cap_sign * radius * math.cos(angle)
                    vert = bm.verts.new((x, 0, z))
                else:
                    y = radius * math.sin(angle)
                    z = cap_z + cap_sign * radius * math.cos(angle)
                    vert = bm.verts.new((0, y, z))
                
                if prev_vert:
                    bm.edges.new((prev_vert, vert))
                
                prev_vert = vert
    
    bm.to_mesh(mesh)
    bm.free()
    
    return mesh
    
#=========================================================================
#==-------------------------------------
# OTHER
#==-------------------------------------    
#=========================================================================     

def fit_rigidbody_to_mesh(context):
    obj = context.object
    if not obj or obj.type != 'MESH' or not hasattr(obj, 'matx_rigid_body'):
        return {'CANCELLED'}
    
    rb = obj.matx_rigid_body
    mesh = obj.data
    
    if len(mesh.vertices) == 0:
        return {'CANCELLED'}
    
    min_x = min_y = min_z = float('inf')
    max_x = max_y = max_z = float('-inf')
    
    for vert in mesh.vertices:
        co = vert.co
        
        min_x = min(min_x, co.x)
        min_y = min(min_y, co.y)
        min_z = min(min_z, co.z)
        
        max_x = max(max_x, co.x)
        max_y = max(max_y, co.y)
        max_z = max(max_z, co.z)
    
    width = max_x - min_x
    height = max_y - min_y
    length = max_z - min_z
    
    center_x = (min_x + max_x) / 2
    center_y = (min_y + max_y) / 2
    center_z = (min_z + max_z) / 2
    
    rb.body_position = (center_x, center_y, center_z)
    
    if rb.rb_type == 'BOX':
        rb.width = width
        rb.height = height
        rb.length = length
    elif rb.rb_type == 'SPHERE':
        max_dimension = max(width, height, length)
        rb.radius = max_dimension / 2
    elif rb.rb_type == 'CAPSULE':
        max_xy = max(width, height)
        rb.radius = max_xy / 2
        rb.height = length
    
    for vis_obj in bpy.data.objects:
        if VISUALIZATION_TAG in vis_obj and vis_obj.get(PARENT_TAG) == obj.name:
            create_rigidbody_visualization(context)
            break
    
    return {'FINISHED'}

#=========================================================================

@bpy.app.handlers.persistent
def on_object_removed(dummy):
    vis_objects = [obj for obj in bpy.data.objects if VISUALIZATION_TAG in obj]
    
    for vis_obj in vis_objects:
        parent_name = vis_obj.get(PARENT_TAG)
        parent_exists = False
        
        if parent_name:
            parent_exists = parent_name in bpy.data.objects and bpy.data.objects[parent_name] is not None

        if not parent_exists:
            mesh = vis_obj.data
            for collection in vis_obj.users_collection:
                collection.objects.unlink(vis_obj)
            bpy.data.objects.remove(vis_obj)
            if mesh and mesh.users == 0:
                bpy.data.meshes.remove(mesh)
       
#=========================================================================
       
def cleanup_all_visualizations():
    vis_objects = [obj for obj in bpy.data.objects if VISUALIZATION_TAG in obj]
    
    for vis_obj in vis_objects:
        mesh = vis_obj.data
        for collection in vis_obj.users_collection:
            collection.objects.unlink(vis_obj)
        bpy.data.objects.remove(vis_obj)
        if mesh and mesh.users == 0:
            bpy.data.meshes.remove(mesh)                

#=========================================================================

def exclude_visualizations_from_export():
    
    original_process_func = matx_exporter.pre_process_mesh_for_export
    
    def filtered_pre_process_mesh_for_export(mesh_objects):
        filtered_objects = [obj for obj in mesh_objects if VISUALIZATION_TAG not in obj]
        
        return original_process_func(filtered_objects)
    
    matx_exporter.pre_process_mesh_for_export = filtered_pre_process_mesh_for_export

#=========================================================================

class MATX_OT_create_rigidbody_visualization(bpy.types.Operator):
    bl_idname = "matx.create_rigidbody_visualization"
    bl_label = "Create RigidBody Visualization"
    bl_description = "Creates a wireframe visualization of the current RigidBody settings"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return (context.object and 
                hasattr(context.object, 'matx_rigid_body') and 
                context.object.matx_rigid_body.enabled)
    
    def execute(self, context):
        return create_rigidbody_visualization(context)

class MATX_OT_remove_rigidbody_visualization(bpy.types.Operator):
    bl_idname = "matx.remove_rigidbody_visualization"
    bl_label = "Remove RigidBody Visualization"
    bl_description = "Removes the wireframe visualization of the RigidBody"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        if not (context.object and hasattr(context.object, 'matx_rigid_body')):
            return False
        
        for obj in bpy.data.objects:
            if (VISUALIZATION_TAG in obj and 
                obj.get(PARENT_TAG) == context.object.name):
                return True
        return False
    
    def execute(self, context):
        obj = context.object
        remove_old_visualization(obj)
        return {'FINISHED'}

#=========================================================================

class MATX_OT_fit_rigidbody_to_mesh(bpy.types.Operator):
    bl_idname = "matx.fit_rigidbody_to_mesh"
    bl_label = "Fit to Mesh"
    bl_description = "Adjust RigidBody size to fit the mesh boundaries"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return (context.object and 
                context.object.type == 'MESH' and 
                hasattr(context.object, 'matx_rigid_body') and 
                context.object.matx_rigid_body.enabled)
    
    def execute(self, context):
        return fit_rigidbody_to_mesh(context)

#=========================================================================

def add_buttons_to_panel():
    def add_buttons(self, context):
        obj = context.object
        if not (obj and hasattr(obj, 'matx_rigid_body') and obj.matx_rigid_body.enabled):
            return
        
        layout = self.layout
        
        has_vis = False
        for vis_obj in bpy.data.objects:
            if VISUALIZATION_TAG in vis_obj and vis_obj.get(PARENT_TAG) == obj.name:
                has_vis = True
                break
        
        box = layout.box()
        box.label(text="Visualization")
        
        if has_vis:
            box.operator("matx.remove_rigidbody_visualization", icon='X')
            box.operator("matx.create_rigidbody_visualization", text="Update Visualization", icon='FILE_REFRESH')
        else:
            box.operator("matx.create_rigidbody_visualization", icon='MESH_CUBE')
        
        if obj.type == 'MESH':
            box = layout.box()
            box.label(text="Auto Sizing")
            box.operator("matx.fit_rigidbody_to_mesh", icon='FULLSCREEN_ENTER')
    
    return add_buttons

#=========================================================================     
        
def on_file_load(dummy):
    bpy.app.timers.register(cleanup_all_visualizations, first_interval=0.5)

#=========================================================================    

@bpy.app.handlers.persistent
def on_file_save(dummy):
    cleanup_all_visualizations()        
        
#=========================================================================
#==-------------------------------------
# REG/UNREG
#==-------------------------------------    
#=========================================================================         

def register():
    global _panel_function
    
    bpy.utils.register_class(MATX_OT_create_rigidbody_visualization)
    bpy.utils.register_class(MATX_OT_remove_rigidbody_visualization)
    bpy.utils.register_class(MATX_OT_fit_rigidbody_to_mesh)
    
    _panel_function = add_buttons_to_panel()
    if hasattr(bpy.types, 'MATX_PT_RigidBodyPanel'):
        bpy.types.MATX_PT_RigidBodyPanel.append(_panel_function)
    
    bpy.app.handlers.load_post.append(on_file_load)
    bpy.app.handlers.save_pre.append(on_file_save)
    bpy.app.handlers.depsgraph_update_post.append(on_object_removed)
    
    exclude_visualizations_from_export()

#=========================================================================   

def unregister(): 
    if on_object_removed in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(on_object_removed)
    
    if on_file_load in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(on_file_load)
    
    if on_file_save in bpy.app.handlers.save_pre:
        bpy.app.handlers.save_pre.remove(on_file_save)
    
    bpy.utils.unregister_class(MATX_OT_fit_rigidbody_to_mesh)
    bpy.utils.unregister_class(MATX_OT_remove_rigidbody_visualization)
    bpy.utils.unregister_class(MATX_OT_create_rigidbody_visualization)
    
#=========================================================================    