import bpy, json
from dataclasses import dataclass, asdict, field
from typing import Any
from .texture_constants import *

# This creates material metadata for unreal assets. This is a specialized setup to handle Ucupaint and Node Wrangler setups.
# https://github.com/ucupumar/ucupaint

# This will store the values (for color/value nodes) and texture names (for texture nodes) for:
# 1. Ucupaint group input socket default values
# 2. Baked images inside an Ucupaint group, if the node tree is using baked images
# 3. Top level texture nodes using node wrangler labels
# 4. Any other applicable node whose label starts with the specified input prefix
# 5. Most unconnected input sockets on the Principled BSDF node (other shader nodes not supported)

METADATA_NAME = "blender_metadata"

def unreal_image_name(name : str) -> str:
    # remove file extension
    for ext in list(IMAGE_EXTENSIONS.values()):
        if name.endswith(f".{ext}"):
            name = name[:-(len(ext) + 1)]
    for c in INVALID_FILENAME_CHARS:
        name = name.replace(c, "_")
    return name

def unreal_material_name(name : str) -> str:
    for c in INVALID_FILENAME_CHARS:
        name = name.replace(c, "_")
    return name

def fix_material_name(material : bpy.types.Material):
    material.name = unreal_material_name(material.name)
    
    # handle duplicate naming suffixes (ex. .001)
    while "." in material.name:
        material.name = unreal_material_name(material.name)

def get_baked_images(node_tree : bpy.types.NodeTree) -> dict[str, bpy.types.TextureNodeImage]:
    image_dict = {}
    for node in node_tree.nodes:
        if node.type == "TEX_IMAGE" and node.label[:len("Baked ")] == "Baked ":
            image_dict[node.label[len("Baked "):]] = node
    return image_dict

def default_vector():
    return [0,0,0,0]

@dataclass
class ScalarInputMetadata():
    default : float = 0
    texture_name : str = ""
     
@dataclass
class VectorInputMetadata():
    default : list[float] = field(default_factory = default_vector)
    texture_name : str = "" 
    
@dataclass
class MaterialMetadata():
    scalar_inputs : dict[str, ScalarInputMetadata]
    vector_inputs : dict[str, VectorInputMetadata]
    
    @staticmethod
    def get_scalar(scalar_inputs : dict[str, ScalarInputMetadata], label : str) -> ScalarInputMetadata:
        if label in scalar_inputs:
            return scalar_inputs[label]
        else:
            scalar_input = ScalarInputMetadata()
            scalar_inputs[label] = scalar_input
            return scalar_input
    
    @staticmethod
    def get_vector(vector_inputs : dict[str, VectorInputMetadata], label : str) -> VectorInputMetadata:
        if label in vector_inputs:
            return vector_inputs[label]
        else:
            vector_input = VectorInputMetadata()
            vector_inputs[label] = vector_input
            return vector_input
    
    @staticmethod
    def create_material_metadata(material : bpy.types.Material) -> 'MaterialMetadata':
        scalar_inputs : dict[str, ScalarInputMetadata] = {}
        vector_inputs : dict[str, VectorInputMetadata] = {}
        
        for node in material.node_tree.nodes:
            # Find Ucupaint group
            if node.type == "GROUP" and node.node_tree.name.find("Ucupaint") >= 0: 
                
                # Handle Ucupaint channels
                for i in range(len(node.inputs)):
                    input = node.inputs[i]
                    input_name = input.name if input.name != "Color" else "Base Color" # Make consistent with Principled BSDF
                    if input.type == "RGBA" or input.type == "VECTOR":
                        MaterialMetadata.get_vector(vector_inputs, input_name).default = list(input.default_value)
                    elif input.type == "VALUE":
                        MaterialMetadata.get_scalar(scalar_inputs, input_name).default = input.default_value
                    else:
                        print(f"Skipping input: {input_name}\n")
                
                if node.node_tree.yp.use_baked:
                    # Handle Ucupaint baked images
                    for channel, image_node in get_baked_images(node.node_tree).items():
                        channel_name = channel if channel != "Color" else "Base Color" # Make consistent with Principled BSDF
                        if len(image_node.outputs[0].links) > 0:
                            socket_type = image_node.outputs[0].links[0].to_socket.type
                            image_name = unreal_image_name(image_node.image.name[len("Ucupaint "):])
                            if socket_type == "RGBA" or socket_type == "VECTOR":
                                MaterialMetadata.get_vector(vector_inputs, channel_name).texture_name = image_name
                            elif socket_type == "VALUE":
                                MaterialMetadata.get_scalar(scalar_inputs, channel_name).texture_name = image_name
                            else:
                               print(f"Skipping baked image due to invalid output connection: {image_node.label}\n")
                        else:
                            print(f"Baked image {image_node.label} not connected to an output, skipping.\n")
            
            # Handle node wrangler / flagged texture nodes
            elif node.type == "TEX_IMAGE":
                if node.label in NODE_WRANGLER_TEXTURES or node.label.find(INPUT_PREFIX) == 0:
                    if node.label in NODE_WRANGLER_TEXTURES:
                        label = node.label
                    else:
                        label = node.label[len(INPUT_PREFIX):]
                    image_name = unreal_image_name(node.image.name)
                    if len(node.outputs[0].links) > 0:
                        socket_type = node.outputs[0].links[0].to_socket.type
                        if socket_type == "RGBA" or socket_type == "VECTOR":
                            MaterialMetadata.get_vector(vector_inputs, label).texture_name = image_name
                        elif socket_type == "VALUE":
                            MaterialMetadata.get_scalar(scalar_inputs, label).texture_name = image_name
                        else:
                           print(f"Skipping image due to invalid output connection: {image_node.label}\n")
                    else:
                        print(f"Image {image_node.label} not connected to an output, skipping.\n")
            
            # Handle flagged color/value constants
            elif node.type == "RGB" and node.label.find(INPUT_PREFIX) == 0:
                vector_input = MaterialMetadata.get_vector(vector_inputs, node.label[len(INPUT_PREFIX):]) 
                vector_input.default = list(node.outputs[0].default_value)
            
            elif node.type == "VALUE" and node.label.find(INPUT_PREFIX) == 0:
                scalar_input = MaterialMetadata.get_scalar(scalar_inputs, node.label[len(INPUT_PREFIX):]) 
                scalar_input.default = node.outputs[0].default_value
                
            elif node.type == "BSDF_PRINCIPLED": # TODO: Just read every input node? Too crowded?
                if len(node.inputs["Base Color"].links) == 0:
                    MaterialMetadata.get_vector(vector_inputs, "Base Color").default = list(node.inputs["Base Color"].default_value)
                if len(node.inputs["Metallic"].links) == 0:
                    MaterialMetadata.get_scalar(scalar_inputs, "Metallic").default = node.inputs["Metallic"].default_value
                if len(node.inputs["Roughness"].links) == 0:
                    MaterialMetadata.get_scalar(scalar_inputs, "Roughness").default = node.inputs["Roughness"].default_value
                if len(node.inputs["Alpha"].links) == 0:
                    MaterialMetadata.get_scalar(scalar_inputs, "Alpha").default = node.inputs["Alpha"].default_value
                if len(node.inputs["Normal"].links) == 0:
                    MaterialMetadata.get_vector(vector_inputs, "Normal").default = default_vector()
                if len(node.inputs["Specular IOR Level"].links) == 0:
                    MaterialMetadata.get_scalar(scalar_inputs, "Specular").default = node.inputs["Specular IOR Level"].default_value
                if len(node.inputs["Emission Color"].links) == 0:
                    MaterialMetadata.get_vector(vector_inputs, "Emission").default = list(node.inputs["Emission Color"].default_value)
                if len(node.inputs["Emission Strength"].links) == 0:
                    MaterialMetadata.get_scalar(scalar_inputs, "Emission Strength").default = node.inputs["Emission Strength"].default_value
        
        return MaterialMetadata(scalar_inputs, vector_inputs)
    
DATACLASSES = [
    MaterialMetadata,
    VectorInputMetadata,
    ScalarInputMetadata
]
 
class MetadataEncoder(json.JSONEncoder):
    def default(self, o):
        if type(o) in DATACLASSES:
            return asdict(o)
        return super().default(o)

def get_mesh_objs() -> list[bpy.types.Object]:
    return [obj for obj in bpy.data.collections['Export'].objects if obj.type == "MESH"]

def get_empty_metadata() -> dict[str, Any]:
    return {
        "materials" : {}
    }

def assign_custom_metadata():
    obj_dict = {}
    empty_dict = {}
    
    for obj in get_mesh_objs():
        metadata = get_empty_metadata()
        
        for i in range(len(obj.material_slots)):
            material = obj.material_slots[i].material
            fix_material_name(material)
            metadata["materials"][material.name] = MaterialMetadata.create_material_metadata(material)
        
        obj_dict[obj] = metadata
        
        # Handle possible combine meshes option
        # Send2ue uses immediate parent empties to group meshes into separate files, if combine meshes is enabled.
        # However, unreal's "combine mesh" import option keeps only one mesh's metadata.
        # Therefore, we need to combine all children's metadata and set it on each child.
        # Results in redundancies, but only way to get around this.
        
        # TODO: Is armature necessary here?
        if obj.parent and obj.parent.type in ["EMPTY", "ARMATURE"]:
            parent = obj.parent
            if parent not in empty_dict:
                empty_dict[parent] = get_empty_metadata()
            for key, value in empty_dict[parent].items():
                if isinstance(value, dict):
                    empty_dict[parent][key] = empty_dict[parent][key] | metadata[key]
                    
    for obj, data in obj_dict.items():
        metadata = data
        if obj.parent and obj.parent.type == "EMPTY" and obj.parent in empty_dict:
            metadata = empty_dict[obj.parent]
        obj[METADATA_NAME] = json.dumps(metadata, cls = MetadataEncoder)


def delete_custom_metadata():
    for obj in get_mesh_objs():
        del obj[METADATA_NAME]