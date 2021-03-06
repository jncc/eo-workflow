import luigi
import os
import json
from os.path import basename, join
from luigi import LocalTarget

def getLocalTarget(key):
    return LocalTarget(key)

def getLocalDatedStateTarget(rootPath, date, fileName):
    statePath = os.path.join(rootPath, os.path.join(str(date), "state"))
    filePath = os.path.join(statePath, fileName)

    return LocalTarget(filePath)

def getLocalStateTarget(targetPath, fileName):
    targetKey = join(targetPath, fileName)
    return getLocalTarget(targetKey)

def getProductIdFromLocalSourceFile(sourceFile):
    productFilename = basename(sourceFile)
    return '%s_%s_%s_%s' % (productFilename[0:3], productFilename[17:25], productFilename[26:32], productFilename[42:48])

def getFormattedJson(jsonOutput):
    return json.dumps(jsonOutput, indent=4)

def getProductNameFromPath(inputPath):
    if inputPath.endswith(".zip"):
        return os.path.basename(os.path.splitext(inputPath)[0])
    else:
        return os.path.basename(inputPath)