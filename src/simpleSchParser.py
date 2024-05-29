
from pathlib import Path
from .sexpdata import sexpdata

# See: https://dev-docs.kicad.org/en/file-formats/sexpr-schematic/
    

def sch_list_to_dict(propertyList):

    buildingDict = {}

    for x in propertyList:

        # the first item in each list is the keyword used for matching
        match str(x.pop(0)):
            case "sheet":
                buildingDict.setdefault("sheet", [])

                sheetDict = sch_list_to_dict(x)
                buildingDict["sheet"].append(sheetDict)

            case "property":
                buildingDict.setdefault("property", {})

                sheetPropertyName = x.pop(0)
                sheetPropertyValue = x.pop(0)
                # otherData = sch_traverse(x) # Is just placement/format data
                buildingDict["property"][sheetPropertyName] = sheetPropertyValue
            
            case "uuid":
                buildingDict["uuid"] = x[0]
                
            # Add more types later

    return buildingDict


def sch_parse_file(schematicFile: Path) -> dict:

    if not isinstance(schematicFile, Path) :
        raise ValueError("Path not given")
    if not schematicFile.exists():
        raise FileNotFoundError("Path not found: " + str(schematicFile))

    with open(schematicFile) as file:
        parsedList = sexpdata.load(file)
    parsedList.pop(0)
    return sch_list_to_dict(parsedList)