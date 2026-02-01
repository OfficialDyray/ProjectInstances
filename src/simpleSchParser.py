
from pathlib import Path
from .sexpdata import sexpdata

# See: https://dev-docs.kicad.org/en/file-formats/sexpr-schematic/
    

def sch_list_to_dict(propertyList):

    buildingDict = {}

    for x in propertyList:

        # the first item in each list is the keyword used for matching
        item = str(x.pop(0))

        if item == "sheet":
            buildingDict.setdefault("sheet", [])
            sheetDict = sch_list_to_dict(x)
            buildingDict["sheet"].append(sheetDict)

        elif item == "property":
            buildingDict.setdefault("property", {})

            sheetPropertyName = x.pop(0)
            sheetPropertyValue = x.pop(0)
            # otherData = sch_traverse(x) # Is just placement/format data
            buildingDict["property"][sheetPropertyName] = sheetPropertyValue  

        elif item == "uuid":
            buildingDict["uuid"] = x[0]
                
            # Add more types later

    return buildingDict


def sch_parse_file(schematicFile: Path) -> dict:

    if not isinstance(schematicFile, Path) :
        raise ValueError("Path not given")
    if not schematicFile.exists():
        raise FileNotFoundError("Path not found: " + str(schematicFile))

    try:
        with open(schematicFile, encoding="utf-8") as file:
            parsedList = sexpdata.load(file)
    except UnicodeDecodeError:
        with open(schematicFile, encoding="latin-1") as file:
            parsedList = sexpdata.load(file)
    parsedList.pop(0)
    return sch_list_to_dict(parsedList)