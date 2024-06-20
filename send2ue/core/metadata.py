import bpy, json
from dataclasses import dataclass, asdict, field

metadata_name = "unreal_metadata"

# This creates metadata for unreal assets. This is a specialized setup to handle Ucupaint and Node Wrangler setups.
# https://github.com/ucupumar/ucupaint

# This will find any Ucupaint group nodes and read default inputs from it.
# It will then look inside the group and read any textures from it.
# It will then look at any top level image texture nodes / value nodes and read them if they start with "Param_"
# or if they are one of the node wrangler names ["Base Color", "Roughness", "Metallic", "Normal", "Alpha"]

def default_vector():
    return [0,0,0,0]

@dataclass
class ScalarInputMetadata():
    default : float = 0
    path : str = ""
     
@dataclass
class VectorInputMetadata():
    default : list[float] = field(default_factory = default_vector)
    path : str = "" 
    
@dataclass
class MaterialMetadata():
    #color_value : list[float] = [0,0,0,0]
    #roughness_value : float = 0
    #metallic_value : float = 0
    #    
    #use_color_value : bool = False
    #use_roughness_value : bool = False
    #use_metallic_value : bool = False
    #    
    #color : str = ""
    #roughness : str = ""
    #normal : str = ""
    
    name : str
    
    color : VectorInputMetadata
    roughness : ScalarInputMetadata
    metallic : ScalarInputMetadata
    normal : VectorInputMetadata
    
    scalarInputs : dict[str, ScalarInputMetadata]
    vectorInputs : dict[str, VectorInputMetadata]
    
    @staticmethod
    def create_material_metadata(material : bpy.types.Material):
        return material.name
        #name = material.name
        #color = VectorInputMetadata()
        #return MaterialMetadata()

dataclasses = [
    MaterialMetadata,
    VectorInputMetadata,
    ScalarInputMetadata
]
 
class MetadataEncoder(json.JSONEncoder):
    def default(self, o):
        if type(o) in dataclasses:
            return asdict(o)
        return super().default(o)

def get_mesh_objs():
    return [obj for obj in bpy.data.collections['Export'].objects if obj.type == "MESH"]

def assign_custom_metadata():
    for obj in get_mesh_objs():
        metadata = {
            "materials" : []
        }
        
        for i in range(len(obj.material_slots)):
            material = obj.material_slots[i].material
            metadata["materials"].append(MaterialMetadata.create_material_metadata(material))
            
        obj[metadata_name] = json.dumps(metadata, cls = MetadataEncoder)

def delete_custom_metadata():
    for obj in get_mesh_objs():
        del obj[metadata_name]