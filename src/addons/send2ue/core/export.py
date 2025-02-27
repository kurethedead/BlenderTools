# Copyright Epic Games, Inc. All Rights Reserved.

import json
import math
import os
import bpy, bpy_extras, mathutils
from . import utilities, validations, settings, ingest, extension, io
from ..constants import BlenderTypes, UnrealTypes, FileTypes, PreFixToken, ToolInfo, ExtensionTasks
from . import metadata

from .texture_constants import *

def get_file_path(asset_name, properties, asset_type, lod=False, file_extension='fbx'):
    """
    Gets the export path if it doesn't already exist.  Then it returns the full path.

    :param str asset_name: The name of the asset that will be exported to a file.
    :param PropertyData properties: A property data instance that contains all property values of the tool.
    :param str asset_type: The unreal type of data being exported.
    :param bool lod: Whether to use the lod post fix of not.
    :param str file_extension: The file extension in the file path.
    :return str: The full path to the file.
    """
    export_folder = utilities.get_export_folder_path(properties, asset_type)
    return os.path.join(
        export_folder,
        f'{utilities.get_asset_name(asset_name, properties, lod)}.{file_extension}'
    )


def export_lods(asset_id, asset_name, properties):
    """
    Exports the lod meshes and returns there file paths.

    :param str asset_id: The unique id of the asset.
    :param str asset_name: The name of the asset that will be exported to a file.
    :param PropertyData properties: A property data instance that contains all property values of the tool.
    :return list: A list of lod file paths.
    """
    lods = {}
    if properties.import_lods:
        mesh_objects = utilities.get_from_collection(BlenderTypes.MESH)
        for mesh_object in mesh_objects:
            if utilities.is_lod_of(asset_name, mesh_object.name, properties):
                if mesh_object.name != utilities.get_lod0_name(mesh_object.name, properties):
                    lod_index = utilities.get_lod_index(mesh_object.name, properties)
                    asset_type = utilities.get_mesh_unreal_type(mesh_object)
                    file_path = get_file_path(mesh_object.name, properties, asset_type, lod=True)
                    export_mesh(asset_id, mesh_object, properties, lod=lod_index)
                    if file_path:
                        lods[str(lod_index)] = file_path
        return lods


def set_parent_rig_selection(mesh_object, properties):
    """
    Recursively selects all parents of an object as long as the parent are in the rig collection.

    :param object mesh_object: A object of type mesh.
    :param object properties: The property group that contains variables that maintain the addon's correct state.
    :return object: A armature object.
    """
    rig_object = utilities.get_armature_modifier_rig_object(mesh_object) or mesh_object.parent

    # if the scene object has a parent
    if rig_object:

        # if the scene object's parent is in the rig collection
        if rig_object in utilities.get_from_collection(BlenderTypes.SKELETON):
            # select the parent object
            rig_object.select_set(True)

            # call the function again to see if this object has a parent that
            set_parent_rig_selection(rig_object, properties)
    return rig_object


def export_fbx_file(file_path, export_settings):
    """
    Exports a fbx file.

    :param str file_path: A file path where the file will be exported.
    :param dict export_settings: A dictionary of blender export settings for the specific file type.
    """
    major_version = bpy.app.version[0] # type: ignore
    
    if major_version <= 3:
        io.fbx_b3.export(
            filepath=file_path,
            use_selection=True,
            bake_anim_use_nla_strips=True,
            bake_anim_use_all_actions=False,
            object_types={'ARMATURE', 'MESH', 'EMPTY'},
            **export_settings
        )
    elif major_version >= 4:
        io.fbx_b4.export(
            filepath=file_path,
            use_selection=True,
            bake_anim_use_nla_strips=True,
            bake_anim_use_all_actions=False,
            object_types={'ARMATURE', 'MESH', 'EMPTY'},
            **export_settings
        )


def export_alembic_file(file_path, export_settings):
    """
    Exports an abc file.

    :param str file_path: A file path where the file will be exported.
    :param dict export_settings: A dictionary of blender export settings for the specific file type.
    """
    bpy.ops.wm.alembic_export(
        filepath=file_path,
        end=1,
        selected=True,
        visible_objects_only=True,
        export_hair=True,
        export_particles=False,
        evaluation_mode='RENDER',
        **export_settings
    )


def export_custom_property_fcurves(action_name, properties):
    """
    Exports custom property fcurves to a file.

    :param str action_name: The name of the action to export.
    :param object properties: The property group that contains variables that maintain the addon's correct state.
    """
    asset_id = bpy.context.window_manager.send2ue.asset_id
    file_path = bpy.context.window_manager.send2ue.asset_data[asset_id]['file_path']

    fcurve_file_path = None
    fcurve_data = utilities.get_custom_property_fcurve_data(action_name)
    if fcurve_data and properties.export_custom_property_fcurves:
        file_path, file_extension = os.path.splitext(file_path)
        fcurve_file_path = ToolInfo.FCURVE_FILE.value.format(file_path=file_path)
        if fcurve_data:
            with open(fcurve_file_path, 'w') as fcurves_file:
                json.dump(fcurve_data, fcurves_file)

    bpy.context.window_manager.send2ue.asset_data[asset_id]['fcurve_file_path'] = fcurve_file_path


def export_file(properties, lod=0, file_type=FileTypes.FBX):
    """
    Calls the blender export operator with specific settings.

    :param object properties: The property group that contains variables that maintain the addon's correct state.
    :param bool lod: Whether the exported mesh is a lod.
    :param str file_type: File type of the export.
    """
    asset_id = bpy.context.window_manager.send2ue.asset_id
    asset_data = bpy.context.window_manager.send2ue.asset_data[asset_id]

    # skip if specified
    if asset_data.get('skip'):
        return

    file_path = asset_data.get('file_path')
    if lod != 0:
        file_path = asset_data['lods'][str(lod)]

    # if the folder does not exist create it
    folder_path = os.path.abspath(os.path.join(file_path, os.pardir))
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    # get blender export settings
    export_settings = {}
    for group_name, group_data in settings.get_settings_by_path('blender-export_method', file_type).items():
        prefix = settings.get_generated_prefix(f'blender-export_method-{file_type}', group_name)
        for attribute_name in group_data.keys():
            export_settings[attribute_name] = settings.get_property_by_path(prefix, attribute_name, properties)

    metadata.assign_custom_metadata(properties)

    if file_type == FileTypes.FBX:
        export_fbx_file(file_path, export_settings)

    elif file_type == FileTypes.ABC:
        export_alembic_file(file_path, export_settings)
        
    metadata.delete_custom_metadata()


def get_asset_sockets(asset_name, properties):
    """
    Gets the socket under the given asset.

    :param str asset_name: The name of the asset to export.
    :param object properties: The property group that contains variables that maintain the addon's correct state.
    """
    socket_data = {}
    mesh_object = bpy.data.objects.get(asset_name)
    if mesh_object:
        for child in mesh_object.children:
            if child.type == 'EMPTY' and child.name.startswith(f'{PreFixToken.SOCKET.value}_'):
                name = utilities.get_asset_name(child.name.replace(f'{PreFixToken.SOCKET.value}_', '').split('.',1)[0], properties)
                relative_location = utilities.convert_blender_to_unreal_location(
                    child.matrix_local.translation
                )
                relative_rotation = utilities.convert_blender_rotation_to_unreal_rotation(
                    child.rotation_euler
                )
                socket_data[name] = {
                    'relative_location': relative_location,
                    'relative_rotation': relative_rotation,
                    'relative_scale': child.matrix_local.to_scale()[:]
                }
    return socket_data


@utilities.track_progress(message='Exporting mesh "{attribute}"...', attribute='file_path')
def export_mesh(asset_id, mesh_object, properties, lod=0):
    """
    Exports a mesh to a file.

    :param str asset_id: The unique id of the asset.
    :param object mesh_object: A object of type mesh.
    :param object properties: The property group that contains variables that maintain the addon's correct state.
    :param bool lod: Whether the exported mesh is a lod.
    """
    # deselect everything
    utilities.deselect_all_objects()

    # run the pre mesh export extensions
    if lod == 0:
        extension.run_extension_tasks(ExtensionTasks.PRE_MESH_EXPORT.value)

    # select the scene object
    mesh_object.select_set(True)

    # select any rigs this object is parented too
    set_parent_rig_selection(mesh_object, properties)

    # select collision meshes
    asset_name = utilities.get_asset_name(mesh_object.name, properties)
    utilities.select_asset_collisions(asset_name, properties)

    # Note: this is a weird work around for morph targets not exporting when
    # particle systems are on the mesh. Making them not visible fixes this bug
    existing_display_options = utilities.disable_particles(mesh_object)
    # export selection to a file
    export_file(properties, lod)
    # restore the particle system display options
    utilities.restore_particles(mesh_object, existing_display_options)

    # run the post mesh export extensions
    if lod == 0:
        extension.run_extension_tasks(ExtensionTasks.POST_MESH_EXPORT.value)


@utilities.track_progress(message='Exporting animation "{attribute}"...', attribute='file_path')
def export_animation(asset_id, rig_object, action_name, properties):
    """
    Exports a single action from a rig object to a file.

    :param str asset_id: The unique id of the asset.
    :param object rig_object: A object of type armature with animation data.
    :param str action_name: The name of the action to export.
    :param object properties: The property group that contains variables that maintain the addon's correct state.
    """
    # run the pre animation export extensions
    extension.run_extension_tasks(ExtensionTasks.PRE_ANIMATION_EXPORT.value)

    if rig_object.animation_data:
        rig_object.animation_data.action = None

    # deselect everything
    utilities.deselect_all_objects()

    # select the scene object
    rig_object.select_set(True)

    # un-mute the action
    utilities.set_action_mute_value(rig_object, action_name, False)

    # export the action
    export_file(properties)

    # export custom property fcurves
    export_custom_property_fcurves(action_name, properties)

    # ensure the rigs are in rest position before setting the mute values
    utilities.clear_pose(rig_object)

    # mute the action
    utilities.set_action_mute_value(rig_object, action_name, True)

    # run the post animation export extensions
    extension.run_extension_tasks(ExtensionTasks.POST_ANIMATION_EXPORT.value)


@utilities.track_progress(message='Exporting curves/hair particle system "{attribute}"...', attribute='file_path')
def export_hair(asset_id, properties):
    """
    Exports a mesh to a file.

    :param str asset_id: The unique id of the asset.
    :param object properties: The property group that contains variables that maintain the addon's correct state.
    """
    asset_data = bpy.context.window_manager.send2ue.asset_data[asset_id]

    # deselect everything
    utilities.deselect_all_objects()

    # clear animation transformations prior to export so groom exports with no distortion
    for scene_object in bpy.context.scene.objects:
        if scene_object.animation_data:
            if scene_object.animation_data.action:
                scene_object.animation_data.action = None
        utilities.set_all_action_mute_values(scene_object, mute=True)
        if scene_object.type == BlenderTypes.SKELETON:
            utilities.clear_pose(scene_object)

    object_type = asset_data.get('_object_type')
    object_name = asset_data.get('_object_name')

    mesh_object = utilities.get_mesh_object_for_groom_name(object_name)

    # get all particle systems display options on all mesh objects
    all_existing_display_options = utilities.get_all_particles_display_options()

    if object_type == BlenderTypes.CURVES:
        curves_object = bpy.data.objects.get(object_name)
        utilities.convert_curve_to_particle_system(curves_object)

    # turn show_emitter off in particle system render settings
    mesh_object.show_instancer_for_render = False

    # display only the particle to export
    utilities.set_particles_display_option(mesh_object, False)
    utilities.set_particles_display_option(mesh_object, True, only=object_name)

    # select the mesh to export
    mesh_object.select_set(True)

    # run the pre groom export extensions
    extension.run_extension_tasks(ExtensionTasks.PRE_GROOM_EXPORT.value)

    # export the abc file
    export_file(properties, file_type=FileTypes.ABC)

    # restore all the display options on all objects
    utilities.restore_all_particles(all_existing_display_options)

    # run the pre groom export extensions
    extension.run_extension_tasks(ExtensionTasks.POST_GROOM_EXPORT.value)


def create_animation_data(rig_objects, properties):
    """
    Collects and creates all the action data needed for an animation import.

    :param list rig_objects: A list of rig objects.
    :param object properties: The property group that contains variables that maintain the addon's correct state.
    :return list: A list of dictionaries containing the action import data.
    """
    animation_data = {}

    if properties.import_animations:
        # get the asset data for the skeletal animations
        for rig_object in rig_objects:

            # if auto stash active action option is on
            if properties.auto_stash_active_action:
                # stash the active animation data in the rig object's nla strips
                utilities.stash_animation_data(rig_object)

            # get the names of all the actions to export
            action_names = utilities.get_action_names(rig_object, all_actions=properties.export_all_actions)

            # mute all actions
            utilities.set_all_action_mute_values(rig_object, mute=True)

            # export the actions and create the action import data
            for action_name in action_names:
                file_path = get_file_path(action_name, properties, UnrealTypes.ANIM_SEQUENCE)
                asset_name = utilities.get_asset_name(action_name, properties)

                # export the animation
                asset_id = utilities.get_asset_id(file_path)
                export_animation(asset_id, rig_object, action_name, properties)

                # save the import data
                asset_id = utilities.get_asset_id(file_path)
                animation_data[asset_id] = {
                    '_asset_type': UnrealTypes.ANIM_SEQUENCE,
                    '_action_name': action_name,
                    '_armature_object_name': rig_object.name,
                    'file_path': file_path,
                    'asset_path': f'{properties.unreal_animation_folder_path}{asset_name}',
                    'asset_folder': properties.unreal_animation_folder_path,
                    'skeleton_asset_path': utilities.get_skeleton_asset_path(rig_object, properties),
                    'skip': False
                }

    return animation_data


def create_mesh_data(mesh_objects, rig_objects, properties):
    """
    Collects and creates all the asset data needed for the import process.

    :param list mesh_objects: A list of mesh objects.
    :param list rig_objects: A list of rig objects.
    :param object properties: The property group that contains variables that maintain the addon's correct state.
    :return list: A list of dictionaries containing the mesh import data.
    """
    mesh_data = {}
    if not properties.import_meshes:
        return mesh_data

    previous_asset_names = []

    # get the asset data for the scene objects
    for mesh_object in mesh_objects:
        already_exported = False
        asset_name = utilities.get_asset_name(mesh_object.name, properties)

        # only export meshes that are lod 0
        if properties.import_lods and utilities.get_lod_index(mesh_object.name, properties) != 0:
            continue

        # TODO: don't think this block is needed, how would the code ever reach this block since all LODs except LOD0 are skipped?
        # check each previous asset name for its lod mesh
        for previous_asset in previous_asset_names:
            if utilities.is_lod_of(previous_asset, mesh_object.name, properties):
                already_exported = True
                break

        if not already_exported:
            asset_type = utilities.get_mesh_unreal_type(mesh_object)
            # get file path
            file_path = get_file_path(mesh_object.name, properties, asset_type, lod=False)
            # export the object
            asset_id = utilities.get_asset_id(file_path)
            export_mesh(asset_id, mesh_object, properties)
            import_path = utilities.get_import_path(properties, asset_type)

            # save the asset data
            mesh_data[asset_id] = {
                '_asset_type': asset_type,
                '_mesh_object_name': mesh_object.name,
                'file_path': file_path,
                'asset_folder': import_path,
                'asset_path': f'{import_path}{asset_name}',
                'skeleton_asset_path': properties.unreal_skeleton_asset_path,
                'lods': export_lods(asset_id, asset_name, properties),
                'sockets': get_asset_sockets(mesh_object.name, properties),
                'skip': False
            }
            previous_asset_names.append(asset_name)

    return mesh_data


def create_groom_data(hair_objects, properties):
    """
    Collects and creates all the asset data needed for the import process.

    :param list hair_objects: A list of hair objects that can be either curve objects or particle systems.
    :param object properties: The property group that contains variables that maintain the addon's correct state.
    :return list: A list of dictionaries containing the groom import data.
    """

    groom_data = {}
    if properties.import_grooms:
        for hair_object in hair_objects:
            if type(hair_object) == bpy.types.Object:
                object_type = hair_object.type
                particle_object_name = None
            else:
                # the object type is set to the particle object rather then the particle system
                object_type = hair_object.settings.type
                particle_object_name = hair_object.settings.name

            file_path = get_file_path(
                hair_object.name,
                properties,
                UnrealTypes.GROOM,
                lod=False,
                file_extension='abc'
            )
            asset_id = utilities.get_asset_id(file_path)
            import_path = utilities.get_import_path(properties, UnrealTypes.GROOM)
            asset_name = utilities.get_asset_name(hair_object.name, properties)

            groom_data[asset_id] = {
                '_asset_type': UnrealTypes.GROOM,
                '_object_name': hair_object.name,
                '_particle_object_name': particle_object_name,
                '_object_type': object_type,
                'file_path': file_path,
                'asset_folder': import_path,
                'asset_path': f'{import_path}{asset_name}',
                'skip': False
            }
            # export particle hair systems as alembic file
            export_hair(asset_id, properties)

    return groom_data

def remove_image_ext(name : str) -> str:
    for ext in list(IMAGE_EXTENSIONS.values()):
        if name.endswith(f".{ext}"):
            return name[:-(len(ext) + 1)]
    return name

def get_image_ext(ext_enum : str) -> str:
    if ext_enum in IMAGE_EXTENSIONS:
        return IMAGE_EXTENSIONS[ext_enum]
    else:
        return ext_enum

def create_texture_data(mesh_objects, mesh_asset_data, properties):
    """
    Collects and creates all the asset data needed for the import process.
    This uses a specialized setup that handles Ucupaint baked images, node wrangler nodes, and explicitly prefixed nodes.

    :param list mesh_objects: A list of mesh objects.
    :param object properties: The property group that contains variables that maintain the addon's correct state.
    :return list: A list of dictionaries containing the texture import data.
    """
    texture_prefix = metadata.get_texture_affix(properties)
    
    texture_data = {}
    if not properties.import_materials_and_textures:
        return texture_data

    previous_asset_names = []
    all_images_file_paths = []

    # get the asset data for the scene objects
    for mesh_object in mesh_objects:
        asset_type = utilities.get_mesh_unreal_type(mesh_object)
        directory = utilities.get_export_folder_path(properties, asset_type)
        already_exported = False
        asset_name = utilities.get_asset_name(mesh_object.name, properties)
        # get mesh file path - used so asset_id corresponds to mesh
        file_path = get_file_path(mesh_object.name, properties, asset_type, lod=False)
        # export the object
        asset_id = utilities.get_asset_id(file_path)
        import_path = utilities.get_import_path(properties, asset_type)
        
        materials = []
        images_file_paths = []
        
        # only export meshes that are lod 0
        if properties.import_lods and utilities.get_lod_index(mesh_object.name, properties) != 0:
            continue

        # TODO: don't think this block is needed, how would the code ever reach this block since all LODs except LOD0 are skipped?
        # check each previous asset name for its lod mesh
        for previous_asset in previous_asset_names:
            if utilities.is_lod_of(previous_asset, mesh_object.name, properties):
                already_exported = True
                break

        if not already_exported:
            # When combine meshes is enabled, only one mesh per parent empty is processed,
            # and the rest are filtered out before we get to this point.
            # Therefore we always gather textures as if combine mesh is enabled,
            # then in ingest.import_asset() we filter out repeat textures to avoid multiple imports.
            objects_to_process = [mesh_object]
            if mesh_object.parent and mesh_object.parent.type in ["EMPTY", "ARMATURE"]:
                objects_to_process = [obj for obj in mesh_object.parent.children_recursive if obj.type == "MESH"]

            for obj in objects_to_process:
                for i in range(len(obj.material_slots)):
                    material = obj.material_slots[i].material
                    if material not in materials:
                        materials.append(material)
                        for node in material.node_tree.nodes:

                            # Handle Ucupaint group nodes
                            if node.type == "GROUP" and node.node_tree.name.find("Ucupaint") >= 0 and node.node_tree.yp.use_baked:          
                                image_dict = get_baked_images(node.node_tree)

                                # Save baked images
                                for channel, image in image_dict.items():
                                    if channel in UCUPAINT_IGNORE_BAKED:
                                        continue
                                    image_name = image.name
                                    if image_name.startswith(f"{UCUPAINT_TITLE} "):
                                        image_name = image_name[len(f"{UCUPAINT_TITLE} "):]
                                    fmt = get_image_ext(image.file_format)
                                    # Remove image extension beforehand, since we dont know if name contains extension or not
                                    filepath = f"{directory}\\{texture_prefix}{remove_image_ext(image_name)}.{fmt}"
                                    if filepath not in all_images_file_paths:
                                        image.save(filepath = filepath)
                                        all_images_file_paths.append(filepath)
                                    images_file_paths.append(filepath)

                            # Handle node wrangler or prefixed image nodes               
                            if node.type == "TEX_IMAGE":
                                if node.image and node.label in NODE_WRANGLER_TEXTURES or node.label.find(INPUT_PREFIX) == 0:
                                    #channel = node.label if node.label in NODE_WRANGLER_TEXTURES else node.label[len(INPUT_PREFIX):]
                                    fmt = get_image_ext(node.image.file_format)
                                    # Remove image extension beforehand, since we dont know if name contains extension or not
                                    filepath = f"{directory}\\{texture_prefix}{remove_image_ext(node.image.name)}.{fmt}"
                                    if filepath not in all_images_file_paths:
                                        node.image.save(filepath = filepath)
                                        all_images_file_paths.append(filepath)
                                    #node.image.save(filepath = f"{directory}\\{material.name}_{channel}.{fmt}")
                                    images_file_paths.append(filepath)

            # save the asset data
            mesh_asset_data[asset_id] = mesh_asset_data[asset_id] | {
                'images_file_paths': images_file_paths,
                'image_asset_folder': import_path,
                'skip': False
            }
            previous_asset_names.append(asset_name)

def get_baked_images(node_tree : bpy.types.NodeTree) -> dict[str, bpy.types.Image]:
    image_dict = {}
    for node in node_tree.nodes:
        if node.type == "TEX_IMAGE" and node.label[:len("Baked ")] == "Baked " and node.image:
            image_dict[node.label[len("Baked "):]] = node.image
    return image_dict
    
def get_other_images(node_tree : bpy.types.NodeTree) -> dict[str, bpy.types.Image]:
    image_dict = {}
    for node in node_tree.nodes:
        if node.type == "TEX_IMAGE" and node.image:
            if node.label in NODE_WRANGLER_TEXTURES:
                image_dict[node.label] = node.image
            elif node.label.find(INPUT_PREFIX) == 0:
                image_dict[node.label[len(INPUT_PREFIX):]] = node.image
    return image_dict

def create_transform_track() -> dict[str, list]:
    return {
        "location_x" : [],
        "location_y" : [],
        "location_z" : [],
        "rotation_x" : [],
        "rotation_y" : [],
        "rotation_z" : [],
        "scale_x" : [],
        "scale_y" : [],
        "scale_z" : [],
        "hide" : [],
    }

def read_transform_frames(track : dict[str, list], frame : int, obj : "bpy.types.Object", scene_scale : float, rotation_offset : list, location_offset : list, is_camera : bool = False):
    mm = mathutils.Matrix.Identity(4)
    mm[1][1] = -1 # handle left vs right hand space
    
    offset_mat = mathutils.Matrix.Translation((-location_offset[0] / (scene_scale * 100), -location_offset[1] / (scene_scale * 100), -location_offset[2] / (scene_scale * 100)))
    loc, rot, scale = (mm @ obj.matrix_world @ offset_mat @ mm.inverted()).decompose()
    
    rot = rot @ mathutils.Euler((-rotation_offset[0], -rotation_offset[1], -rotation_offset[2]), 'XYZ').to_quaternion()
    hide = not obj.hide_viewport
    
    track["location_x"].append((frame, loc[0] * 100 * scene_scale)) # handle unreal-blender unit scale
    track["location_y"].append((frame, loc[1] * 100 * scene_scale))
    track["location_z"].append((frame, loc[2] * 100 * scene_scale))
    track["rotation_x"].append((frame, math.degrees(rot.to_euler()[0]) + 90 if is_camera else -math.degrees(rot.to_euler()[0]))) # handle different camera orientation
    track["rotation_y"].append((frame, math.degrees(rot.to_euler()[1]) if is_camera else -math.degrees(rot.to_euler()[1])))
    track["rotation_z"].append((frame, math.degrees(rot.to_euler()[2]) - (90 if is_camera else 0)))
    track["scale_x"].append((frame, scale[0]))
    track["scale_y"].append((frame, scale[1]))
    track["scale_z"].append((frame, scale[2]))
    track["hide"].append((frame, hide))

def create_level_sequence_data_cameras(scene, properties, start_frame, end_frame) -> dict[str,dict[str, list]]:
    camera_objs : dict [bpy.types.Object, tuple[float, float]] = {} # camera object to frame range
    camera_markers = [m for m in scene.timeline_markers if m.camera is not None]
    for i, marker in enumerate(camera_markers):
        if i == 0:
            camera_start_frame = start_frame
        else:
            camera_start_frame = camera_markers[i].frame
        
        if i == len(camera_markers) - 1:
            camera_end_frame = end_frame
        else:
            camera_end_frame = camera_markers[i + 1].frame
        camera_objs[marker.camera] = (camera_start_frame, camera_end_frame)
    
    # evaluate transform each frame
    #anim_camera_objs = [obj for obj in camera_objs if obj.animation_data is not None]
    #static_camera_objs = [obj for obj in camera_objs if obj.animation_data is None]
    transform_tracks : dict[str, object] = {}
    for camera_obj, frame_range in camera_objs.items():
        transform_tracks[camera_obj.name] = create_transform_track() | {
            "frame_range" : frame_range,
            "fov" : [],
            
        }
    for i in range(start_frame, end_frame):
        scene.frame_set(i)
        for camera_obj, frame_range in camera_objs.items():
            track = transform_tracks[camera_obj.name]
            fov = math.degrees(camera_obj.data.angle)
            
            read_transform_frames(track, i, camera_obj, properties.sequencer_scene_scale, mathutils.Vector([0,0,0]), mathutils.Vector([0,0,0]), True)
            track["fov"].append((i, fov))
    
    return transform_tracks

def create_level_sequence_data_anims(scene, rig_objects, properties, start_frame, end_frame) -> list[dict]:
    # null actions on objects, so only NLA influence is evaluated
    for obj in rig_objects:
        if obj.animation_data and obj.animation_data.action:
            obj.animation_data.action.use_fake_user = True # TODO: Should we do this?
            obj.animation_data.action = None

    anim_tracks = []
    for rig_object in [obj for obj in rig_objects if obj]:
        transform_track_saved = False
        if rig_object.send2ue_armature.actor_prop.get_path() == "":
            print(f"{rig_object.name} does not have an actor path set for its appropriate mode, skipping.")
            continue
        num_tracks = len(rig_object.animation_data.nla_tracks)
        if rig_object.animation_data and num_tracks > 0:
            nla_track = None
            solo_tracks = [i for i in rig_object.animation_data.nla_tracks if i.is_solo]
            if len(solo_tracks) > 0:
                nla_track = solo_tracks[0]
            else:
                for i in range(num_tracks):
                    nla_track = rig_object.animation_data.nla_tracks[-(i+1)]
                    if not nla_track.mute:
                        break
            if nla_track:
                for strip in nla_track.strips:
                    if strip.action and utilities.is_armature_action(strip.action):
                        action_name = strip.action.name
                        anim_asset_name = utilities.get_asset_name(action_name, properties)
                        
                        # We assume linked actions are already exported using their rig object's anim asset path
                        # Otherwise, we save all sequence specific actions to global path found in the scene property
                        if strip.action.library is not None:
                            anim_asset_folder = rig_object.send2ue_armature.anim_asset_path.strip()
                            if anim_asset_folder == "":
                                raise Exception(f"{rig_object.name} must have a defined anim_asset_path if linked actions are used in its NLA track.")
                            anim_asset_path = f'{anim_asset_folder}{anim_asset_name}'
                        else:
                            anim_asset_path = f'{properties.unreal_animation_folder_path}{anim_asset_name}'
                        strip_prop = strip.action.send2ue_strip
                        
                        if not transform_track_saved and rig_object.send2ue_armature.actor_prop.export_transforms:
                            transform_track_saved = True
                            utilities.set_all_action_mute_values(rig_object, mute=False) # un-mute actions since animation export mutes them
                            transform_track = create_transform_track()
                            for i in range(start_frame, end_frame):
                                bpy.context.scene.frame_set(i)
                                read_transform_frames(transform_track, i, rig_object, properties.sequencer_scene_scale, 
                                                      rig_object.send2ue_armature.actor_prop.rotation_offset,
                                                      rig_object.send2ue_armature.actor_prop.location_offset)
                            utilities.set_all_action_mute_values(rig_object, mute=True)
                        else:
                            transform_track = None
                        
                        anim_tracks.append({
                            "type" : "Animation",
                            "frame_range" : (strip.frame_start, strip.frame_end),
                            "anim_asset_path" : anim_asset_path,
                            "skeleton_asset_path" : rig_object.send2ue_armature.skeleton_asset_path,
                            "actor_path" : rig_object.send2ue_armature.actor_prop.get_path(),
                            "actor_category" : rig_object.send2ue_armature.actor_prop.actor_category,
                            "force_custom_mode" : strip_prop.force_custom_mode,
                            "play_rate" : strip_prop.play_rate,
                            "reverse" : strip_prop.reverse,
                            "skip_anim_notifiers" : strip_prop.skip_anim_notifiers,
                            "slot_name" : strip_prop.slot_name,
                            "completion_mode" : strip_prop.completion_mode,
                            "transform_track" : transform_track,
                        })
    return anim_tracks

def create_level_sequence_data_objects(scene, mesh_objects, properties, start_frame, end_frame) -> dict[str,dict[str, list]]:
    obj_transform_tracks = {}
    for i in range(start_frame, end_frame):
        scene.frame_set(i)
        for mesh_object in [obj for obj in mesh_objects if obj.send2ue_object.actor_prop.export_transforms]:
            if mesh_object.name not in obj_transform_tracks:
                transform_track = create_transform_track() | {
                    "actor_path" : mesh_object.send2ue_object.actor_prop.get_path(),
                    "actor_category" : mesh_object.send2ue_object.actor_prop.actor_category,
                }
                obj_transform_tracks[mesh_object.name] = transform_track
            utilities.set_all_action_mute_values(mesh_object, mute=False) # un-mute actions since animation export mutes them
            read_transform_frames(obj_transform_tracks[mesh_object.name], i, mesh_object, properties.sequencer_scene_scale, 
                                  mesh_object.send2ue_object.actor_prop.rotation_offset,
                                  mesh_object.send2ue_object.actor_prop.location_offset)
            utilities.set_all_action_mute_values(mesh_object, mute=True)
    return obj_transform_tracks

def create_level_sequence_data(rig_objects, mesh_objects, properties):
    """
    Collects and creates all the asset data needed for the import process.
    
    Importer Quirks:
        - Marker Naming
            - markers with an empty name will be ignored for marker import, but not for camera shot import
        - linked objects must be made fully local, or else:
            - actor/skeletal path properties on object won't be saved
            - NLA tracks/strips can't be editted
        - Note that linked actions are assumed to already by exported using their rig_object's anim_asset_path.
        - Make sure linked animations have the same framerate as the sequence, otherwise ranges will be incorrect in unreal.
        - Make sure NLA track is not in edit mode, otherwise export fails.
        
    Note that all NLA tracks are muted during export (each unmuted one at a time), and active actions are pushed to track beforehand.

    :param list rig_objects: A list of rig objects.
    :param object properties: The property group that contains variables that maintain the addon's correct state.
    :return list: A list of dictionaries containing the texture import data.
    """
    sequence_data = {}
    
    # save the import data
    sequence_name = bpy.path.basename(bpy.context.blend_data.filepath)[:-6] # remove .blend extension
    asset_name = utilities.get_asset_name(sequence_name, properties)
    #asset_id = utilities.get_asset_id(file_path)
    asset_id = "LevelSequenceID" # since there is only one level sequence per export, this should be okay
    
    # basic params
    scene = bpy.context.scene
    start_frame = scene.frame_start
    end_frame = scene.frame_end
    framerate = scene.render.fps
    
    # get markers used for dialog system stopping points
    markers = []
    for marker in scene.timeline_markers:
        # Ignore any empty names (we do this to handle camera cut markers)
        if marker.name.strip() == "":
            continue
        markers.append({"name" : marker.name, "frame" : marker.frame})
        
    # get camera tracks
    cam_tracks = create_level_sequence_data_cameras(scene, properties, start_frame, end_frame)
    
    # get armature animation tracks
    anim_tracks = create_level_sequence_data_anims(scene, rig_objects, properties, start_frame, end_frame)

    # get object animation tracks
    obj_transform_tracks = create_level_sequence_data_objects(scene, mesh_objects, properties, start_frame, end_frame)

    sequence_data[asset_id] = {
        '_asset_type': UnrealTypes.LEVEL_SEQUENCE,
        'sequence_name': asset_name,
        'asset_path': f'{properties.unreal_level_sequence_folder_path}{asset_name}',
        'asset_folder': properties.unreal_level_sequence_folder_path,
        'skip': False,
        'start_frame': start_frame,
        'end_frame': end_frame,
        'framerate': framerate,
        'markers' : markers,
        'cam_tracks' : cam_tracks,
        'anim_tracks' : anim_tracks,
        'obj_tracks' : obj_transform_tracks,
        'subsequence_path' : properties.unreal_subsequence_asset_path,
    }
    #print(str(sequence_data[asset_id]))
    return sequence_data

def create_asset_data(properties):
    """
    Collects and creates all the asset data needed for the import process.

    :param object properties: The property group that contains variables that maintain the addon's correct state.
    """
    # get the mesh and rig objects from their collections
    mesh_objects = utilities.get_from_collection(BlenderTypes.MESH)
    rig_objects = utilities.get_from_collection(BlenderTypes.SKELETON)
    hair_objects = utilities.get_hair_objects(properties)

    # filter the rigs and meshes based on the extension filter methods
    rig_objects, mesh_objects, hair_objects = extension.run_extension_filters(
        rig_objects,
        mesh_objects,
        hair_objects
    )

    # get the asset data for all the mesh objects
    mesh_data = create_mesh_data(mesh_objects, rig_objects, properties)

    # get the asset data for all the actions on the rig objects
    animation_data = create_animation_data(rig_objects, properties)

    # get the asset data for all the hair systems
    hair_data = create_groom_data(hair_objects, properties)
    
    # get all textures, merge asset data into mesh asset data
    create_texture_data(mesh_objects, mesh_data, properties)
    
    # get level sequence data
    level_sequence_data = create_level_sequence_data(rig_objects, mesh_objects, properties)

    # update the properties with the asset data
    bpy.context.window_manager.send2ue.asset_data.update({**mesh_data, **animation_data, **hair_data, **level_sequence_data})


def send2ue(properties):
    """
    Sends assets to unreal.

    :param object properties: The property group that contains variables that maintain the addon's correct state.
    """
    # get out of local view
    utilities.escape_local_view()

    # clear the asset_data and current id
    bpy.context.window_manager.send2ue.asset_id = ''
    bpy.context.window_manager.send2ue.asset_data.clear()

    # if there are no failed validations continue
    validation_manager = validations.ValidationManager(properties)
    if validation_manager.run():
        # create the asset data
        create_asset_data(properties)
        ingest.assets(properties)
