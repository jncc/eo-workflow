import luigi
import logging
import os
import workflow_common.common as wc
import json
from string import Template
from workflow_common.SubmitJob import SubmitJob
from process_s2_basket.GetInputSwaths import GetInputSwaths
from process_s2_basket.SetupWorkDirs import SetupWorkDirs
from luigi.util import requires
from os.path import join

log = logging.getLogger('luigi-interface')

@requires(SetupWorkDirs)
class SubmitPrepareArdProcessingJobs(luigi.Task):
    paths = luigi.DictParameter()
    demFilename = luigi.Parameter()
    outWktFilename = luigi.Parameter()
    projAbbv = luigi.Parameter()
    arcsiReprojection = luigi.BoolParameter()
    arcsiCmdTemplate = luigi.OptionalParameter(default=None)
    testProcessing = luigi.BoolParameter(default = False)

    def run(self):
        setupWorkDirs = {}
        with self.input().open('r') as setupWorkDirsInfo:
            setupWorkDirs = json.load(setupWorkDirsInfo)

        basketDir = self.paths["basketDir"]

        with open(os.path.join(self.paths["templatesDir"], 's2_mpi_PrepareArdProcessing_job_template.sbatch'), 'r') as t:
            sbatchTemplate = Template(t.read())

        tasks = []
        for swathSetup in setupWorkDirs["swathSetups"]:
            productName = wc.getProductNameFromPath(swathSetup["swathDir"])

            outWktArg = "--outWkt={}".format(self.outWktFilename) if self.arcsiReprojection else ""
            projAbbvArg = "--projAbbv={}".format(self.projAbbv) if self.arcsiReprojection else ""

            arcsiCmdTemplate = ""
            if self.arcsiCmdTemplate is not None:
                arcsiCmdTemplate = "--arcsiCmdTemplate={}".format(self.arcsiCmdTemplate)

            sbatchParams = {
                "jobWorkingDir" : swathSetup["workspaceRoot"],
                "workingMount" : swathSetup["workingFileRoot"],
                "stateMount" : swathSetup["stateFileRoot"],
                "inputMount" : swathSetup["swathDir"],
                "staticMount" : self.paths["staticDir"],
                "outputMount" : self.paths["outputDir"],
                "s2ArdContainer": self.paths["singularityImgPath"],
                "dem": self.demFilename,
                "outWktArg" : outWktArg,
                "projAbbvArg" : projAbbvArg,
                "arcsiCmdTemplate" : arcsiCmdTemplate
            }

            sbatch = sbatchTemplate.substitute(sbatchParams)
            sbatchScriptPath = os.path.join(swathSetup["workspaceRoot"], "submit_PrepareArdProcessing_job_for_{}.sbatch".format(productName))

            with open(sbatchScriptPath, 'w') as sbatchScriptFile:
                sbatchScriptFile.write(sbatch)

            tasks.append(SubmitJob(
                paths = self.paths,
                productName = productName,
                sbatchScriptPath = sbatchScriptPath,
                testProcessing = self.testProcessing
            ))
        yield tasks

        outputFile = {
            "basket": basketDir,
            "submittedSwaths": []
        }

        for task in tasks:
            with task.output().open('r') as taskOutput:
                submittedSwath = json.load(taskOutput)
                outputFile["submittedSwaths"].append(submittedSwath)

        with self.output().open("w") as outFile:
            outFile.write(wc.getFormattedJson(outputFile))

    def output(self):
        outputFolder = self.paths["stateDir"]
        return wc.getLocalStateTarget(outputFolder, "SubmitPrepareArdProcessingJobs.json")