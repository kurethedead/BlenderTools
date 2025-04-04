import bpy
from dataclasses import dataclass, field
from ..texture_constants import *

# This creates material metadata for unreal assets. This is a specialized setup to handle Ucupaint and Node Wrangler setups.
# https://github.com/ucupumar/ucupaint

# This will store the values (for color/value nodes) and texture names (for texture nodes) for:
# 1. Ucupaint group input socket default values
# 2. Baked images inside an Ucupaint group, if the node tree is using baked images
# 3. Top level texture nodes using node wrangler labels
# 4. Any other applicable node whose label starts with the specified input prefix
# 5. Most unconnected input sockets on the Principled BSDF node (other shader nodes not supported)


def unreal_image_name(name : str) -> str:
    # remove file extension
    for ext in list(IMAGE_EXTENSIONS.values()):
        if name.endswith(f".{ext}"):
            name = name[:-(len(ext) + 1)]
    for c in INVALID_FILENAME_CHARS:
        name = name.replace(c, "_")
    return name

def get_baked_images(node_tree : bpy.types.NodeTree) -> dict[str, bpy.types.TextureNodeImage]:
    image_dict = {}
    for node in node_tree.nodes:
        if node.type == "TEX_IMAGE" and node.label[:len("Baked ")] == "Baked ":
            image_dict[node.label[len("Baked "):]] = node
    return image_dict

# Usually, properties = bpy.context.scene.send2ue
def get_texture_affix(properties : "Send2UeSceneProperties") -> str:   
    affix_props = properties.extensions.affixes
    texture_prefix = ""
    if affix_props.auto_add_asset_name_affixes:
        texture_prefix = affix_props.texture_name_affix
    return texture_prefix

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
    
    # Note that input prefixed nodes do not have to be connected to anything to export.
    @staticmethod
    def create_material_metadata(material : bpy.types.Material, properties : "Send2UeSceneProperties") -> 'MaterialMetadata':
        scalar_inputs : dict[str, ScalarInputMetadata] = {}
        vector_inputs : dict[str, VectorInputMetadata] = {}
        
        texture_prefix = get_texture_affix(properties)
        
        nodes = material.node_tree.nodes if material.node_tree else []
        for node in nodes:
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
                            image_name = texture_prefix + unreal_image_name(image_node.image.name[len("Ucupaint "):])
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
                    image_name = texture_prefix + unreal_image_name(node.image.name)
                    if len(node.outputs[0].links) > 0:
                        socket_type = node.outputs[0].links[0].to_socket.type
                        if socket_type == "RGBA" or socket_type == "VECTOR":
                            MaterialMetadata.get_vector(vector_inputs, label).texture_name = image_name
                        elif socket_type == "VALUE":
                            MaterialMetadata.get_scalar(scalar_inputs, label).texture_name = image_name
                        else:
                           print(f"Skipping image due to invalid output connection: {node.label}\n")
                    else:
                        print(f"Image {node.label} not connected to an output, skipping.\n")
            
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