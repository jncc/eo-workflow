import luigi
import logging
import os
import workflow_common.common as wc
import json

from datetime import datetime
from pathlib import Path
from string import Template
from workflow_common.SubmitJob import SubmitJob
from process_s1_basket.SetupWorkDirs import SetupWorkDirs
from luigi.util import requires
from os.path import join

log = logging.getLogger('luigi-interface')

@requires(SetupWorkDirs)
class ProcessS1Basket(luigi.Task):
    paths = luigi.DictParameter()
    spatialConfig = luigi.DictParameter()
    testProcessing = luigi.BoolParameter(default = False)
    removeSourceFile = luigi.BoolParameter()
    spatialConfig = luigi.DictParameter()

    def run(self):
        setupWorkDirs = {}
        with self.input().open('r') as setupWorkDirsInfo:
            setupWorkDirs = json.load(setupWorkDirsInfo)

        basketDir = self.paths["basketDir"]

        with open(os.path.join(self.paths["templatesDir"], 's1_job_template.sbatch'), 'r') as t:
            sbatchTemplate = Template(t.read())

        reportFileName = "{}-{}.csv".format(os.path.basename(self.paths["basketDir"]), datetime.now().strftime("%Y%m%d%H%M"))

        tasks = []
        for productSetup in setupWorkDirs["productSetups"]:
            productName = wc.getProductNameFromPath(productSetup["inputPath"])

            path = Path(productSetup["inputPath"])
            inputDir = path.parent
            removeSourceFileFlag = "--removeInputFile" if self.removeSourceFile else ""

            sbatchParams = {
                "jobWorkingDir" : productSetup["workspaceRoot"],
                "reportMount": self.paths["reportDir"],
                "databaseMount": self.paths["databaseDir"], 
                "workingMount": productSetup["workingFileRoot"],
                "stateMount": productSetup["stateFileRoot"],
                "inputMount" :inputDir,
                "staticMount" :self.paths["staticDir"],
                "outputMount": self.paths["outputDir"],
                "s1ArdContainer": self.paths["singularityImgPath"],
                "productName": productName,
                "snapConfigUtmProj": self.spatialConfig["snapConfigUtmProj"],
                "snapConfigCentralMeridian": self.spatialConfig["snapConfigCentralMeridian"],
                "snapConfigFalseNorthing": self.spatialConfig["snapConfigFalseNorthing"],
                "snapRunArguments": self.spatialConfig["snapRunArguments"],
                "sourceSrs": self.spatialConfig["sourceSrs"],
                "targetSrs": self.spatialConfig["targetSrs"],
                "filenameDemData": self.spatialConfig["filenameDemData"],
                "filenameSrs": self.spatialConfig["filenameSrs"],
                "demFilename": self.spatialConfig["demFilename"],
                "demTitle": self.spatialConfig["demTitle"],
                "metadataProjection": self.spatialConfig["metadataProjection"],
                "metadataPlaceName": self.spatialConfig["metadataPlaceName"],
                "metadataParentPlaceName": self.spatialConfig["metadataParentPlaceName"],
                "removeSourceFileFlag": removeSourceFileFlag,
                "reportFileName": reportFileName
            }

            bsub = sbatchTemplate.substitute(sbatchParams)
            sbatchScriptPath = os.path.join(productSetup["workspaceRoot"], "process_s1_ard.sbatch")

            with open(sbatchScriptPath, 'w') as sbatchScriptFile:
                sbatchScriptFile.write(bsub)

            task = SubmitJob(
                paths = self.paths,
                productName = productName,
                sbatchScriptPath = sbatchScriptPath,
                testProcessing = self.testProcessing
            )

            tasks.append(task)
        yield tasks

        outputFile = {
            "basket": basketDir,
            "submittedProducts": []
        }

        for task in tasks:
            with task.output().open('r') as taskOutput:
                submittedProduct = json.load(taskOutput)
                outputFile["submittedProducts"].append(submittedProduct)

        with self.output().open("w") as outFile:
            outFile.write(wc.getFormattedJson(outputFile))

    def output(self):
        outputFolder = self.paths["stateDir"]
        return wc.getLocalStateTarget(outputFolder, "ProcessS1Basket.json")
