# Car Prep Tool

A Blender add-on that streamlines vehicle asset preparation for game engines (Unreal Engine, Unity, etc.). It handles pivot correction, orientation, scale normalization, collection organization and per-collection FBX export from a single sidebar panel.

**Version:** 1.3 · **Blender:** 4.3 and above · **Author:** Alfredo Mendez

## Features

1. **Pivot & Orientation** – Clears the parent hierarchy, applies all transforms, centers the car on X/Y, drops it to Z = 0 and rotates the geometry so the front faces +X. Choose the original front axis (+Y, -Y, -X or already +X). Leftover empties and armatures are removed.
2. **Scale Check** – Shows the longest dimension of the selection and normalizes the geometry by a power of ten so it lands in the 1–9 m range, keeping proportions intact.
3. **Collections** – One-click assignment to standard collections: Body, Glass, Interior, the four Wheels, the four Brake Calipers, and `NO_Export`. Each row has a visibility toggle and its own export button.
4. **Export** – Exports every collection (except `NO_Export`) as a separate FBX into an `export/` folder next to the `.blend`, named `<blendfile>_<Collection>.fbx`. You can also export a single collection or the current selection as one FBX.

### Wheel & caliper origins (non-destructive)

- **Wheels: Origin at Wheel Center** (v1.2) – Each wheel collection is exported with its origin at the center of its own bounding box instead of the shared car origin.
- **Calipers: Origin at Wheel Center** (v1.3) – Each caliper collection is exported with its origin at the center of its matching wheel (FL caliper → FL wheel, etc.), so calipers line up with the wheels in-engine.

Both options work on temporary mesh copies during export and restore the scene afterwards, so shared/instanced wheel meshes are never modified. The panel shows the computed wheel centers and warns when a caliper's matching wheel collection is missing.

## Installation

1. Download `car_prep_tool_v1.3.zip` from the [Releases](../../releases) page (do not unzip it).
2. In Blender go to **Edit › Preferences › Add-ons**, open the dropdown in the top-right corner and choose **Install from Disk…**
3. Select the `.zip` and enable **Car Prep Tool**.
4. The panel appears in the 3D Viewport sidebar (**N**) under the **Car Prep** tab.

Alternatively, open `car_prep_tool.py` in the Scripting workspace and click **Run Script** to use it for the current session only.

> Upgrading from v1.1: disable and remove the old add-on before installing this version.

## Workflow

1. Import the vehicle and select all its parts.
2. Pick the **Original Front** axis and click **Fix Car Pivot**.
3. Click **Set Proper Scale** if the scale check reports a problem.
4. Select parts and assign them to the matching collections.
5. Save the `.blend`, set the wheel/caliper origin options if needed, and click **Export All Collections to FBX**.

FBX settings: meshes only, modifiers applied, scale 1.0, forward Y / up Z, no leaf bones.

## Changelog

- **1.3** – Caliper collections can export with origin at the center of their matching wheel.
- **1.2** – Wheel collections can export with origin at the wheel's own bounding-box center (non-destructive).
- **1.1** – Initial public release.

## License

Released under the [GNU General Public License v3.0](LICENSE).
