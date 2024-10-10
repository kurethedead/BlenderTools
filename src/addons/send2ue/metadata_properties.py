import bpy

ARMATURE_CATEGORIES = [
    ("None", "None", "None"),
    ("Observable", "Observable", "Mesh that has multiple moving parts that can play one-off anims independently that pause at end"),
]

class Send2UeArmatureProperties(bpy.types.PropertyGroup):
    category: bpy.props.EnumProperty(
        name = "Category",
        items = ARMATURE_CATEGORIES
    )

class Send2UeBoneProperties(bpy.types.PropertyGroup):
    is_observable_section: bpy.props.BoolProperty(
        name = "Is Observable Section",
        description = "Is this bone the base bone for a portion of the armature that plays a one-off animation independently of the rest of the armature?"
    )

def prop_split(layout, data, field, name, **prop_kwargs):
    split = layout.split(factor=0.5)
    split.label(text=name)
    split.prop(data, field, text="", **prop_kwargs)
    
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
        prop = obj.data.send2ue_armature
        col = self.layout.column().box()
        col.box().label(text="Send2UE Armature")

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
    Send2UeBonePanel
]
    
def register_metadata_properties():
    for cls in PROPERTY_CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Armature.send2ue_armature = bpy.props.PointerProperty(type=Send2UeArmatureProperties)
    bpy.types.Bone.send2ue_bone = bpy.props.PointerProperty(type=Send2UeBoneProperties)

def unregister_metadata_properties():
    del bpy.types.Armature.send2ue_armature
    del bpy.types.Bone.send2ue_bone
    for cls in PROPERTY_CLASSES:
        bpy.utils.unregister_class(cls)