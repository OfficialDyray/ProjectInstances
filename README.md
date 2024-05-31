# Project Instances
A simplified fork of [`HierarchicalPcb`](https://github.com/gauravmm/HierarchicalPcb) which was originally inspired by [`ReplicateLayout`](https://github.com/MitjaNemec/ReplicateLayout) plugin.

## How To Use

### Create a sub-project:
   1. Creating another (sub-)project inside your main project's folder.
   2. Create your schematic and pcb in the sub-project like normal
   3. Include the sub-project schematic in your Main Project
   4. Prepare the board like you are about to lay it out.
   5. Run the plugin on the main project's PCB to import the sub-project's PCB

### Update an existing sub-project:
   1. Make your changes to the sub-project's schematic and pcb
   2. Go to your main project and (re)annotate the sub-project's sheet.
   3. Update the pcb from your new schematics
   4. Run the plugin to apply the changes

[A Basic Example](examples/Basic)

## Tips
   1. Footprints placed outside the top and left edges of the PCB in your sub-project are not updated.
   2. Footprints deleted from the sub-project PCB are also not updated

## Advanced Usage:
### [Nested Projects](examples/Nesting)
### [Variants of same project](examples/Variants)
### [And more](examples)
