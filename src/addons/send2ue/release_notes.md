## Patch Changes
* Object Origin scaling properly fixed
  * [64](https://github.com/poly-hammer/BlenderTools/pull/64)
* Fixed Blender 4.2 extension loading bug
  * [67](https://github.com/poly-hammer/BlenderTools/pull/67)
* Removed sys.path.append in RPC module
  * [70](https://github.com/poly-hammer/BlenderTools/pull/70)
* restricted object iteration to scene objects
  * [71](https://github.com/poly-hammer/BlenderTools/pull/71)
* Fixed ue2rigify extension addon detection and incorrect strip usage
  * [68](https://github.com/poly-hammer/BlenderTools/pull/68), [74](https://github.com/poly-hammer/BlenderTools/pull/74)
* added validate_unreal_plugins property
  * [74](https://github.com/poly-hammer/BlenderTools/pull/74)

## Special Thanks
@jack-yao91, @JoshQuake

## Tests Passing On
* Blender `3.6`, `4.2` (installed from blender.org)
* Unreal `5.3`, `5.4`