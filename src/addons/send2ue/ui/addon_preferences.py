# Copyright Epic Games, Inc. All Rights Reserved.

import bpy
from ..properties import Send2UeAddonProperties
from ..constants import ToolInfo
from .. import __package__


class SendToUnrealPreferences(Send2UeAddonProperties, bpy.types.AddonPreferences):
    """
    This class creates the settings interface in the send to unreal addon.
    """
    bl_idname = __package__

    def draw(self, context):
        """
        This defines the draw method, which is in all Blender UI types that create interfaces.

        :param context: The context of this interface.
        """
        row = self.layout.row()
        row.prop(self, 'automatically_create_collections')
        row = self.layout.row()
        row.label(text='RPC Response Timeout')
        row.prop(self, 'rpc_response_timeout', text='')
        row = self.layout.row()

        row.label(text="Multicast TTL")
        row.prop(self, 'multicast_ttl', text='')
        row = self.layout.row()
        row.label(text="Multicast Group Endpoint")
        row.prop(self, 'multicast_group_endpoint', text='')
        row = self.layout.row()
        row.label(text="Command Endpoint")
        row.prop(self, 'command_endpoint', text='')
        row = self.layout.row()

        row.label(text='Extensions Repo Path:')
        row = self.layout.row()
        row = row.split(factor=0.95, align=True)
        row.prop(self, 'extensions_repo_path', text='')
        row.operator('send2ue.reload_extensions', text='', icon='UV_SYNC_SELECT')

def register():
    """
    Registers the addon preferences when the addon is enabled.
    """
    bpy.utils.register_class(SendToUnrealPreferences)


def unregister():
    """
    Unregisters the addon preferences when the addon is disabled.
    """
    bpy.utils.unregister_class(SendToUnrealPreferences)
