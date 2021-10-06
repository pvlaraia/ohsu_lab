import codecs
import csv
import json
import os
from ohsu.config.config import Config
from ohsu.file_manager.directory import IJDirectory
from ohsu.image.image import Image
from ohsu.results.results import Results
from ij import IJ, WindowManager
from ij.gui import GenericDialog
from ij.plugin.frame import RoiManager

HEADER_KEY = '__HEADER__'

def run():

    config = Config.getConfig()

    gd = GenericDialog('Instructions')
    gd.addMessage('1. When prompted, choose the input folder (Where are the files we want to analyze?)')
    gd.addMessage('2. When prompted, choose the output folder (Where should we put the results?)')
    gd.addMessage('3. Start processing images from the input folder. For each image, you will be asked to select a Threshold.')
    gd.addMessage('Channels:')
    gd.addMessage('Channel 1 - ' + config["channels"]["1"])
    gd.addMessage('Channel 2 - ' + config["channels"]["2"])
    gd.addMessage('Channel 3 - ' + config["channels"]["3"])
    gd.showDialog()
    if (gd.wasCanceled()):
        return 0

    inDir = IJDirectory('Input')
    outDir = IJDirectory('Output')

    ImageProcessor(inDir, outDir).run()


class ImageProcessor:
    def __init__(self, inputDir, outputDir):
        self.inputDir = inputDir
        self.outputDir = outputDir
        self.roiManager = None
        self.channel1Cells = {}
        self.channel2Cells = {}
        self.channel3Cells = {}
        self.colocalisation = {}

    '''
    Main entrypoint, run the program. walk all the images in inputDir and process in sequence

    return void
    '''
    def run(self):
        for root, _dirs, files in os.walk(self.inputDir.path):
            for filename in files:
                imgpath = os.path.join(root, filename)
                self.processImage(imgpath)
        self.postProcessData()

    '''
    Over the course of running each image, we've aggregated the data in ImageProcessor, and after processing
    all images we want to save the aggregated data into individual csv files
    
    return void
    ''' 
    def postProcessData(self):
        channels = Config.getConfig()["channels"]
        self.saveCollection(self.channel1Cells, '{}_cells.csv'.format(channels["1"]))
        self.saveCollection(self.channel2Cells, '{}_cells.csv'.format(channels["2"]))
        self.saveCollection(self.channel3Cells, '{}_cells.csv'.format(channels["3"]))
        self.saveCollection(self.colocalisation, 'colocalisation.csv')

    '''
    Save a collection to a file
    
    @collection dict -  of type 
    {
        '__HEADER__' => ['header', 'columns'],
        'imgFileName' => [[measurements, for, roi1], [measurements, for, roi2], [measurements, for, roi3]]
    }

    @name str - name of the file

    return void
    '''
    def saveCollection(self, collection, name):
        with open('{}/{}'.format(self.outputDir.path, name), 'wb') as csvfile:
            csvfile.write(codecs.BOM_UTF8)
            writer = csv.writer(csvfile)
            headers = [header.encode('utf-8') for header in collection[HEADER_KEY]]
            writer.writerow([''] + headers)
            for imgName, measurements in sorted(collection.items()):
                if (imgName == HEADER_KEY):
                    continue
                writer.writerow([imgName])
                writer.writerows(map(lambda measurement_row: [''] + [entry.encode('utf-8') for entry in measurement_row], measurements))
        

    '''
    Process a single image by running the various ROI analyses/measurements

    @imgpath str - file path to the image being processed

    return void
    '''
    def processImage(self, imgpath):
        img = Image.fromCZI(imgpath)
        filename = os.path.basename(imgpath)
        imgName = os.path.splitext(filename)[0]

        config = Config.getConfig()
        threshold = img.getThreshold(config["channels"][config["mainChannel"]])
        # routine to select and create single images of the channels and then close the parent z-stack
        channel_1_img = img.createStackedImage(config["channels"]["1"], 1)
        channel_2_img = img.createStackedImage(config["channels"]["2"], 2)
        channel_3_img = img.createStackedImage(config["channels"]["3"], 3)
        images = {
            "1": channel_1_img,
            "2": channel_2_img,
            "3": channel_3_img,
        }
        img.close()

        # routine to create ROIs for each nucleus using a set threshold, saves a nuclear mask image and then closes it, saves nuclei properties and the nuclear ROIs
        # save DAPI TIFF
        images[config["mainChannel"]].select()
        IJ.setThreshold(threshold, 65535)

        self.getRoiManager().runCommand('Show All with labels')
        IJ.run("Analyze Particles...", "size=500-Infinity show=Outlines add slice")
        drawing = IJ.getImage()
        tif_name = 'Drawing of {}.tif'.format(imgName)
        IJ.saveAsTiff(drawing, '{}/{}'.format(self.outputDir.path, tif_name))
        drawing.close()

        self.getRoiManager().runCommand('Save', '{}/{}_RoiSet.zip'.format(self.outputDir.path, imgName))

        # Channel1
        headings, c1_measurements = self.getRoiMeasurements(channel_1_img)
        self.channel1Cells[HEADER_KEY] = headings
        self.channel1Cells[imgName] = c1_measurements

        # Channel2
        headings, c2_measurements = self.getRoiMeasurements(channel_2_img)
        self.channel2Cells[HEADER_KEY] = headings
        self.channel2Cells[imgName] = c2_measurements

        # Channel3
        headings, c3_measurements = self.getRoiMeasurements(channel_3_img)
        self.channel3Cells[HEADER_KEY] = headings
        self.channel3Cells[imgName] = c3_measurements

        # Colocalisation
        coloc_channel = config["colocChannel"]
        if (coloc_channel is not None and config["channels"].has_key(coloc_channel)):
            headings, coloc_measurements = self.getColocalisationForImg(images[coloc_channel])
            self.colocalisation[HEADER_KEY] = headings
            self.colocalisation[imgName] = coloc_measurements

        # close everything
        self.disposeRoiManager()
        for img in images.values():
            img.close()
        Results().close()


    '''
    Given an image, run Colocalisation Test plugin

    @img Image - the image to run Coloc on

    return tuple([headers], [[roi measurements]])
    '''
    def getColocalisationForImg(self, img):
        roiM = self.getRoiManager()
        headers = None
        collection = []
        config = Config.getConfig()
        for i in range(0, roiM.getCount()):
            img.select()
            roiM.select(i)
            IJ.run('Colocalization Test', 'channel_1={} channel_2={} roi=[ROI in channel {} ] randomization=[Fay (x,y,z translation)] current_slice'.format(config["channels"]["1"], config["channels"]["2"], config["colocChannel"]))
            resultsTextWindow = WindowManager.getWindow('Results')
            textPanel = resultsTextWindow.getTextPanel()
            headings = textPanel.getOrCreateResultsTable().getColumnHeadings().split("\t")
            data = textPanel.getLine(0).split("\t")
            headers = headings if headers is None else headers
            collection.append(data)

        return (headers, collection)


    '''
    Get a reference to our roiManager, create if non exists

    return RoiManager
    '''
    def getRoiManager(self):
        if self.roiManager is None:
            self.roiManager = RoiManager()
        return self.roiManager
    
    '''
    Get rid of our RoiManager

    return void
    '''
    def disposeRoiManager(self):
        if (self.roiManager is not None):
            self.roiManager.reset()
            self.roiManager.close()
            self.roiManager = None


    '''
    Given an image, get ROI measurements

    @img Image - the image to run Coloc on

    return tuple([headers], [[roi measurements]])
    '''
    def getRoiMeasurements(self, img):
        roiM = self.getRoiManager()
        roiM.deselect()
        img.select()
        roiM.runCommand('Measure')
        results = Results()
        data = results.getResultsArray()
        results.close()
        return data

run()