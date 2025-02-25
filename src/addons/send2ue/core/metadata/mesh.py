import bpy
from dataclasses import dataclass, field
from typing import Optional
from ...metadata_properties import Send2UeMeshProperties

@dataclass
class MeshMetadata():
    category : str
    
    @staticmethod
    def create_mesh_metadata(mesh_obj : bpy.types.Object, properties : "Send2UeSceneProperties") -> 'MeshMetadata':
        mesh_prop : Send2UeMeshProperties = mesh_obj.send2ue_mesh
        if mesh_prop.category == "None":
            return MeshMetadata("None")
        elif mesh_prop.category == "Observable":
            return MeshMetadata("Observable")
        else:
            raise Exception(f"Invalid mesh category: {mesh_prop.category}")