# Copyright Epic Games, Inc. All Rights Reserved.
import bpy
from bpy.utils import register_class, unregister_class

class Send2UE_AddSockets(bpy.types.Operator):
    # set bl_ properties
    bl_description = 'Add sockets at each child object for all selected objects'
    bl_idname = "object.send2ue_add_socket_hierarchy"
    bl_label = "Add Sockets"
    bl_options = {"REGISTER", "UNDO", "PRESET"}
    
    socket_size : bpy.props.FloatProperty(name = "Socket Size", default = 0.3)

    # Called on demand (i.e. button press, menu item)
    # Can also be called from operator search menu (Spacebar)
    def execute(self, context):
        if context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
            
        def add_sockets(parent : bpy.types.Object, size : float):
            for child in parent.children:
                print(child.name)
                name = child.name
                socket_name = f"SOCKET_{name}"
                if socket_name not in [i.name for i in parent.children]:
                    empty = bpy.data.objects.new(socket_name, None)  # Create new empty object
                    parent.users_collection[0].objects.link(empty)  # Link empty to the current object's collection
                    empty.empty_display_type = 'SPHERE'
                    empty.empty_display_size = size
                    empty.parent = parent
                    empty.matrix_local = child.matrix_local
                add_sockets(child, size)

        objects = bpy.context.view_layer.objects.selected[:]
        for obj in objects:   
            add_sockets(obj, self.socket_size)
        
        return {'FINISHED'}


class Send2UE_ToolsPanel(bpy.types.Panel):
    bl_idname = "SEND2UE_PT_global_tools"
    bl_label = "Send2UE Tools"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Send2UE"

    @classmethod
    def poll(cls, context):
        return True

    # called every frame
    def draw(self, context):
        col = self.layout.column()
        add_sockets = col.operator(Send2UE_AddSockets.bl_idname)
        
classes = [Send2UE_ToolsPanel, Send2UE_AddSockets]

def register():
    for cls in classes:
        register_class(cls)

def unregister():
    for cls in classes:
        unregister_class(cls)
