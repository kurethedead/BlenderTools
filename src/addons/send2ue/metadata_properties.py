import bpy

ARMATURE_CATEGORIES = [
    ("None", "None", "None"),
    ("Observable", "Observable", "Mesh that has multiple moving parts that can play one-off anims independently that pause at end"),
]

MESH_CATEGORIES = [
    ("None", "None", "None"),
    ("Observable", "Observable", "Mesh that has multiple moving parts that can play one-off anims independently that pause at end"),
]

SEQUENCER_ACTOR_CATEGORIES = [
    ("Spawnable", "Spawnable", "Spawnable"),
    ("Possessable", "Possessable", "Possessable"),
]

class Send2UeMeshProperties(bpy.types.PropertyGroup):
    category: bpy.props.EnumProperty(
        name = "Category",
        items = MESH_CATEGORIES
    )
    
class Send2UeArmatureProperties(bpy.types.PropertyGroup):
    category: bpy.props.EnumProperty(
        name = "Category",
        items = ARMATURE_CATEGORIES
    )
    
    skeleton_asset_path: bpy.props.StringProperty(
        name = "Skeleton Path",
        override={"LIBRARY_OVERRIDABLE"},
        description = "Unreal path for skeleton asset. If empty, path will fallback to scene property value. Can be found by RMB asset -> Copy Reference"
    )
    
    # Warning: utilities.get_import_path() doesn't take this into account.
    # However, that function doesn't seem to be used for animation exporting in way that would miss this.
    anim_asset_path: bpy.props.StringProperty(
        name = "Animation Path (Linked)",
        override={"LIBRARY_OVERRIDABLE"},
        description = "Unreal path for anim folder for linked actions, which are assumed to be already exported. Must be terminated with a slash"
    )
    
    actor_category: bpy.props.EnumProperty(
        name = "Sequencer Category",
        items = SEQUENCER_ACTOR_CATEGORIES,
        override={"LIBRARY_OVERRIDABLE"},
    )
    
    actor_asset_path: bpy.props.StringProperty(
        name = "Actor Path",
        override={"LIBRARY_OVERRIDABLE"},
    )
    
    actor_name: bpy.props.StringProperty(
        name = "Actor Name",
        override={"LIBRARY_OVERRIDABLE"},
    )
    
    def get_path(self):
        if self.actor_category == "Spawnable":
            return self.actor_asset_path
        else:
            return self.actor_name

class Send2UeBoneProperties(bpy.types.PropertyGroup):
    is_observable_section: bpy.props.BoolProperty(
        name = "Is Observable Section",
        description = "Is this bone the base bone for a portion of the armature that plays a one-off animation independently of the rest of the armature?"
    )

def prop_split(layout, data, field, name, **prop_kwargs):
    split = layout.split(factor=0.5)
    split.label(text=name)
    split.prop(data, field, text="", **prop_kwargs)

'''    
class Send2UeObjectPanel(bpy.types.Panel):
    bl_label = "Send2UE Object"
    bl_idname = "OBJECT_PT_Send2UE_Object"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"
    bl_options = {"HIDE_HEADER"}

    @classmethod
    def poll(cls, context):
        return (
            context.object is not None
            and isinstance(context.object.data, bpy.types.Object)
        )

    def draw(self, context):
        obj = context.object
        prop = obj.data.send2ue_object
        col = self.layout.column().box()
        col.box().label(text="Send2UE Object")   
'''    
        
class Send2UeArmaturePanel(bpy.types.Panel):
    bl_label = "Send2UE Armature"
    bl_idname = "OBJECT_PT_Send2UE_Armature"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"
    bl_options = {"HIDE_HEADER"}

    @classmethod
    def poll(cls, context):
        return (
            context.object is not None
            and isinstance(context.object.data, bpy.types.Armature)
        )

    def draw(self, context):
        obj = context.object
        prop = obj.send2ue_armature
        col = self.layout.column().box()
        col.box().label(text="Send2UE Armature")

        col.prop(prop, "category")
        col.prop(prop, "skeleton_asset_path")
        col.prop(prop, "anim_asset_path")
        col.prop(prop, "actor_category")
        if prop.actor_category == "Spawnable":
            col.prop(prop, "actor_asset_path")
        else:
            col.prop(prop, "actor_name")
    
class Send2UeMeshPanel(bpy.types.Panel):
    bl_label = "Send2UE Mesh"
    bl_idname = "OBJECT_PT_Send2UE_Mesh"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"
    bl_options = {"HIDE_HEADER"}

    @classmethod
    def poll(cls, context):
        return (
            context.object is not None
            and isinstance(context.object.data, bpy.types.Mesh)
            and False # TODO: Mesh properties unused for now, remove later?
        )

    def draw(self, context):
        obj = context.object
        prop = obj.send2ue_mesh
        col = self.layout.column().box()
        col.box().label(text="Send2UE Mesh")

        col.prop(prop, "category")

class Send2UeBonePanel(bpy.types.Panel):
    bl_label = "Send2UE Bone"
    bl_idname = "OBJECT_PT_Send2UE_Bone"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "bone"
    bl_options = {"HIDE_HEADER"}

    @classmethod
    def poll(cls, context):
        return context.bone is not None

    def draw(self, context):
        bone = context.bone
        prop = bone.send2ue_bone
        col = self.layout.column().box()
        col.box().label(text="Send2UE Armature")

        col.prop(prop, "is_observable_section")

PROPERTY_CLASSES = [
    Send2UeArmatureProperties,
    Send2UeBoneProperties,
    Send2UeArmaturePanel,
    Send2UeBonePanel,
    Send2UeMeshProperties,
    Send2UeMeshPanel,
    #Send2UeObjectProperties,
    #Send2UeObjectPanel
]
    
def register_metadata_properties():
    for cls in PROPERTY_CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Object.send2ue_armature = bpy.props.PointerProperty(type=Send2UeArmatureProperties, override={"LIBRARY_OVERRIDABLE"})
    bpy.types.Object.send2ue_mesh = bpy.props.PointerProperty(type=Send2UeMeshProperties)
    bpy.types.Bone.send2ue_bone = bpy.props.PointerProperty(type=Send2UeBoneProperties)
    #bpy.types.Object.send2ue_object = bpy.props.PointerProperty(type=Send2UeObjectProperties)

def unregister_metadata_properties():
    del bpy.types.Object.send2ue_armature
    del bpy.types.Object.send2ue_mesh
    del bpy.types.Bone.send2ue_bone
    #del bpy.types.Object.send2ue_object
    for cls in PROPERTY_CLASSES:
        bpy.utils.unregister_class(cls)