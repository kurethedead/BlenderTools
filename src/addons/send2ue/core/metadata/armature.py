import bpy
from dataclasses import dataclass, field
from typing import Optional
from ...metadata_properties import Send2UeBoneProperties, Send2UeArmatureProperties

@dataclass
class ArmatureMetadata():
    category : str
    observable_sections : list[str] # bone names
    
    @staticmethod
    def create_armature_metadata(armature : bpy.types.Armature, properties : "Send2UeSceneProperties") -> 'ArmatureMetadata':
        armature_prop : Send2UeArmatureProperties = armature.send2ue_armature
        if armature_prop.category == "None":
            return ArmatureMetadata("None", [])
        elif armature_prop.category == "Observable":
            observable_sections : list[str] = []
            for bone in armature.bones:
                bone_prop : Send2UeBoneProperties = bone.send2ue_bone
                if bone_prop.is_observable_section:
                    observable_sections.append(bone.name)
            return ArmatureMetadata("Observable", observable_sections)
        else:
            raise Exception(f"Invalid armature category: {armature_prop.category}")