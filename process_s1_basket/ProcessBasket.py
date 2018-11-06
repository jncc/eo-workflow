import luigi
import logging
import os
import glob
import workflow_common.common as wc
import json
from workflow_common.RunJob import RunJob
from os.path import join

log = logging.getLogger('luigi-interface')

class ProcessBasket(luigi.Task):
    pathRoots = luigi.DictParameter()
    demFilename = luigi.Parameter()
    testProcessing = luigi.BoolParameter(default = False)

    def run(self):
        basketDir = self.pathRoots["basketDir"]

        tasks = []
        for inputFile in glob.glob(os.path.join(basketDir, "*.zip")):
            task = RunJob(
                inputFile = inputFile,
                demFilename = self.demFilename,
                pathRoots = self.pathRoots,
                removeSourceFile = True,
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
        outputFolder = self.pathRoots["stateDir"]
        return wc.getLocalStateTarget(outputFolder, "ProcessBasket.json")