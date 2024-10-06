INPUT_PREFIX = "Param_"
UCUPAINT_TITLE = "Ucupaint"
NODE_WRANGLER_TEXTURES = [
    "Base Color",
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

UCUPAINT_IGNORE_BAKED = [
    "Normal Overlay Only",
    "Normal Displacement"
]

INVALID_FILENAME_CHARS = "!@#$%^&*()=[]\\:;\"\'<,>./? "

# Blender image format enum to file extension
IMAGE_EXTENSIONS = {
    "BMP" : "bmp", 
    "PNG" : "png",
    "JPEG" : "jpg",
    "JPEG2000" : "jp2",
    "TARGA" : "tga",
    "OPEN_EXR" : "exr",
    "HDR" : "hdr",
    "TIFF" : "tiff",
    "WEBP" : "webp"
}