import bpy, json
from dataclasses import dataclass, asdict, field
from typing import Any
from .material import MaterialMetadata, VectorInputMetadata, ScalarInputMetadata, get_texture_affix, get_baked_images, has_packed_textures
from .armature import ArmatureMetadata
from .mesh import MeshMetadata
from ..texture_constants import INVALID_FILENAME_CHARS

METADATA_NAME = "blender_metadata"

DATACLASSES = [
    MaterialMetadata,
    VectorInputMetadata,
    ScalarInputMetadata,
    ArmatureMetadata,
    MeshMetadata,
]
 
class MetadataEncoder(json.JSONEncoder):
    def default(self, o):
        if type(o) in DATACLASSES:
            return asdict(o)
        try:
            return super().default(o)
        except TypeError:
            raise TypeError(f"{type(o)} is not serializable, make sure metadata classes are added to DATACLASSES array.")

def get_mesh_objs() -> list[bpy.types.Object]:
    return [obj for obj in bpy.data.collections['Export'].objects if obj.type == "MESH"]

def get_empty_metadata() -> dict[str, Any]:
    return {
        "materials" : {},
        "armature" : None,
        "mesh" : None,
    }

def unreal_material_name(name : str) -> str:
    for c in INVALID_FILENAME_CHARS:
        name = name.replace(c, "_")
    return name

def fix_material_name(material : bpy.types.Material):
    material.name = unreal_material_name(material.name)
    
    # handle duplicate naming suffixes (ex. .001)
    while "." in material.name:
        material.name = unreal_material_name(material.name)

def assign_custom_metadata(properties : "Send2UeSceneProperties"):
    obj_dict = {}
    empty_dict = {}
    armature_dict = {}
    
    for obj in get_mesh_objs():
        metadata = get_empty_metadata()
        
        for i in range(len(obj.material_slots)):
            material = obj.material_slots[i].material
            # Usually for level sequence we want to export object animations but not geometry.
            if not properties.export_level_sequence:
                fix_material_name(material)
            metadata["materials"][material.name] = MaterialMetadata.create_material_metadata(material, properties)
         
        # Add armature metadata to mesh if armature is used.
        # See below comment about why this has to be done
        parent = get_highest_ancestor(obj)
        if parent and parent.type == "ARMATURE":
            if parent not in armature_dict:
                armature_dict[parent] = ArmatureMetadata.create_armature_metadata(parent, properties)
            metadata["armature"] = armature_dict[parent]
            
        # TODO: For combine mesh, this results in a random mesh's properties being chosen?
        metadata["mesh"] = MeshMetadata.create_mesh_metadata(obj, properties)
        
        obj_dict[obj] = metadata
        
        # Handle possible combine meshes option
        # Send2ue uses immediate parent empties to group meshes into separate files, if combine meshes is enabled.
        # However, unreal's "combine mesh" import option keeps only one mesh's metadata.
        # Therefore, we need to combine all children's metadata and set it on each child.
        # Results in redundancies, but only way to get around this.
        
        parent = get_highest_ancestor(obj)
        
        if parent and parent.type in ["EMPTY", "ARMATURE"]:
            if parent not in empty_dict:
                empty_dict[parent] = get_empty_metadata()
            for key, value in empty_dict[parent].items(): # key = materials, armature
                if isinstance(value, dict):
                    # (a = b | c) means c overwrites values in b
                    empty_dict[parent][key] = empty_dict[parent][key] | metadata[key]
                elif value is None:
                    empty_dict[parent][key] = metadata[key]
                    
    for obj, data in obj_dict.items():
        metadata = data
        parent = get_highest_ancestor(obj)
        if parent and parent.type in ["EMPTY", "ARMATURE"] and parent in empty_dict:
            empty_dict[parent]
            metadata = empty_dict[parent]
        obj[METADATA_NAME] = json.dumps(metadata, cls = MetadataEncoder)

def get_highest_ancestor(obj : bpy.types.Object):
    parent = obj.parent
    while parent and parent.type not in ["EMPTY", "ARMATURE"]:
        parent = parent.parent
    return parent

def delete_custom_metadata():
    for obj in get_mesh_objs():
        del obj[METADATA_NAME]