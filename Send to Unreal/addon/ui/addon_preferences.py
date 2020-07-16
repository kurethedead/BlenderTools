# Copyright Epic Games, Inc. All Rights Reserved.

import bpy
from ..properties import Send2UeProperties, Send2UeUIProperties


class SendToUnrealPreferences(Send2UeProperties, Send2UeUIProperties, bpy.types.AddonPreferences):
    """
    This class creates the settings interface in the send to unreal addon.
    """
    bl_idname = __package__.split('.')[0]

    def draw(self, context):
        """
        This defines the draw method, which is in all Blender UI types that create interfaces.
        :param context: The context of this interface.
        """
        layout = self.layout

        # basic or advanced menu
        row = layout.row()
        row.prop(self, 'always_use_unreal_scene_scale')

        row = layout.row()
        row.prop(self, 'options_type', expand=True)

        if self.options_type == 'paths':
            row = layout.row()
            row.prop(self, 'path_mode', text='')
            if self.path_mode in ['send_to_unreal', 'both']:
                row = layout.row()
                row.label(text='Mesh Folder (Unreal)')

                # disable the mesh folder path input if a skeleton path is provided
                row = layout.row()
                row.enabled = not bool(self.unreal_skeleton_asset_path)
                row.prop(self, 'unreal_mesh_folder_path', text='')
                row = layout.row()
                row.label(text='Animation Folder (Unreal)')
                row = layout.row()
                row.prop(self, 'unreal_animation_folder_path', text='')
                row = layout.row()
                row.label(text='Skeleton Asset (Unreal)')
                row = layout.row()
                row.prop(self, 'unreal_skeleton_asset_path', text='')

            if self.path_mode in ['export_to_disk', 'both']:
                row = layout.row()
                row.label(text='Mesh Folder (Disk)')

                # disable the mesh folder path input if a skeleton path is provided
                row.enabled = not bool(self.unreal_skeleton_asset_path)
                row = layout.row()
                row.alert = self.incorrect_disk_mesh_folder_path
                row.prop(self, 'disk_mesh_folder_path', text='')
                row = layout.row()
                row.label(text='Animation Folder (Disk)')
                row = layout.row()
                row.alert = self.incorrect_disk_animation_folder_path
                row.prop(self, 'disk_animation_folder_path', text='')

        if self.options_type == 'export':
            row = layout.row()
            row.prop(self, 'export_all_actions')
            row = layout.row()
            row.prop(self, 'auto_stash_active_action')
            # this option is greyed out unless ue2rigify is active
            row = layout.row()
            row.enabled = bool(bpy.context.preferences.addons.get('ue2rigify'))
            row.prop(self, 'auto_sync_control_nla_to_source')
            row = layout.row()
            row.prop(self, 'use_object_origin')
            row = layout.row()

            # fbx settings box
            box = row.box()
            row = box.row()
            row.prop(
                self,
                'show_fbx_settings',
                icon='TRIA_DOWN' if self.show_fbx_settings else 'TRIA_RIGHT',
                icon_only=True,
                emboss=False
            )
            row.label(text='FBX Settings', icon='EXPORT')
            if self.show_fbx_settings:
                row = box.row()
                row.label(text='Include:')
                row = box.row()
                row.prop(self, 'use_custom_props')
                row = box.row()
                row.label(text='Transform:')
                row = box.row()
                row.prop(self, 'global_scale')
                row = box.row()
                row.prop(self, 'apply_scale_options')
                row = box.row()
                row.prop(self, 'axis_forward')
                row = box.row()
                row.prop(self, 'axis_up')
                row = box.row()
                row.prop(self, 'apply_unit_scale')
                row = box.row()
                row.prop(self, 'bake_space_transform')
                row = box.row()
                row.label(text='Geometry:')
                row = box.row()
                row.prop(self, 'mesh_smooth_type')
                row = box.row()
                row.prop(self, 'use_subsurf')
                row = box.row()
                row.prop(self, 'use_mesh_modifiers')
                row = box.row()
                row.prop(self, 'use_mesh_edges')
                row = box.row()
                row.prop(self, 'use_tspace')
                row = box.row()
                row.label(text='Armature:')
                row = box.row()
                row.prop(self, 'primary_bone_axis')
                row = box.row()
                row.prop(self, 'secondary_bone_axis')
                row = box.row()
                row.prop(self, 'armature_nodetype')
                row = box.row()
                row.prop(self, 'use_armature_deform_only')
                row = box.row()
                row.prop(self, 'add_leaf_bones')
                row = box.row()
                row.label(text='Animation:')
                row = box.row()
                row.prop(self, 'bake_anim')
                row = box.row()
                row.prop(self, 'bake_anim_use_all_bones')
                row = box.row()
                row.prop(self, 'bake_anim_force_startend_keying')
                row = box.row()
                row.prop(self, 'bake_anim_step')
                row = box.row()
                row.prop(self, 'bake_anim_simplify_factor')
                row = box.row()
                row.label(text='Extras:')
                row = box.row()
                row.prop(self, 'use_metadata')

        if self.options_type == 'validations':
            row = layout.row()
            row.prop(self, 'validate_materials')
            row = layout.row()
            row.prop(self, 'validate_textures')

        if self.options_type == 'import':
            row = layout.row()
            row.prop(self, 'import_materials')
            row = layout.row()
            row.prop(self, 'import_textures')
            row = layout.row()
            row.prop(self, 'import_animations')
            row = layout.row()
            row.prop(self, 'import_lods')
            row = layout.row()
            row.prop(self, 'advanced_ui_import')