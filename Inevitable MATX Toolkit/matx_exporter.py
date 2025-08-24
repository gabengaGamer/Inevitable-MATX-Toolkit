#=============================================================================
#
# Module:  MATX exporter. Based on rawmesh2.cpp and other .matx files.
#
#=============================================================================

import bpy
import bmesh
import os
import math
import time
import getpass
import socket
import mathutils
import traceback
from mathutils import Vector, Matrix
from textout import TextWriter, TextType

#=============================================================================

def report(level, message):
    print(f"[{level}] {message}")

#=============================================================================

def write_file_header(writer, filepath, mesh_objects, armature_objects=None):
    report('INFO', "Writing file header metadata")
    
    writer.add_header("MatxVersion")
    writer.add_field("Version:d", 2)
    writer.add_end_line()
    
    current_time = time.localtime()
    writer.add_header("TimeStamp")
    writer.add_field("Time:ddd Date:ddd", 
                    current_time.tm_hour, current_time.tm_min, current_time.tm_sec,
                    current_time.tm_mday, current_time.tm_mon, current_time.tm_year)
    writer.add_end_line()
    
    writer.add_header("UserInfo")
    writer.add_field("UserName:s ComputerName:s", getpass.getuser(), socket.gethostname())
    writer.add_end_line()
    
    armature_objects = armature_objects or []
    
    writer.fp.write("//===================================================================================\n")
    writer.fp.write("//\n")
    writer.fp.write(f"// File: {filepath}\n")
    writer.fp.write("//\n")
    
    total_bones = sum(len(arm.data.bones) for arm in armature_objects) if armature_objects else 1
    total_vertices = sum(len(obj.data.vertices) for obj in mesh_objects)
    total_polygons = sum(len(obj.data.polygons) for obj in mesh_objects)
    
    total_materials = 0
    total_textures = 0
    materials_set = set()
    
    for obj in mesh_objects:
        for mat_slot in obj.material_slots:
            if mat_slot.material and mat_slot.material not in materials_set:
                materials_set.add(mat_slot.material)
                total_materials += 1
                
                if hasattr(mat_slot.material, 'node_tree') and mat_slot.material.node_tree:
                    for node in mat_slot.material.node_tree.nodes:
                        if node.type == 'TEX_IMAGE' and node.image:
                            total_textures += 1
    
    report('INFO', f"Geometry statistics: {total_bones} bones, {total_vertices} vertices, {total_polygons} polygons")
    report('INFO', f"Material statistics: {total_materials} materials, {total_textures} textures")
    
    writer.fp.write(f"// Geometry information\n")
    writer.fp.write(f"//   Bones:{total_bones}\n")
    writer.fp.write(f"//   Vertices:{total_vertices}\n")
    writer.fp.write(f"//   Polygons:{total_polygons}\n")
    writer.fp.write(f"//   Textures:{total_textures}\n")
    writer.fp.write(f"//   Materials:{total_materials}\n")
    writer.fp.write("//\n")
    writer.fp.write(f"// Inevitable Entertainment\n")
    writer.fp.write(f"// Death. Taxes. Games.\n")
    writer.fp.write("//\n")
    writer.fp.write("//===================================================================================\n")
    writer.fp.write("\n")
    
    return {"materials": list(materials_set)}
    
#============================================================================= 
#==-------------------------------------
# MODEL DATA BEGINS HERE
#==-------------------------------------    
#=============================================================================

def export_mesh_data(writer, mesh_objects, name_mapping=None):
    writer.add_header("Mesh", len(mesh_objects))
    for idx, obj in enumerate(mesh_objects):
        original_name = name_mapping.get(obj, obj.name) if name_mapping else obj.name
        report('INFO', f"  Writing mesh index {idx}: '{original_name}'")
        writer.add_field("Index:d Name:s", idx, original_name)
        writer.add_end_line()
    
    report('INFO', "Mesh data export completed")             

#=============================================================================

def export_hierarchy(writer, mesh_objects, armature_objects=None):
    has_real_bones = False
    total_bones = 0
    
    if armature_objects:
        for arm in armature_objects:
            if arm.data.bones and len(arm.data.bones) > 0:
                has_real_bones = True
                total_bones += len(arm.data.bones)
    
    if not has_real_bones:
        report('INFO', "No armatures with bones found, creating default root bone")
        writer.add_header("Hierarchy", 1)
        writer.add_field("Index:d Name:s nChildren:d iParent:d Scale:fff Rotate:ffff Pos:fff LODGroup:d", 
                        0, "NoAnimRoot", 0, -1, 
                        1.0, 1.0, 1.0,
                        0.0, 0.0, 0.0, -1.0,
                        0.0, 0.0, 0.0,
                        -1)
        writer.add_end_line()
        return
    
    report('INFO', f"Exporting hierarchical bone structure from {len(armature_objects)} armatures with total {total_bones} bones")
    
    all_bones = []
    
    for arm_obj in armature_objects:
        if arm_obj.pose:
            arm_world_matrix = arm_obj.matrix_world
            report('INFO', f"Processing armature '{arm_obj.name}' with {len(arm_obj.data.bones)} bones")
            
            for bone in arm_obj.data.bones:
                parent_idx = -1
                if bone.parent:
                    for idx, b in enumerate(all_bones):
                        if b.get('bone_obj') == bone.parent:
                            parent_idx = idx
                            break
                
                bone_idx = len(all_bones)
                all_bones.append({
                    'name': bone.name,
                    'children': [],
                    'parent_idx': parent_idx,
                    'matrix_local': bone.matrix_local,
                    'bone_obj': bone
                })
                
                if parent_idx >= 0:
                    all_bones[parent_idx]['children'].append(bone_idx)
                    report('INFO', f"  Bone '{bone.name}' (idx: {bone_idx}) has parent '{all_bones[parent_idx]['name']}' (idx: {parent_idx})")
                else:
                    report('INFO', f"  Bone '{bone.name}' (idx: {bone_idx}) is a root bone")
    
    writer.add_header("Hierarchy", len(all_bones))
    report('INFO', f"Writing {len(all_bones)} bones to hierarchy")
    
    for idx, bone_data in enumerate(all_bones):
        matrix = bone_data['matrix_local']
        loc, rot, scale = matrix.decompose()
        
        pos = (loc.x, loc.z, -loc.y)
        rot = (rot.w, rot.x, rot.z, -rot.y)
        scale = (scale.x, scale.z, scale.y)
        
        writer.add_field("Index:d Name:s nChildren:d iParent:d Scale:fff Rotate:ffff Pos:fff LODGroup:d", 
                        idx, bone_data['name'], len(bone_data['children']), bone_data['parent_idx'], 
                        scale[0], scale[1], scale[2],
                        rot[0], rot[1], rot[2], rot[3],
                        pos[0], pos[1], pos[2],
                        -1)        
        writer.add_end_line()
    
    report('INFO', "Hierarchy export completed")

#=============================================================================

def export_rigid_bodies(writer, mesh_objects):
    rigid_body_objects = [obj for obj in mesh_objects if hasattr(obj, 'matx_rigid_body') and obj.matx_rigid_body.enabled]
    
    if not rigid_body_objects:
        report('INFO', "No rigid bodies found to export")
        return
    
    report('INFO', f"Exporting {len(rigid_body_objects)} rigid bodies")
    writer.add_header("RigidBodies", len(rigid_body_objects))
    
    def get_rb_type_string(rb_type):
        if rb_type == 'SPHERE':
            return "Sphere"
        elif rb_type == 'CAPSULE':
            return "Cylinder"
        elif rb_type == 'BOX':
            return "Box"
        else:
            return "Sphere"
    
    for idx, obj in enumerate(rigid_body_objects):
        rb = obj.matx_rigid_body
        rb_type_str = get_rb_type_string(rb.rb_type)
        
        parent_idx = -1
        if obj.parent and obj.parent in rigid_body_objects:
            parent_idx = rigid_body_objects.index(obj.parent)
            parent_name = obj.parent.name
            report('INFO', f"  Rigid body '{obj.name}' (type: {rb_type_str}) has parent '{parent_name}' (idx: {parent_idx})")
        else:
            report('INFO', f"  Rigid body '{obj.name}' (type: {rb_type_str}) has no parent, mass: {rb.mass}")
        
        writer.add_field(
            "Index:d Name:s Type:s Mass:f iParent:d "
            "Body_Scale:fff Body_Rotate:ffff Body_Pos:fff "
            "Pivot_Scale:fff Pivot_Rotate:ffff Pivot_Pos:fff "
            "Radius:f Width:f Height:f Length:f "
            "TX_Act:d TX_Lim:d TX_Min:f TX_Max:f "
            "TY_Act:d TY_Lim:d TY_Min:f TY_Max:f "
            "TZ_Act:d TZ_Lim:d TZ_Min:f TZ_Max:f "
            "RX_Act:d RX_Lim:d RX_Min:f RX_Max:f "
            "RY_Act:d RY_Lim:d RY_Min:f RY_Max:f "
            "RZ_Act:d RZ_Lim:d RZ_Min:f RZ_Max:f",
            
            idx, obj.name, rb_type_str, rb.mass, parent_idx,
            
            rb.body_scale[0], rb.body_scale[1], rb.body_scale[2],
            rb.body_rotation[0], rb.body_rotation[1], rb.body_rotation[2], rb.body_rotation[3],
            rb.body_position[0], rb.body_position[1], rb.body_position[2],
            
            rb.pivot_scale[0], rb.pivot_scale[1], rb.pivot_scale[2],
            rb.pivot_rotation[0], rb.pivot_rotation[1], rb.pivot_rotation[2], rb.pivot_rotation[3],
            rb.pivot_position[0], rb.pivot_position[1], rb.pivot_position[2],
            
            rb.radius, rb.width, rb.height, rb.length,
            
            int(obj.tx_dof.active), int(obj.tx_dof.limited), obj.tx_dof.min, obj.tx_dof.max,
            int(obj.ty_dof.active), int(obj.ty_dof.limited), obj.ty_dof.min, obj.ty_dof.max,
            int(obj.tz_dof.active), int(obj.tz_dof.limited), obj.tz_dof.min, obj.tz_dof.max,
            int(obj.rx_dof.active), int(obj.rx_dof.limited), obj.rx_dof.min, obj.rx_dof.max,
            int(obj.ry_dof.active), int(obj.ry_dof.limited), obj.ry_dof.min, obj.ry_dof.max,
            int(obj.rz_dof.active), int(obj.rz_dof.limited), obj.rz_dof.min, obj.rz_dof.max
        )       
        writer.add_end_line()
        
        dof_info = []
        if obj.tx_dof.active: dof_info.append(f"TX: {'limited' if obj.tx_dof.limited else 'free'}")
        if obj.ty_dof.active: dof_info.append(f"TY: {'limited' if obj.ty_dof.limited else 'free'}")
        if obj.tz_dof.active: dof_info.append(f"TZ: {'limited' if obj.tz_dof.limited else 'free'}")
        if obj.rx_dof.active: dof_info.append(f"RX: {'limited' if obj.rx_dof.limited else 'free'}")
        if obj.ry_dof.active: dof_info.append(f"RY: {'limited' if obj.ry_dof.limited else 'free'}")
        if obj.rz_dof.active: dof_info.append(f"RZ: {'limited' if obj.rz_dof.limited else 'free'}")
        
        if dof_info:
            report('INFO', f"    DOF: {', '.join(dof_info)}")
        
    report('INFO', "Rigid bodies export completed")

#=============================================================================

def export_vertices(writer, mesh_objects):
    total_vertices = sum(len(obj.data.vertices) for obj in mesh_objects)
    writer.add_header("Vertices", total_vertices)
    
    vertex_index = 0
    for obj in mesh_objects:
        mesh = obj.data
        world_matrix = obj.matrix_world
        
        for vert in mesh.vertices:
            pos = world_matrix @ vert.co
            pos_max = Vector((pos.x, pos.z, -pos.y))
            
            writer.add_field("Index:d Pos:fff nNormals:d nUVSets:d nColors:d nWeights:d", 
                            vertex_index, pos_max.x, pos_max.y, pos_max.z, 
                            1, 1, 1, 1)
            
            vertex_index += 1
            writer.add_end_line()

#=============================================================================

def export_normals(writer, mesh_objects):
    total_vertices = sum(len(obj.data.vertices) for obj in mesh_objects)
    writer.add_header("Normals", total_vertices)
    
    vertex_index = 0
    for obj in mesh_objects:
        mesh = obj.data
        mesh.calc_normals_split()
        
        world_matrix = obj.matrix_world
        rot_matrix = world_matrix.to_quaternion().to_matrix()
        
        vert_to_loop_normals = {}
        
        for poly in mesh.polygons:
            if not poly.use_smooth:
                poly_normal = poly.normal
                for vert_idx in poly.vertices:
                    if vert_idx not in vert_to_loop_normals:
                        vert_to_loop_normals[vert_idx] = []
                    vert_to_loop_normals[vert_idx].append(poly_normal)
            else:
                for loop_idx in poly.loop_indices:
                    loop = mesh.loops[loop_idx]
                    vert_idx = loop.vertex_index
                    if vert_idx not in vert_to_loop_normals:
                        vert_to_loop_normals[vert_idx] = []
                    vert_to_loop_normals[vert_idx].append(loop.normal)
        
        for vert_idx in range(len(mesh.vertices)):
            if vert_idx in vert_to_loop_normals and vert_to_loop_normals[vert_idx]:
                avg_normal = Vector((0, 0, 0))
                for n in vert_to_loop_normals[vert_idx]:
                    avg_normal += n
                
                if avg_normal.length > 0:
                    avg_normal.normalize()
                else:
                    avg_normal = mesh.vertices[vert_idx].normal
                
                normal_world = rot_matrix @ avg_normal
                normal_max = Vector((normal_world.x, normal_world.z, -normal_world.y)).normalized()
                
                writer.add_field("iVertex:d Index:d Normal:fff", 
                                vertex_index, 0, normal_max.x, normal_max.y, normal_max.z)
            else:
                normal = mesh.vertices[vert_idx].normal
                normal_world = rot_matrix @ normal
                normal_max = Vector((normal_world.x, normal_world.z, -normal_world.y)).normalized()
                
                writer.add_field("iVertex:d Index:d Normal:fff", 
                                vertex_index, 0, normal_max.x, normal_max.y, normal_max.z)
            
            vertex_index += 1
            writer.add_end_line()

#=============================================================================

def export_colors(writer, mesh_objects):
    total_vertices = sum(len(obj.data.vertices) for obj in mesh_objects)
    writer.add_header("Colors", total_vertices)
    
    vertex_index = 0
    for obj in mesh_objects:
        mesh = obj.data
        has_colors = mesh.vertex_colors and len(mesh.vertex_colors) > 0
        
        for _ in mesh.vertices:
            if has_colors:
                writer.add_field("iVertex:d Index:d Color:ffff", 
                                 vertex_index, 0, 1.0, 1.0, 1.0, 1.0) #It's worth adding support for this in the future.
            else:
                writer.add_field("iVertex:d Index:d Color:ffff", 
                                 vertex_index, 0, 1.0, 1.0, 1.0, 1.0)
            
            vertex_index += 1
            writer.add_end_line()

#=============================================================================

def export_uvs(writer, mesh_objects):
    total_vertices = sum(len(obj.data.vertices) for obj in mesh_objects)
    writer.add_header("UVSet", total_vertices)
    
    vertex_index = 0
    for obj in mesh_objects:
        mesh = obj.data
        has_uvs = mesh.uv_layers and len(mesh.uv_layers) > 0
        
        if has_uvs:
            vert_to_uv = {}
            
            uv_layer = mesh.uv_layers[0].data
            
            for poly in mesh.polygons:
                for loop_idx, vert_idx in zip(poly.loop_indices, poly.vertices):
                    if vert_idx not in vert_to_uv:
                        uv = uv_layer[loop_idx].uv
                        vert_to_uv[vert_idx] = uv
            
            for vert_idx in range(len(mesh.vertices)):
                if vert_idx in vert_to_uv:
                    uv = vert_to_uv[vert_idx]
                    uv_y_mirrored = 1.0 - uv.y
                    writer.add_field("iVertex:d Index:d UV:ff", 
                                     vertex_index, 0, uv.x, uv_y_mirrored)
                else:
                    writer.add_field("iVertex:d Index:d UV:ff", 
                                     vertex_index, 0, 0.0, 1.0)
                
                vertex_index += 1
                writer.add_end_line()
        else:
            for _ in range(len(mesh.vertices)):
                writer.add_field("iVertex:d Index:d UV:ff", 
                                vertex_index, 0, 0.0, 1.0)
                vertex_index += 1
                writer.add_end_line()

#=============================================================================

def export_skin_weights(writer, mesh_objects, armature_objects=None):
    total_vertices = sum(len(obj.data.vertices) for obj in mesh_objects)
    writer.add_header("Skin", total_vertices)
    
    has_real_bones = False
    
    if armature_objects:
        for arm in armature_objects:
            if arm.data.bones and len(arm.data.bones) > 0:
                has_real_bones = True
                break
    
    bone_name_to_index = {}
    
    if has_real_bones:
        bone_index = 0
        for arm_obj in armature_objects:
            for bone in arm_obj.data.bones:
                if bone.name not in bone_name_to_index:
                    bone_name_to_index[bone.name] = bone_index
                    bone_index += 1
    
    vertex_index = 0
    for obj in mesh_objects:
        mesh = obj.data
        
        has_weights = False
        armature_obj = None
        
        if has_real_bones:
            for modifier in obj.modifiers:
                if modifier.type == 'ARMATURE' and modifier.object in armature_objects:
                    has_weights = True
                    armature_obj = modifier.object
                    break
        
        if has_real_bones and has_weights and armature_obj:
            vertex_groups = obj.vertex_groups
            
            group_to_bone = {}
            
            for group in vertex_groups:
                if group.name in bone_name_to_index:
                    group_to_bone[group.index] = bone_name_to_index[group.name]
            
            for vert_idx, vert in enumerate(mesh.vertices):
                vert_groups = [g for g in vert.groups if g.weight > 0]
                
                if vert_groups:
                    vert_groups.sort(key=lambda g: g.weight, reverse=True)
                    
                    group = vert_groups[0]
                    bone_index = group_to_bone.get(group.group, 0)
                    
                    writer.add_field("iVertex:d Index:d iBone:d Weight:f", 
                                     vertex_index, 0, bone_index, group.weight)
                else:
                    writer.add_field("iVertex:d Index:d iBone:d Weight:f", 
                                     vertex_index, 0, 0, 1.0)
                
                vertex_index += 1
                writer.add_end_line()
        else:
            for _ in mesh.vertices:
                writer.add_field("iVertex:d Index:d iBone:d Weight:f", 
                                 vertex_index, 0, 0, 1.0)
                vertex_index += 1
                writer.add_end_line()

#=============================================================================

def export_polygons(writer, mesh_objects):
    
    report('INFO', f"Processing polygon data for {len(mesh_objects)} objects")
    
    material_mapping = {}
    all_materials = []
    
    for obj in mesh_objects:
        for slot_idx, slot in enumerate(obj.material_slots):
            if slot.material and slot.material not in all_materials:
                material_mapping[(obj.name, slot_idx)] = len(all_materials)
                all_materials.append(slot.material)
                report('INFO', f"Adding material '{slot.material.name}' for object '{obj.name}'")
            else:
                for i, mat in enumerate(all_materials):
                    if slot.material == mat:
                        material_mapping[(obj.name, slot_idx)] = i
                        break
    
    report('INFO', f"Found {len(all_materials)} unique materials")
    
    all_triangles = []
    total_triangles = 0
    
    for obj_idx, obj in enumerate(mesh_objects):
        mesh = obj.data
        world_matrix = obj.matrix_world
        rot_matrix = world_matrix.to_quaternion().to_matrix()
        
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bmesh.ops.triangulate(bm, faces=bm.faces)
        
        face_count = len(bm.faces)
        total_triangles += face_count
        
        report('INFO', f"Processing '{obj.name}': {face_count} triangulated faces")
        
        for face in bm.faces:
            normal = face.normal
            normal_world = rot_matrix @ normal
            normal_max = Vector((normal_world.x, normal_world.z, -normal_world.y)).normalized()
            
            local_mat_idx = face.material_index if len(obj.material_slots) > 0 else 0
            global_mat_idx = material_mapping.get((obj.name, local_mat_idx), 0)
            
            all_triangles.append({
                'obj_idx': obj_idx,
                'normal': normal_max,
                'material_index': global_mat_idx
            })
        
        bm.free()
    
    report('INFO', f"Writing {total_triangles} triangles to MATX file")
    writer.add_header("Polygons", total_triangles)
    
    for triangle_idx, triangle in enumerate(all_triangles):
        writer.add_field("iMesh:d Index:d nVerts:d Normal:fff iMaterial:d", 
                       triangle['obj_idx'], triangle_idx, 3, 
                       triangle['normal'].x, triangle['normal'].y, triangle['normal'].z, 
                       triangle['material_index'])
        writer.add_end_line()
    
    report('INFO', f"Polygon export completed")
    return all_materials

#=============================================================================

def export_facet_index(writer, mesh_objects):
    all_facets = []
    vertex_offset = 0
    
    for obj_idx, obj in enumerate(mesh_objects):
        mesh = obj.data  
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bmesh.ops.triangulate(bm, faces=bm.faces)
        
        triangles_for_obj = []
        for face in bm.faces:
            if len(face.verts) >= 3:
                triangle = [face.verts[0].index + vertex_offset,
                            face.verts[1].index + vertex_offset,
                            face.verts[2].index + vertex_offset]
                triangles_for_obj.append(triangle)
        
        all_facets.extend(triangles_for_obj)
        
        bm.free()
        
        vertex_offset += len(mesh.vertices)
    
    total_facets = len(all_facets)
    total_indices = total_facets * 3
    
    if total_indices > 0:
        writer.add_header("FacetIndex", total_indices)
        
        facet_idx = 0
        for triangle in all_facets:
            writer.add_field("iFacet:d Index:d iVertex:d", facet_idx, 0, triangle[0])
            writer.add_end_line()
            writer.add_field("iFacet:d Index:d iVertex:d", facet_idx, 1, triangle[1])
            writer.add_end_line()
            writer.add_field("iFacet:d Index:d iVertex:d", facet_idx, 2, triangle[2])
            writer.add_end_line()
            facet_idx += 1
    else:
        writer.add_header("FacetIndex", 0)
        writer.add_end_line()
              
#=============================================================================
#==-------------------------------------
# MATERIAL DATA BEGINS HERE
#==-------------------------------------    
#=============================================================================      

def export_materials(writer, materials):
    textures = []
    report('INFO', f"Processing {len(materials)} materials")
    
    for mat in materials:
        if mat and hasattr(mat, 'node_tree') and mat.node_tree:
            mat_textures = []
            for node in mat.node_tree.nodes:
                if node.type == 'TEX_IMAGE' and node.image:
                    if node.image not in textures:
                        textures.append(node.image)
                        mat_textures.append(node.image.name)
            if mat_textures:
                report('INFO', f"Material '{mat.name}' uses textures: {', '.join(mat_textures)}")
    
    report('INFO', f"Found {len(textures)} unique textures")
    writer.add_header("Materials", len(materials))
    
    for idx, mat in enumerate(materials):
        name = mat.name if mat else f"Material_{idx}"
        
        matx_settings = getattr(mat, "matx_settings", None)
        
        lighting_type = "STATIC_AND_DYNAMIC"
        blend_type = "OVERWRITE"
        tint_type = "NONE"
        two_sided = 0
        sort_bias = 50
        punchthrough = 0
        
        if matx_settings:
            if hasattr(matx_settings, "lighting_type"):
                lighting_type = matx_settings.lighting_type.replace("LIGHTING_TYPE_", "")
            if hasattr(matx_settings, "blend_type"):
                blend_type = matx_settings.blend_type.replace("BLEND_TYPE_", "")
            if hasattr(matx_settings, "tint_type"):
                tint_type = matx_settings.tint_type.replace("TINT_TYPE_", "")
            if hasattr(matx_settings, "two_sided"):
                two_sided = 1 if matx_settings.two_sided else 0
            if hasattr(matx_settings, "sort_bias"):
                sort_bias = matx_settings.sort_bias
            if hasattr(matx_settings, "punchthrough"):
                punchthrough = 1 if matx_settings.punchthrough else 0
            
            report('INFO', f"Material '{name}' settings: lighting={lighting_type}, blend={blend_type}, tint={tint_type}, two_sided={two_sided}")
        
        writer.add_field("Index:d Name:s Type:d LightingType:s BlendType:s TwoSided:d RandomAnim:d SortBias:d TintType:s Punchthrough:d VertexAlpha:d ExposeName:d", 
                        idx, name, 1, lighting_type, blend_type, 
                        two_sided, 0, sort_bias, tint_type, punchthrough, 0, 0)
        writer.add_end_line()               
    
    if len(materials) > 0 and len(textures) > 0:
        report('INFO', f"Exporting material-texture links")
        export_material_textures(writer, materials, textures)
    
    return textures

#=============================================================================

def export_material_textures(writer, materials, textures):
    material_texture_links = []
    
    for mat_idx, mat in enumerate(materials):
        if mat and hasattr(mat, 'node_tree') and mat.node_tree:
            for node in mat.node_tree.nodes:
                if node.type == 'TEX_IMAGE' and node.image:
                    material_texture_links.append({
                        'material_idx': mat_idx,
                        'material_name': mat.name,
                        'texture_path': node.image.filepath
                    })
                    break
    
    writer.add_header("Material_Textures", len(material_texture_links))
    
    for idx, link in enumerate(material_texture_links):
        writer.add_field("Index:d Filename:s", idx, link['texture_path'])
        writer.add_end_line()
    
    export_material_params(writer, materials)

#=============================================================================

def export_material_params(writer, materials):
    if not materials or len(materials) == 0:
        return
    
    param_count = 0
    for _ in materials:
        param_count += 58
    
    writer.add_header("Material_ParamPkg", int(param_count))
    
    for mat_idx, mat in enumerate(materials):
        writer.add_field("Index:d iMaterial:d iMap:d iPackage:s Current_0:f Current_1:f Current_2:f Current_3:f ModeType:s FPS:d iKeys:d nKeys:d nParamsPerKey:d", 
                        mat_idx * 58, mat_idx, -1, "Tint Color", 
                        255.0, 255.0, 255.0, 0.0, 
                        "CYCLE", 30, -1, 0, 3)
        writer.add_end_line()
        
        writer.add_field("Index:d iMaterial:d iMap:d iPackage:s Current_0:f Current_1:f Current_2:f Current_3:f ModeType:s FPS:d iKeys:d nKeys:d nParamsPerKey:d", 
                        mat_idx * 58 + 1, mat_idx, -1, "Tint Alpha", 
                        255.0, 0.0, 0.0, 0.0, 
                        "CYCLE", 30, -1, 0, 1)
        writer.add_end_line()
        
        for i in range(2, 58):
            package_name = None
            current_values = [0.0, 0.0, 0.0, 0.0]
            current_map_idx = -1
            fps_value = 30
            
            if i < 10:
                package_name = f"Constant{i-2}"
            else:
                current_map_idx = (i - 10) // 3
                map_type_idx = (i - 10) % 3
                map_type = ["UV Translation", "UV Rotation", "UV Scale"][map_type_idx]
                package_name = map_type
                
                if map_type == "UV Scale" and current_map_idx == 0:
                    current_values[0] = 1.0
                    current_values[1] = 1.0
                
                fps_value = 30 if current_map_idx == 0 else 0
            
            writer.add_field("Index:d iMaterial:d iMap:d iPackage:s Current_0:f Current_1:f Current_2:f Current_3:f ModeType:s FPS:d iKeys:d nKeys:d nParamsPerKey:d", 
                            mat_idx * 58 + i, mat_idx, 
                            current_map_idx, package_name, 
                            current_values[0], current_values[1], current_values[2], current_values[3], 
                            "CYCLE", fps_value, -1, 0, 
                            3 if package_name == "Tint Color" else (2 if "Translation" in package_name or "Scale" in package_name else 1))
            writer.add_end_line()        

#=============================================================================

def export_material_maps(writer, materials):
    if not materials or len(materials) == 0:
        writer.add_header("Material_Maps", 0)
        writer.add_end_line()
        return
    
    map_count = 0
    for _ in materials:
        map_count += 16
    
    writer.add_header("Material_Maps", map_count)
    
    for mat_idx, mat in enumerate(materials):
        for map_idx in range(16):
            tex_idx = mat_idx if map_idx == 0 else -1
            tex_count = 1 if map_idx == 0 else 0
            fps = 30 if map_idx == 0 else 0
            uv_idx = 0 if map_idx == 0 else -1
            
            writer.add_field("Index:d iMaterial:d iMap:d iTextures:d nTextures:d TextureFPS:d iUV:d RGBASource:s FilterType:s UAddress:s VAddress:s", 
                            mat_idx * 16 + map_idx, mat_idx, 
                            map_idx, tex_idx, tex_count, fps, uv_idx, 
                            "RGB", "BILINEAR", "WRAP", "WRAP")
            writer.add_end_line()

#=============================================================================

def pre_process_mesh_for_export(mesh_objects):
    processed_objects = []
    name_mapping = {}
    
    for obj in mesh_objects:
        report('INFO', f"Pre-processing mesh '{obj.name}'")
        
        obj_copy = obj.copy()
        mesh_copy = obj.data.copy()
        obj_copy.data = mesh_copy
        obj_copy.name = obj.name + "_export"
        
        name_mapping[obj_copy] = obj.name
        
        bpy.context.collection.objects.link(obj_copy)
        report('INFO', f"  Created temporary object '{obj_copy.name}' for export")
        
        mesh = obj_copy.data
        
        bm = bmesh.new()
        bm.from_mesh(mesh)
        
        uv_layer = None
        if hasattr(bm.loops.layers, 'uv') and bm.loops.layers.uv:
            uv_layer = bm.loops.layers.uv.active
            report('INFO', f"  Found UV layer")
        
        seam_edges = []
        sharp_edges = []
        
        report('INFO', f"  Analyzing mesh topology for '{obj_copy.name}'")
        
        for edge in bm.edges:
            if len(edge.link_faces) < 2:
                continue
            
            is_uv_seam = False
            is_sharp_edge = False
            
            if uv_layer:
                uv_coords = set()
                for face in edge.link_faces:
                    for loop in face.loops:
                        if loop.vert in edge.verts:
                            uv = loop[uv_layer].uv
                            uv_coords.add((round(uv.x, 6), round(uv.y, 6)))
                
                if len(uv_coords) > 2:
                    is_uv_seam = True
            
            connected_faces = list(edge.link_faces)
            if len(connected_faces) >= 2:
                has_flat = any(not face.smooth for face in connected_faces)
                has_smooth = any(face.smooth for face in connected_faces)
                
                if has_flat:
                    face_normals = [face.normal for face in connected_faces]
                    if len(face_normals) >= 2:
                        angle = face_normals[0].angle(face_normals[1])
                        if angle > 0.523599:  # ~30 degrees
                            is_sharp_edge = True
            
            if is_uv_seam:
                seam_edges.append(edge)
            if is_sharp_edge:
                sharp_edges.append(edge)
        
        report('INFO', f"  Found {len(seam_edges)} UV seam edges and {len(sharp_edges)} sharp edges")
        
        all_edges_to_split = list(set(seam_edges + sharp_edges))
        
        if all_edges_to_split:
            report('INFO', f"  Splitting {len(all_edges_to_split)} edges")
            bmesh.ops.split_edges(bm, edges=all_edges_to_split)
        
        report('INFO', f"  Triangulating mesh")
        result = bmesh.ops.triangulate(bm, faces=bm.faces[:])
        report('INFO', f"  Triangulation created {len(result.get('faces', []))} triangular faces")
        
        bm.to_mesh(mesh)
        bm.free()
        
        mesh.update()
        mesh.validate()
        
        report('INFO', f"  Final processed mesh: {len(mesh.vertices)} vertices, {len(mesh.polygons)} faces")
        mesh.calc_normals_split()
        
        processed_objects.append(obj_copy)
    
    report('INFO', f"Pre-processing completed, created {len(processed_objects)} processed meshes")
    return processed_objects, name_mapping

#=============================================================================

def export_matx_file(filepath, context):
    mesh_objects = [obj for obj in context.view_layer.objects if obj.type == 'MESH']
    armature_objects = [obj for obj in context.view_layer.objects if obj.type == 'ARMATURE']
    
    if not mesh_objects:
        report('ERROR', "No meshes found for export")
        return {'CANCELLED'}
    
    temp_object_names = []
    
    writer = None
    try:
        processed_mesh_objects, name_mapping = pre_process_mesh_for_export(mesh_objects)
        
        temp_object_names = [obj.name for obj in processed_mesh_objects if obj.name.endswith("_export")]
        
        writer = TextWriter()
        writer.open_file(filepath)
        
        resources = write_file_header(writer, filepath, processed_mesh_objects, armature_objects)
        materials = resources.get("materials", [])
        
        export_mesh_data(writer, processed_mesh_objects, name_mapping)
        
        export_hierarchy(writer, processed_mesh_objects, armature_objects)
        
        export_rigid_bodies(writer, processed_mesh_objects)
        
        export_vertices(writer, processed_mesh_objects)
        export_normals(writer, processed_mesh_objects)
        export_colors(writer, processed_mesh_objects)
        export_uvs(writer, processed_mesh_objects)
        export_skin_weights(writer, processed_mesh_objects, armature_objects)
        
        all_materials = export_polygons(writer, processed_mesh_objects)
        export_facet_index(writer, processed_mesh_objects)        
        textures = export_materials(writer, all_materials)       
        export_material_maps(writer, all_materials)  
        
        writer.fp.write("//===================================================================================\n")
        writer.fp.write("/*\n")
        writer.fp.write("*/\n")
        
        report('INFO', f"MATX export completed: {filepath}")
        return {'FINISHED'}
    
    except Exception as e:
        error_msg = f"MATX export failed: {str(e)}\n{traceback.format_exc()}"
        report('ERROR', error_msg)
        return {'CANCELLED'}
    
    finally:
        if writer and hasattr(writer, 'fp') and writer.fp:
            writer.close_file()
            
        try:
            for name in temp_object_names:
                if name in bpy.data.objects:
                    obj = bpy.data.objects[name]
                    mesh_data = obj.data
                    bpy.context.collection.objects.unlink(obj)
                    bpy.data.objects.remove(obj)
                    if mesh_data and mesh_data.users == 0:
                        bpy.data.meshes.remove(mesh_data)
        except Exception as e:
            report('WARNING', f"Error clearing temporary objects: {str(e)}")    
            
#=============================================================================             