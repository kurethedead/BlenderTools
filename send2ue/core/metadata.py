import bpy, json
from dataclasses import dataclass, asdict, field

# This creates metadata for unreal assets. This is a specialized setup to handle Ucupaint and Node Wrangler setups.
# https://github.com/ucupumar/ucupaint

# This will find any Ucupaint group nodes and read default inputs from it.
# It will then look inside the group and read any textures from it.
# It will then look at any top level image texture nodes / value nodes and read them if they start with "Param_"
# or if they are one of the node wrangler names ["Base Color", "Roughness", "Metallic", "Normal", "Alpha"]

# Only Principled BSDF materials are supported for non-Ucupaint values on the main shader node.

metadata_name = "unreal_metadata"
input_prefix = "Param_"
node_wrangler_textures = [
    "Base Color", # gets converted to "Color" (for Ucupaint consistency) in metadata, see below
    "Metallic",
    "Specular",
    "Roughness",
    "Gloss",
    "Normal",
    "Bump",
    "Displacement",
    "Transmission",
    "Emission",
    "Alpha",
    "Ambient Occlusion",
]

def unreal_name(name : str) -> str:
    return name.replace(" ", "_").rsplit(".", 1)[0] # remove file extension

def get_baked_images(node_tree : bpy.types.NodeTree) -> dict[str, bpy.types.TextureNodeImage]:
    imageDict = {}
    for node in node_tree.nodes:
        if node.type == "TEX_IMAGE" and node.label[:len("Baked ")] == "Baked ":
            imageDict[node.label[len("Baked "):]] = node
    return imageDict

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
    name : str
    
    scalarInputs : dict[str, ScalarInputMetadata]
    vectorInputs : dict[str, VectorInputMetadata]
    
    @staticmethod
    def get_scalar(scalarInputs : dict[str, ScalarInputMetadata], label : str) -> ScalarInputMetadata:
        if label in scalarInputs:
            return scalarInputs[label]
        else:
            scalarInput = ScalarInputMetadata()
            scalarInputs[label] = scalarInput
            return scalarInput
    
    @staticmethod
    def get_vector(vectorInputs : dict[str, VectorInputMetadata], label : str) -> VectorInputMetadata:
        if label in vectorInputs:
            return vectorInputs[label]
        else:
            vectorInput = VectorInputMetadata()
            vectorInputs[label] = vectorInput
            return vectorInput
    
    @staticmethod
    def create_material_metadata(material : bpy.types.Material) -> 'MaterialMetadata':
        name = material.name
        scalarInputs : dict[str, ScalarInputMetadata] = {}
        vectorInputs : dict[str, VectorInputMetadata] = {}
        
        for node in material.node_tree.nodes:
            # Find Ucupaint group
            if node.type == "GROUP" and node.node_tree.name.find("Ucupaint") >= 0 and node.node_tree.yp.use_baked: 
                
                # Handle default Ucupaint channels
                MaterialMetadata.get_vector(vectorInputs, "Color").default = list(node.inputs["Color"].default_value)
                MaterialMetadata.get_scalar(scalarInputs, "Metallic").default = node.inputs["Metallic"].default_value
                MaterialMetadata.get_scalar(scalarInputs, "Roughness").default = node.inputs["Roughness"].default_value
                MaterialMetadata.get_vector(vectorInputs, "Normal").default = default_vector()
                # ignore normal height input
                
                # Handle custom Ucupaint channels
                # This assumes Ucupaint inputs start adding custom inputs at index 5.
                for i in range(5, len(node.inputs)):
                    input = node.inputs[i]
                    if input.type == "RGBA" or input.type == "VECTOR":
                        MaterialMetadata.get_vector(vectorInputs, input.name).default = input.default_value
                    elif input.type == "VALUE":
                        MaterialMetadata.get_scalar(scalarInputs, input.name).default = input.default_value
                    else:
                        print(f"Skipping input: {input.name}\n")
                
                # Handle Ucupaint baked images
                for channel, image_node in get_baked_images(node.node_tree).items():
                    if len(image_node.outputs[0].links) > 0:
                        socket_type = image_node.outputs[0].links[0].to_socket.type
                        image_name = unreal_name(image_node.image.name[len("Ucupaint "):])
                        if socket_type == "RGBA" or socket_type == "VECTOR":
                            MaterialMetadata.get_vector(vectorInputs, channel).texture_name = image_name
                        elif socket_type == "VALUE":
                            MaterialMetadata.get_scalar(scalarInputs, channel).texture_name = image_name
                        else:
                           print(f"Skipping baked image due to invalid output connection: {image_node.label}\n")
                    else:
                        print(f"Baked image {image_node.label} not connected to an output, skipping.\n")
            
            # Handle node wrangler / flagged texture nodes
            elif node.type == "TEX_IMAGE":
                if node.label in node_wrangler_textures or node.label.find(input_prefix) == 0:
                    if node.label in node_wrangler_textures:
                        label = node.label if node.label != "Base Color" else "Color"
                    else:
                        label = node.label[len(input_prefix):]
                    image_name = unreal_name(node.image.name)
                    if len(node.outputs[0].links) > 0:
                        socket_type = node.outputs[0].links[0].to_socket.type
                        if socket_type == "RGBA" or socket_type == "VECTOR":
                            MaterialMetadata.get_vector(vectorInputs, label).texture_name = image_name
                        elif socket_type == "VALUE":
                            MaterialMetadata.get_scalar(scalarInputs, label).texture_name = image_name
                        else:
                           print(f"Skipping image due to invalid output connection: {image_node.label}\n")
                    else:
                        print(f"Image {image_node.label} not connected to an output, skipping.\n")
            
            # Handle flagged color/value constants
            elif node.type == "RGB" and node.label.find(input_prefix) == 0:
                vectorInput = MaterialMetadata.get_vector(vectorInputs, node.label[len(input_prefix):]) 
                vectorInput.default = list(node.outputs[0].default_value)
            
            elif node.type == "VALUE" and node.label.find(input_prefix) == 0:
                scalarInput = MaterialMetadata.get_scalar(scalarInputs, node.label[len(input_prefix):]) 
                scalarInput.default = node.outputs[0].default_value
                
            elif node.type == "BSDF_PRINCIPLED":
                if len(node.inputs["Base Color"].links) == 0:
                    MaterialMetadata.get_vector(vectorInputs, "Color").default = list(node.inputs["Base Color"].default_value)
                if len(node.inputs["Metallic"].links) == 0:
                    MaterialMetadata.get_scalar(scalarInputs, "Metallic").default = node.inputs["Metallic"].default_value
                if len(node.inputs["Roughness"].links) == 0:
                    MaterialMetadata.get_scalar(scalarInputs, "Roughness").default = node.inputs["Roughness"].default_value
                if len(node.inputs["Alpha"].links) == 0:
                    MaterialMetadata.get_scalar(scalarInputs, "Alpha").default = node.inputs["Alpha"].default_value
                if len(node.inputs["Normal"].links) == 0:
                    MaterialMetadata.get_vector(vectorInputs, "Normal").default = default_vector()
                if len(node.inputs["Specular IOR Level"].links) == 0:
                    MaterialMetadata.get_scalar(scalarInputs, "Specular").default = node.inputs["Specular IOR Level"].default_value
                if len(node.inputs["Emission Color"].links) == 0:
                    MaterialMetadata.get_vector(vectorInputs, "Emission").default = list(node.inputs["Emission Color"].default_value)
                if len(node.inputs["Emission Strength"].links) == 0:
                    MaterialMetadata.get_scalar(scalarInputs, "Emission Strength").default = node.inputs["Emission Strength"].default_value
        
        return MaterialMetadata(name, scalarInputs, vectorInputs)
    
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

def get_mesh_objs() -> list[bpy.types.Object]:
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