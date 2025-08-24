#=============================================================================
#
# Module:  MATX importer. Based on rawmesh2.cpp and other .matx files.
#
#=============================================================================

import bpy
import bmesh
import os
import math
from mathutils import Vector
from textin import TextParser

#=============================================================================

def report(level, message):
    print(f"[{level}] {message}")

#=============================================================================

def parse_matx_file(filepath):
    parser = TextParser()
    sections = parser.parse_file(filepath)   
    report('INFO', f"Loaded sections: {', '.join(sections.keys())}")
    
    matx_version = "1"
    if 'MatxVersion' in sections:
        if sections['MatxVersion'].data and len(sections['MatxVersion'].data[0]) > 0:
            matx_version = str(sections['MatxVersion'].data[0][0])
            report('INFO', f"MATX Version: {matx_version}")
    
    if matx_version.startswith("2"):   
        timestamp_section         = sections.get('TimeStamp')
        userinfo_section          = sections.get('UserInfo')
        mesh_section              = sections.get('Mesh')
        hierarchy_section         = sections.get('Hierarchy')
        vertices_section          = sections.get('Vertices')
        normals_section           = sections.get('Normals')
        colors_section            = sections.get('Colors')
        uvset_section             = sections.get('UVSet')
        skin_section              = sections.get('Skin')
        polygons_section          = sections.get('Polygons')
        facet_section             = sections.get('FacetIndex')
        materials_section         = sections.get('Materials')  
        material_textures_section = sections.get('Material_Textures')
        material_parampkg_section = sections.get('Material_ParamPkg')
        material_maps_section     = sections.get('Material_Maps')         
     
        report('INFO', f"Mesh             count: {len(mesh_section.data) if mesh_section else 0}")
        report('INFO', f"Hierarchy        count: {len(hierarchy_section.data) if hierarchy_section else 0}")
        report('INFO', f"Vertices         count: {len(vertices_section.data) if vertices_section else 0}")
        report('INFO', f"Normal           count: {len(normals_section.data) if normals_section else 0}")
        report('INFO', f"Color            count: {len(colors_section.data) if colors_section else 0}")
        report('INFO', f"UV               count: {len(uvset_section.data) if uvset_section else 0}")
        report('INFO', f"Skin             count: {len(skin_section.data) if skin_section else 0}")
        report('INFO', f"Polygon          count: {len(polygons_section.data) if polygons_section else 0}")
        report('INFO', f"Face             count: {len(facet_section.data) if facet_section else 0}")
        report('INFO', f"Materials        count: {len(materials_section.data) if materials_section else 0}")
        report('INFO', f"MaterialTextures count: {len(material_textures_section.data) if material_textures_section else 0}")
        report('INFO', f"MaterialParamPkg count: {len(material_parampkg_section.data) if material_parampkg_section else 0}")
        report('INFO', f"MaterialMaps     count: {len(material_maps_section.data) if material_maps_section else 0}")
    
        obj = create_mesh_from_matx2(
            mesh_section, vertices_section, polygons_section, facet_section, 
            filepath, normals_section, uvset_section, materials_section,
            hierarchy_section, skin_section, material_textures_section, 
            material_maps_section, sections
        )
    else:
        #MATX 1.0 [DEPRECATED]
        hierarchy_section         = sections.get('Hierarchy')
        vertices_section          = sections.get('Vertices')
        normals_section           = sections.get('Normals')
        colors_section            = sections.get('Colors')
        uvset_section             = sections.get('UVSet')
        skin_section              = sections.get('Skin')
        polygons_section          = sections.get('Polygons')
        facet_section             = sections.get('FacetIndex')
        textures_section          = sections.get('Textures')
        materials_section         = sections.get('Materials')       
        mattexture_section        = sections.get('MatTexture') 
        
        report('INFO', f"Hierarchy        count: {len(hierarchy_section.data) if hierarchy_section else 0}")
        report('INFO', f"Vertices         count: {len(vertices_section.data) if vertices_section else 0}")
        report('INFO', f"Normal           count: {len(normals_section.data) if normals_section else 0}")
        report('INFO', f"Color            count: {len(colors_section.data) if colors_section else 0}")
        report('INFO', f"UV               count: {len(uvset_section.data) if uvset_section else 0}")
        report('INFO', f"Skin             count: {len(skin_section.data) if skin_section else 0}")
        report('INFO', f"Polygon          count: {len(polygons_section.data) if polygons_section else 0}")
        report('INFO', f"Face             count: {len(facet_section.data) if facet_section else 0}")
        report('INFO', f"Textures         count: {len(textures_section.data) if textures_section else 0}")
        report('INFO', f"Materials        count: {len(materials_section.data) if materials_section else 0}")
        report('INFO', f"MatTexture       count: {len(mattexture_section.data) if mattexture_section else 0}")
        
        '''
        obj = create_mesh_from_matx(
                vertices_section, polygons_section, facet_section, 
                filepath, normals_section, uvset_section
            )
        '''   
        
        report('INFO', f"Unexpected dimension! MATX 1.0 is deprecated. Aborting!")
        return {'FINISHED'}
    
    report('INFO', f"MATX file import completed")
    return {'FINISHED'}
  
#=============================================================================
  
def create_mesh_from_matx2(mesh_section, vertices_section, polygons_section, facet_section, filepath, 
                           normals_section, uvset_section, materials_section,
                           hierarchy_section, skin_section, material_textures_section, 
                           material_maps_section, all_sections=None):
    
    root_name = os.path.basename(filepath).split('.')[0]
    root_obj = bpy.data.objects.new(root_name, None)
    bpy.context.collection.objects.link(root_obj)
    
    root_obj.rotation_mode = 'XYZ'
    root_obj.rotation_euler = (math.radians(90), 0, 0)
    
    global sections
    sections = all_sections if all_sections else {}
    material_dict = create_materials(materials_section, material_textures_section, filepath)
    
    armature_obj, bone_dict = create_armature(hierarchy_section, filepath, root_obj)
    
    vertex_dict = process_vertices(vertices_section)
    normal_dict = process_normals(normals_section)
    uv_dict = process_uvs(uvset_section)
    
    created_meshes = create_mesh_objects(mesh_section, root_obj, root_name)
    
    poly_material_dict = create_polygon_material_mapping(polygons_section)
    distribute_polygons_to_meshes(polygons_section, facet_section, created_meshes, root_obj, root_name)
    
    meshes_created = build_mesh_geometry(created_meshes, vertex_dict, uv_dict, normal_dict, 
                                       poly_material_dict, material_dict, bone_dict, 
                                       armature_obj, skin_section)
    
    report('INFO', f"Created {meshes_created} meshes")
    
    bpy.ops.object.select_all(action='DESELECT')
    root_obj.select_set(True)
    bpy.context.view_layer.objects.active = root_obj
    
    return root_obj

#=============================================================================

def create_materials(materials_section, material_textures_section, filepath):
    material_dict = {}
    if not (materials_section and materials_section.data):
        return material_dict
        
    report('INFO', f"Processing materials, quantity: {len(materials_section.data)}")
    
    texture_paths = {}
    
    if material_textures_section and material_textures_section.data:
        report('INFO', f"Processing Material_Textures, quantity: {len(material_textures_section.data)}")
        
        for tex_data in material_textures_section.data:
            try:
                if len(tex_data) >= 2:
                    tex_idx = int(tex_data[0])
                    tex_filename = str(tex_data[1]).strip('"')
                    texture_paths[tex_idx] = tex_filename
                    report('INFO', f"Loaded texture {tex_idx}: {tex_filename}")
            except Exception as e:
                report('WARNING', f"Error loading texture: {str(e)}, data: {tex_data}")
    
    for material_data in materials_section.data:
        try:
            if len(material_data) < 2:
                continue
            
            mat_idx = int(material_data[0])
            mat_name = str(material_data[1])
            
            if mat_name not in bpy.data.materials:
                blender_material = bpy.data.materials.new(name=mat_name)
            else:
                blender_material = bpy.data.materials[mat_name]
            
            material_dict[mat_idx] = blender_material
            report('INFO', f"Material {mat_idx}: {mat_name} created successfully")
        except Exception as e:
            report('WARNING', f"Error while creating material: {str(e)}")
    
    try:
        if 'Material_Maps' in sections:
            material_maps_section = sections['Material_Maps']
            
            for map_data in material_maps_section.data:
                if len(map_data) >= 5:
                    try:
                        mat_idx = int(map_data[1])
                        tex_idx = int(map_data[3])
                        
                        if mat_idx in material_dict and tex_idx in texture_paths:
                            blender_material = material_dict[mat_idx]
                            tex_path = texture_paths[tex_idx]
                            setup_material_nodes(blender_material, mat_idx, {mat_idx: tex_path}, filepath)
                            report('INFO', f"Texture is attached {tex_idx} to material {mat_idx}")
                    except Exception as e:
                        report('WARNING', f"Error attaching texture to material: {str(e)}")
    except Exception as e:
        report('WARNING', f"Error processing Material_Maps: {str(e)}")
    
    return material_dict

#=============================================================================

def setup_material_nodes(material, mat_idx, texture_paths, filepath):
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    
    nodes.clear()
    
    output_node = nodes.new('ShaderNodeOutputMaterial')
    output_node.location = (300, 0)
    
    principled_node = nodes.new('ShaderNodeBsdfPrincipled')
    principled_node.location = (0, 0)
    
    links.new(principled_node.outputs['BSDF'], output_node.inputs['Surface'])
    
    tex_path = None
    if mat_idx in texture_paths:
        tex_path = texture_paths[mat_idx]
    
    if tex_path:
        resolved_path = resolve_texture_path(tex_path, filepath)
        if resolved_path:
            add_texture_to_material(nodes, links, principled_node, resolved_path, material)
        else:
            report('WARNING', f"Texture {tex_path} not found")

#=============================================================================

def resolve_texture_path(tex_path, filepath):
    if os.path.exists(tex_path):
        return tex_path
            
    filename = os.path.basename(tex_path)
    base_dir = os.path.dirname(filepath)
    rel_path = os.path.join(base_dir, filename)
    
    if os.path.exists(rel_path):
        return rel_path
    
    for subfolder in ['textures', 'Textures', 'texture', 'Texture', 'resources']:
        test_path = os.path.join(base_dir, subfolder, filename)
        if os.path.exists(test_path):
            return test_path
    
    for root, dirs, files in os.walk(base_dir):
        if filename in files:
            return os.path.join(root, filename)
    
    return None

#=============================================================================

def add_texture_to_material(nodes, links, principled_node, texture_path, material):
    try:
        texture_node = nodes.new('ShaderNodeTexImage')
        texture_node.location = (-300, 0)
        
        if os.path.basename(texture_path) not in bpy.data.images:
            img = bpy.data.images.load(texture_path)
        else:
            img = bpy.data.images[os.path.basename(texture_path)]
        
        texture_node.image = img
        
        links.new(texture_node.outputs['Color'], principled_node.inputs['Base Color'])
        
        coords_node = nodes.new('ShaderNodeTexCoord')
        coords_node.location = (-600, 0)
        links.new(coords_node.outputs['UV'], texture_node.inputs['Vector'])
        
        report('INFO', f"Texture {os.path.basename(texture_path)} loaded successfully")
    except Exception as e:
        report('WARNING', f"Error loading texture {texture_path}: {str(e)}")

#=============================================================================

def create_armature(hierarchy_section, filepath, root_obj):
    armature_obj = None
    bone_dict = {}
    
    if not (hierarchy_section and hierarchy_section.data):
        return armature_obj, bone_dict
    
    report('INFO', f"Processing armature, quantity: {len(hierarchy_section.data)}")
    
    armature_name = os.path.basename(filepath).split('.')[0] + "_Armature"
    armature_data = bpy.data.armatures.new(armature_name)
    armature_obj = bpy.data.objects.new(armature_name, armature_data)
    bpy.context.collection.objects.link(armature_obj)
    armature_obj.parent = root_obj
    
    bpy.context.view_layer.objects.active = armature_obj
    bpy.ops.object.mode_set(mode='EDIT')
    
    edit_bones = {}
    
    hierarchy_data = []
    for bone_data in hierarchy_section.data:
        bone_idx = int(bone_data[0])
        bone_name = str(bone_data[1])
        parent_idx = int(bone_data[3])
        
        position = [0.0, 0.0, 0.0]
        rotation = [0.0, 0.0, 0.0, 1.0]
        scale = [1.0, 1.0, 1.0]
        
        if len(bone_data) > 4 and isinstance(bone_data[4], list) and len(bone_data[4]) >= 3:
            scale = [float(bone_data[4][i]) for i in range(3)]
        
        if len(bone_data) > 5 and isinstance(bone_data[5], list) and len(bone_data[5]) >= 4:
            rotation = [float(bone_data[5][i]) for i in range(4)]
        
        if len(bone_data) > 6 and isinstance(bone_data[6], list) and len(bone_data[6]) >= 3:
            position = [float(bone_data[6][i]) for i in range(3)]
        
        hierarchy_data.append({
            'Index': bone_idx,
            'Name': bone_name,
            'Parent': parent_idx,
            'Pos': position,
            'Rot': rotation,
            'Scale': scale
        })
        
        bone_dict[bone_idx] = {
            "name": bone_name,
            "parent_idx": parent_idx,
            "position": position,
            "rotation": rotation,
            "scale": scale
        }
    
    for bone_data in hierarchy_data:
        bone = armature_data.edit_bones.new(bone_data['Name'])
        bone.head = Vector((0, 0, 0))
        bone.tail = Vector((0, 0.1, 0))
        edit_bones[bone_data['Index']] = bone
    
    max_distance = 0.1
    for bone_data in hierarchy_data:
        parent_idx = bone_data['Parent']
        if parent_idx >= 0:
            parent_data = next((b for b in hierarchy_data if b['Index'] == parent_idx), None)
            if parent_data:
                pos1 = Vector((
                    bone_data['Pos'][0],
                    bone_data['Pos'][1],
                    bone_data['Pos'][2]
                ))
                pos2 = Vector((
                    parent_data['Pos'][0],
                    parent_data['Pos'][1],
                    parent_data['Pos'][2]
                ))
                distance = (pos1 - pos2).length
                max_distance = max(max_distance, distance)
    
    default_bone_length = max(0.1, max_distance * 0.2)
    
    for bone_data in hierarchy_data:
        bone = edit_bones[bone_data['Index']]
        
        pos = Vector((
            bone_data['Pos'][0],
            bone_data['Pos'][1],
            bone_data['Pos'][2]
        ))
        
        bone.head = pos
        
        direct_children = [b for b in hierarchy_data if b['Parent'] == bone_data['Index']]
        
        if direct_children:
            if len(direct_children) == 1:
                child_data = direct_children[0]
                child_pos = Vector((
                    child_data['Pos'][0],
                    child_data['Pos'][1],
                    child_data['Pos'][2]
                ))
                
                distance = (child_pos - pos).length
                if distance < 0.01:
                    direction = (child_pos - pos).normalized()
                    if direction.length < 0.001:
                        bone.tail = pos + Vector((0, default_bone_length, 0))
                    else:
                        bone.tail = pos + direction * default_bone_length
                else:
                    bone.tail = child_pos
            else:
                avg_direction = Vector((0, 0, 0))
                for child_data in direct_children:
                    child_pos = Vector((
                        child_data['Pos'][0],
                        child_data['Pos'][1],
                        child_data['Pos'][2]
                    ))
                    direction = (child_pos - pos)
                    if direction.length > 0.001:
                        avg_direction += direction.normalized()
                
                if avg_direction.length > 0.001:
                    avg_direction.normalize()
                    bone.tail = pos + avg_direction * default_bone_length
                else:
                    bone.tail = pos + Vector((0, default_bone_length, 0))
        else:
            bone.tail = pos + Vector((0, default_bone_length, 0))
    
    for bone_data in hierarchy_data:
        bone = edit_bones[bone_data['Index']]
        parent_idx = bone_data['Parent']
        
        if parent_idx >= 0 and parent_idx in edit_bones:
            parent_bone = edit_bones[parent_idx]
            bone.parent = parent_bone
            
            head_to_parent_tail_dist = (bone.head - parent_bone.tail).length
            if head_to_parent_tail_dist < 0.01:
                bone.use_connect = True
            else:
                child_bones = [b for b_data in hierarchy_data 
                              if b_data['Parent'] == parent_idx 
                              for b in [edit_bones[b_data['Index']]]]
                
                if len(child_bones) == 1:
                    parent_bone.tail = bone.head
                    bone.use_connect = True
    
    min_length = default_bone_length * 0.5
    for bone in armature_data.edit_bones:
        if (bone.tail - bone.head).length < min_length:
            direction = (bone.tail - bone.head).normalized()
            if direction.length < 0.001:
                bone.tail = bone.head + Vector((0, min_length, 0))
            else:
                bone.tail = bone.head + direction * min_length
    
    bpy.ops.object.mode_set(mode='OBJECT')
    
    return armature_obj, bone_dict

#=============================================================================

def process_vertices(vertices_section):
    vertex_dict = {}
    
    vert_pos_index = -1
    for i, field in enumerate(vertices_section.fields):
        if hasattr(field, 'name') and field.name == "Pos":
            vert_pos_index = i
            break
    
    if vert_pos_index == -1:
        return vertex_dict
    
    for i, vertex_data in enumerate(vertices_section.data):
        try:
            if isinstance(vertex_data[vert_pos_index], list) and len(vertex_data[vert_pos_index]) >= 3:
                x = float(vertex_data[vert_pos_index][0])
                y = float(vertex_data[vert_pos_index][1])
                z = float(vertex_data[vert_pos_index][2])
                vertex_dict[i] = (x, y, z)
        except Exception as e:
            report('WARNING', f"Error processing vertex {i}: {str(e)}")
    
    return vertex_dict

#=============================================================================

def process_normals(normals_section):
    normal_dict = {}
    
    if not (normals_section and normals_section.data):
        return normal_dict
    
    report('INFO', f"Processing normals, quantity: {len(normals_section.data)}")
    
    for normal_data in normals_section.data:
        try:
            vert_idx = int(normal_data[0])
            
            if len(normal_data) > 2 and isinstance(normal_data[2], list) and len(normal_data[2]) >= 3:
                nx = float(normal_data[2][0])
                ny = float(normal_data[2][1])
                nz = float(normal_data[2][2])
                
                length = math.sqrt(nx*nx + ny*ny + nz*nz)
                if length > 0:
                    nx, ny, nz = nx/length, ny/length, nz/length
                
                normal_dict[vert_idx] = (nx, ny, nz)
        except Exception as e:
            report('WARNING', f"Error processing vertex normal {vert_idx}: {str(e)}")
    
    return normal_dict

#=============================================================================

def process_uvs(uvset_section):
    uv_dict = {}
    
    if not (uvset_section and uvset_section.data):
        return uv_dict
    
    report('INFO', f"Processing UV coordinates, quantity: {len(uvset_section.data)}")
    
    sample_uv = uvset_section.data[0]
    has_nested_uv = (len(sample_uv) > 2 and isinstance(sample_uv[2], list) and len(sample_uv[2]) >= 2)  
    for uv_data in uvset_section.data:
        try:
            vert_idx = int(uv_data[0])
            
            if has_nested_uv:
                u = float(uv_data[2][0])
                v = float(uv_data[2][1])
                
                v = 1.0 - v
                
                uv_dict[vert_idx] = (u, v)
        except Exception as e:
            report('WARNING', f"Error processing UV for vertex {vert_idx}: {str(e)}")
    
    return uv_dict

#=============================================================================

def create_mesh_objects(mesh_section, root_obj, root_name):
    created_meshes = {}
    
    if mesh_section and mesh_section.data:
        for mesh_data in mesh_section.data:
            mesh_idx = int(mesh_data[0])
            mesh_name = str(mesh_data[1])
            report('INFO', f"Creating submesh {mesh_idx}: {mesh_name}")
            
            blender_mesh = bpy.data.meshes.new(mesh_name)
            mesh_obj = bpy.data.objects.new(mesh_name, blender_mesh)
            bpy.context.collection.objects.link(mesh_obj)
            
            mesh_obj.parent = root_obj
            
            created_meshes[mesh_idx] = {"obj": mesh_obj, "mesh": blender_mesh, "faces": []}
    
    if not created_meshes:
        mesh_name = root_name
        blender_mesh = bpy.data.meshes.new(mesh_name)
        mesh_obj = bpy.data.objects.new(mesh_name, blender_mesh)
        bpy.context.collection.objects.link(mesh_obj)
        mesh_obj.parent = root_obj
        created_meshes[0] = {"obj": mesh_obj, "mesh": blender_mesh, "faces": []}
    
    return created_meshes

#=============================================================================

def create_polygon_material_mapping(polygons_section):
    poly_material_dict = {}
    
    for poly_data in polygons_section.data:
        poly_idx = int(poly_data[1])
        if len(poly_data) > 4 and poly_data[4] is not None:
            mat_idx = int(poly_data[4])
            poly_material_dict[poly_idx] = mat_idx
    
    return poly_material_dict

#=============================================================================

def distribute_polygons_to_meshes(polygons_section, facet_section, created_meshes, root_obj, root_name):
    for poly_data in polygons_section.data:
        mesh_idx = int(poly_data[0])
        poly_idx = int(poly_data[1])
        
        if mesh_idx not in created_meshes:
            mesh_name = f"{root_name}_mesh_{mesh_idx}"
            blender_mesh = bpy.data.meshes.new(mesh_name)
            mesh_obj = bpy.data.objects.new(mesh_name, blender_mesh)
            bpy.context.collection.objects.link(mesh_obj)
            mesh_obj.parent = root_obj
            created_meshes[mesh_idx] = {"obj": mesh_obj, "mesh": blender_mesh, "faces": []}
        
        vert_indices = []
        for facet_data in facet_section.data:
            if facet_data[0] == poly_idx:
                vert_indices.append(int(facet_data[2]))
        
        if len(vert_indices) >= 3:
            created_meshes[mesh_idx]["faces"].append((poly_idx, vert_indices))

#=============================================================================

def apply_weights(mesh_obj, global_to_local_vert_map, skin_section, bone_dict, armature_obj):
    if not (armature_obj and skin_section and skin_section.data):
        return
    
    weight_dict = {}
    
    for skin_data in skin_section.data:
        try:
            global_vert_idx = int(skin_data[0])
            bone_idx = int(skin_data[2])
            weight = float(skin_data[3])
            
            if bone_idx in bone_dict and weight > 0:
                if global_vert_idx in global_to_local_vert_map:
                    if global_vert_idx not in weight_dict:
                        weight_dict[global_vert_idx] = []
                    
                    weight_dict[global_vert_idx].append({
                        "bone_name": bone_dict[bone_idx]["name"],
                        "weight": weight
                    })
        except Exception as e:
            report('WARNING', f"Error processing vertex weight {global_vert_idx}: {str(e)}")
    
    for global_vert_idx, weights in weight_dict.items():
        local_vert_idx = global_to_local_vert_map.get(global_vert_idx)
        if local_vert_idx is None:
            continue
        
        total_weight = sum(w["weight"] for w in weights)
        if total_weight > 0:
            for weight_info in weights:
                bone_name = weight_info["bone_name"]
                norm_weight = weight_info["weight"] / total_weight
                
                if bone_name not in mesh_obj.vertex_groups:
                    mesh_obj.vertex_groups.new(name=bone_name)
                
                vgroup = mesh_obj.vertex_groups[bone_name]
                vgroup.add([local_vert_idx], norm_weight, 'REPLACE')
    
    mod = mesh_obj.modifiers.new(name="Armature", type='ARMATURE')
    mod.object = armature_obj
    mod.use_vertex_groups = True
    
#=============================================================================    

def build_mesh_geometry(created_meshes, vertex_dict, uv_dict, normal_dict, 
                      poly_material_dict, material_dict, bone_dict, 
                      armature_obj, skin_section):
    meshes_created = 0
    
    all_weights = {}
    if armature_obj and skin_section and skin_section.data:
        for skin_data in skin_section.data:
            try:
                vert_idx = int(skin_data[0])
                bone_idx = int(skin_data[2])
                weight = float(skin_data[3])
                
                if bone_idx in bone_dict and weight > 0:
                    if vert_idx not in all_weights:
                        all_weights[vert_idx] = []
                    
                    all_weights[vert_idx].append({
                        "bone_name": bone_dict[bone_idx]["name"],
                        "weight": weight,
                        "bone_idx": bone_idx
                    })
            except Exception as e:
                report('WARNING', f"Error preparing vertex weight {vert_idx}: {str(e)}")
    
    for mesh_idx, mesh_info in created_meshes.items():
        if not mesh_info["faces"]:
            report('WARNING', f"Mesh {mesh_idx} does not contain polygons, skipping...")
            continue
        
        mesh_obj = mesh_info["obj"]
        blender_mesh = mesh_info["mesh"]
        faces_with_indices = mesh_info["faces"]
        
        unique_verts = set()
        for poly_idx, face in faces_with_indices:
            unique_verts.update(face)
        
        vert_map = {}
        vertices = []
        
        for idx, global_idx in enumerate(sorted(unique_verts)):
            if global_idx in vertex_dict:
                vertices.append(vertex_dict[global_idx])
                vert_map[global_idx] = idx
        
        reverse_vert_map = {v: k for k, v in vert_map.items()}
        
        final_faces = []
        poly_map = {}
        
        for poly_idx, face in faces_with_indices:
            local_face = [vert_map[idx] for idx in face if idx in vert_map]
            if len(local_face) >= 3:
                poly_map[len(final_faces)] = poly_idx
                final_faces.append(local_face)
        
        blender_mesh.from_pydata(vertices, [], final_faces)
        
        apply_materials(blender_mesh, poly_map, poly_material_dict, material_dict)
        
        apply_uvs(blender_mesh, uv_dict, reverse_vert_map)
        
        for poly in blender_mesh.polygons:
            poly.use_smooth = True
        
        apply_normals(blender_mesh, normal_dict, reverse_vert_map)
        
        if armature_obj:
            apply_weights_to_mesh(mesh_obj, reverse_vert_map, all_weights, armature_obj)
        
        blender_mesh.update()
        meshes_created += 1
    
    return meshes_created

#=============================================================================

def apply_weights_to_mesh(mesh_obj, global_to_local_vert_map, all_weights, armature_obj):
    if not (armature_obj and all_weights):
        return
    
    bone_vertex_groups = {}
    
    for local_vert_idx, global_vert_idx in global_to_local_vert_map.items():
        if global_vert_idx in all_weights:
            vertex_weights = all_weights[global_vert_idx]
            
            total_weight = sum(w["weight"] for w in vertex_weights)
            if total_weight > 0:
                for weight_info in vertex_weights:
                    bone_name = weight_info["bone_name"]
                    norm_weight = weight_info["weight"] / total_weight
                    
                    if bone_name not in bone_vertex_groups:
                        bone_vertex_groups[bone_name] = []
                    
                    bone_vertex_groups[bone_name].append((local_vert_idx, norm_weight))
    
    for bone_name, vertex_data in bone_vertex_groups.items():
        if vertex_data:
            if bone_name not in mesh_obj.vertex_groups:
                vgroup = mesh_obj.vertex_groups.new(name=bone_name)
            else:
                vgroup = mesh_obj.vertex_groups[bone_name]
            
            for vert_idx, weight in vertex_data:
                vgroup.add([vert_idx], weight, 'REPLACE')
    
    if mesh_obj.vertex_groups:
        mod = mesh_obj.modifiers.new(name="Armature", type='ARMATURE')
        mod.object = armature_obj
        mod.use_vertex_groups = True

#=============================================================================

def apply_materials(blender_mesh, poly_map, poly_material_dict, material_dict):
    if not material_dict:
        return
    
    used_materials = set()
    for blender_poly_idx, matx_poly_idx in poly_map.items():
        if matx_poly_idx in poly_material_dict:
            used_materials.add(poly_material_dict[matx_poly_idx])
    
    material_indices = {}
    
    for i, mat_idx in enumerate(sorted(used_materials)):
        if mat_idx in material_dict:
            blender_mesh.materials.append(material_dict[mat_idx])
            material_indices[mat_idx] = i
    
    for blender_poly_idx, matx_poly_idx in poly_map.items():
        if matx_poly_idx in poly_material_dict:
            mat_idx = poly_material_dict[matx_poly_idx]
            if mat_idx in material_indices and blender_poly_idx < len(blender_mesh.polygons):
                blender_mesh.polygons[blender_poly_idx].material_index = material_indices[mat_idx]

#=============================================================================

def apply_uvs(blender_mesh, uv_dict, reverse_vert_map):
    if not uv_dict:
        return
    
    blender_mesh.uv_layers.new(name="UVMap")
    uv_layer = blender_mesh.uv_layers[0].data
    
    for poly in blender_mesh.polygons:
        for loop_idx in range(poly.loop_start, poly.loop_start + poly.loop_total):
            loop = blender_mesh.loops[loop_idx]
            vert_idx = loop.vertex_index
            
            global_idx = reverse_vert_map.get(vert_idx)
            
            if global_idx is not None and global_idx in uv_dict:
                uv_layer[loop_idx].uv = uv_dict[global_idx]

#=============================================================================

def apply_normals(blender_mesh, normal_dict, reverse_vert_map):
    if not normal_dict:
        return
    
    report('INFO', "Applying custom normals")
    
    try:
        blender_mesh.update()

        if bpy.app.version >= (4, 1, 0):
            pass
        else:
            blender_mesh.use_auto_smooth = True
            blender_mesh.auto_smooth_angle = 3.14159
            blender_mesh.calc_normals_split()
          
        custom_normals = []
        
        for poly in blender_mesh.polygons:
            for loop_idx in range(poly.loop_start, poly.loop_start + poly.loop_total):
                loop = blender_mesh.loops[loop_idx]
                vert_idx = loop.vertex_index
                
                global_idx = reverse_vert_map.get(vert_idx)
                
                if global_idx is not None and global_idx in normal_dict:
                    nx, ny, nz = normal_dict[global_idx]
                    custom_normals.append((nx, ny, nz))
                else:
                    if bpy.app.version >= (4, 1, 0):
                        custom_normals.append(loop.normal[:])
                    else:
                        custom_normals.append(loop.normal[:])

        if custom_normals:
            blender_mesh.normals_split_custom_set(custom_normals)
        
        blender_mesh.validate(clean_customdata=False)
        blender_mesh.update()
        
    except Exception as e:
        report('WARNING', f"Error while setting custom normals: {str(e)}")

        if bpy.app.version < (4, 1, 0):
            blender_mesh.use_auto_smooth = False
        try:
            if hasattr(blender_mesh, 'free_normals_split'):
                blender_mesh.free_normals_split()
        except:
            pass