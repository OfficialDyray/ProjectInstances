# Project Instances
A fork of [`HierarchicalPcb`](https://github.com/gauravmm/HierarchicalPcb) which was originally inspired by the [`ReplicateLayout`](https://github.com/MitjaNemec/ReplicateLayout) plugin.

## How To Use

### Create a sub-project:
   1. Creating another (sub-)project inside your main project's folder. 

Here is what the recommended folder structure looks like from the root project:
![What the project tree looks like](https://github.com/OfficialDyray/ProjectInstances/blob/schParser/images/FolderStructure.png)

   3. Create your schematic and pcb in the sub-project like normal
   4. Include the sub-project schematic in your Main Project
   5. Prepare the board like you are about to lay it out.
   6. Run the plugin on the main project's PCB to import the sub-project's PCB

![](https://github.com/OfficialDyray/ProjectInstances/blob/schParser/images/SideBySideHierarchy.png)

### Update an existing sub-project:
   1. Make your changes to the sub-project's schematic and pcb
   2. Go to your main project and (re)annotate the sub-project's sheet.
   3. Update the pcb from your new schematics
   4. Run the plugin to apply the changes


https://github.com/user-attachments/assets/78d0a88c-ed20-4e0c-ae54-b3dcbba4581b


[A Basic Example](examples/Basic)

## Tips
   1. It is intended to leave footprints out of a sub-board and they won't be laid out in the root project.

## Advanced Usage:
### [Nested Projects](examples/Nesting)
### [Variants of same project](examples/Variants)
### [And more](examples)
